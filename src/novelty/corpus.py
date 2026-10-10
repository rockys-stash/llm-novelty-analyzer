"""Literature corpus: Crossref adapter, DOI manifest and loaders.

The prior art for each topic is the ``per_topic`` most relevant journal articles Crossref returns for
the topic query, published between ``from`` and ``until``, that have an abstract and a deposited
reference list. Search results drift as Crossref's index grows, so the first retrieval writes a DOI
manifest (``data/corpus_manifest.json``, committed) and every later fetch rehydrates exactly those
DOIs. Abstracts stay in ``data/raw`` (publishers hold their copyright) and are never committed.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "corpus_manifest.json"
CONFIG = ROOT / "configs" / "corpus.yaml"
API = "https://api.crossref.org/works"
MAILTO = "rockys-stash@users.noreply.github.com"  # Crossref's "polite pool" asks for a contact
FIELDS = "DOI,title,abstract,reference,issued,container-title,is-referenced-by-count"


@dataclass
class Paper:
    doi: str
    title: str
    abstract: str
    year: int | None
    venue: str
    references: list[str] = field(default_factory=list)  # lower-cased DOIs of deposited references
    cited_by: int = 0

    @property
    def text(self) -> str:
        return f"{self.title}. {self.abstract}"


def config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
# inline formatting that survives as escaped text; never matches "<5 °C" or "a > b"
_FORMAT = re.compile(r"</?(?:i|b|em|strong|sub|sup|scp|sc|u|span|mml:[a-z]+)(?:\s[^<>]*)?/?>", re.IGNORECASE)


def clean_abstract(raw: str) -> str:
    """JATS XML to plain text: drop tags and a leading 'Abstract' heading, unescape entities."""
    text = _FORMAT.sub("", html.unescape(_TAG.sub(" ", raw)))  # some records escape their markup (&lt;i&gt;)
    text = _SPACE.sub(" ", text).strip()
    return re.sub(r"^(abstract|summary)\s*[:.]?\s*", "", text, flags=re.IGNORECASE)


def parse(item: dict[str, Any]) -> Paper | None:
    title = _SPACE.sub(" ", _FORMAT.sub("", html.unescape(_TAG.sub("", " ".join(item.get("title") or []))))).strip()
    abstract = clean_abstract(item.get("abstract") or "")
    if not title or len(abstract.split()) < 40:  # too short to say what the paper did
        return None
    parts = (item.get("issued") or {}).get("date-parts") or [[None]]
    refs = sorted({r["DOI"].lower() for r in item.get("reference") or [] if r.get("DOI")})
    return Paper(item["DOI"].lower(), title, abstract, parts[0][0],
                 " ".join(item.get("container-title") or []), refs, int(item.get("is-referenced-by-count") or 0))  # fmt: skip


def _get(params: dict[str, str], tries: int = 5) -> dict[str, Any]:
    url = f"{API}?{urllib.parse.urlencode({**params, 'mailto': MAILTO})}"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"novelty-analyzer/0.1 (mailto:{MAILTO})"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())["message"]
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


def search(query: str, start: str, until: str, rows: int) -> list[Paper]:
    """The ``rows`` most relevant matching articles (Crossref relevance order), cleaned and filtered."""
    flt = f"has-abstract:true,has-references:true,type:journal-article,from-pub-date:{start},until-pub-date:{until}"
    out: list[Paper] = []
    seen: set[str] = set()
    msg = _get({"query.bibliographic": query, "filter": flt, "rows": str(min(rows * 2, 1000)), "select": FIELDS})
    for item in msg["items"]:
        p = parse(item)
        if p and p.doi not in seen and p.title.lower() not in {q.title.lower() for q in out}:
            seen.add(p.doi)
            out.append(p)
        if len(out) == rows:
            break
    return out


def by_doi(dois: list[str], batch: int = 50) -> list[Paper]:
    """Rehydrate papers from their DOIs, in the given order."""
    found: dict[str, Paper] = {}
    for i in range(0, len(dois), batch):
        chunk = dois[i : i + batch]
        msg = _get({"filter": ",".join(f"doi:{d}" for d in chunk), "rows": str(len(chunk)), "select": FIELDS})
        for item in msg["items"]:
            if p := parse(item):
                found[p.doi] = p
        time.sleep(0.2)
    return [found[d] for d in dois if d in found]


def _write(path: Path, papers: list[Paper]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for p in papers:
            f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")


def _hash(dois: list[str]) -> str:
    return hashlib.sha256("\n".join(dois).encode()).hexdigest()


def fetch(retrieve: bool = False) -> dict[str, int]:
    """Make ``data/raw/corpus`` match the manifest. With ``retrieve`` (or no manifest yet), search
    Crossref afresh and write a new manifest; otherwise rehydrate the manifest's DOIs."""
    cfg = config()
    manifest: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    fresh = retrieve or not manifest
    if fresh:
        manifest = {"retrieved": time.strftime("%Y-%m-%d"), "source": "Crossref REST API", "config": cfg, "topics": {}}
    counts: dict[str, int] = {}
    for key, t in cfg["topics"].items():
        for part, (start, until, n) in {"corpus": (cfg["from"], cfg["until"], cfg["per_topic"]),
                                        "later": (cfg["later_from"], cfg["later_until"], cfg["later_per_topic"])}.items():  # fmt: skip
            path = RAW / part / f"{key}.jsonl.gz"
            if fresh:
                papers = search(t["query"], start, until, n)
                entry: dict[str, Any] = {"dois": [p.doi for p in papers]}
                entry["sha256"] = _hash(entry["dois"])
                manifest["topics"].setdefault(key, {})[part] = entry
            else:
                entry = manifest["topics"][key][part]
                if path.exists() and [p.doi for p in load_path(path)] == entry["dois"]:
                    counts[f"{key}/{part}"] = len(entry["dois"])
                    continue
                papers = by_doi(entry["dois"])
                missing = set(entry["dois"]) - {p.doi for p in papers}
                if missing:
                    raise RuntimeError(
                        f"{key}/{part}: {len(missing)} manifest DOIs no longer resolve, e.g. {sorted(missing)[:3]}"
                    )
            _write(path, papers)
            counts[f"{key}/{part}"] = len(papers)
    if fresh:
        MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return counts


def load_path(path: Path) -> list[Paper]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [Paper(**json.loads(line)) for line in f if line.strip()]


@lru_cache(maxsize=32)
def load(topic: str, part: str = "corpus") -> tuple[Paper, ...]:
    path = RAW / part / f"{topic}.jsonl.gz"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run `make data`")
    return tuple(load_path(path))


def topics() -> dict[str, str]:
    return {k: v["label"] for k, v in config()["topics"].items()}


def iter_all(part: str = "corpus") -> Iterator[tuple[str, Paper]]:
    for t in topics():
        for p in load(t, part):
            yield t, p


def input_hashes() -> dict[str, str]:
    """SHA-256 of each topic's DOI list and of the generated items, for provenance."""
    out: dict[str, str] = {}
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for t, parts in m["topics"].items():
            for part, e in parts.items():
                out[f"{t}/{part}"] = e["sha256"]
    items = ROOT / "items" / "items.jsonl"
    if items.exists():
        out["items"] = hashlib.sha256(items.read_bytes()).hexdigest()
    return out
