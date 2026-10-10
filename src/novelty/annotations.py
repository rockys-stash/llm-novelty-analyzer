"""Human annotations: an append-only store written by the console's annotation page.

Each record is one annotator's scores for one item on the three criteria of
``docs/ANNOTATION_PROTOCOL.md`` (integers 1-5), with an optional comment. Annotators are identified
only by a pseudonym they choose. Records are never edited; a corrected score is a new record and the
latest record per (annotator, item) counts.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "annotations" / "human.jsonl"
CRITERIA = ("novelty", "relevance", "meaningfulness")
_PSEUDONYM = re.compile(r"^[A-Za-z0-9_-]{2,32}$")
_lock = threading.Lock()


class InvalidAnnotationError(ValueError):
    pass


def validate(rec: dict[str, Any], item_ids: set[str]) -> dict[str, Any]:
    annotator = str(rec.get("annotator", ""))
    if not _PSEUDONYM.match(annotator):
        raise InvalidAnnotationError("annotator must be a pseudonym of 2-32 letters, digits, - or _")
    item = str(rec.get("item", ""))
    if item not in item_ids:
        raise InvalidAnnotationError("unknown item")
    out: dict[str, Any] = {"annotator": annotator, "item": item}
    for c in CRITERIA:
        v = rec.get(c)
        if not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 5:
            raise InvalidAnnotationError(f"{c} must be an integer from 1 to 5")
        out[c] = v
    comment = rec.get("comment") or ""
    if not isinstance(comment, str) or len(comment) > 1000:
        raise InvalidAnnotationError("comment must be text of at most 1,000 characters")
    out["comment"] = comment.strip()
    if rec.get("seconds") is not None:
        s = rec["seconds"]
        if not isinstance(s, int | float) or not 0 <= s < 86_400:
            raise InvalidAnnotationError("seconds out of range")
        out["seconds"] = round(float(s), 1)
    return out


def append(rec: dict[str, Any], store: Path = STORE) -> dict[str, Any]:
    rec = {**rec, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with _lock:
        store.parent.mkdir(parents=True, exist_ok=True)
        with store.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def latest(store: Path = STORE) -> list[dict[str, Any]]:
    """The latest record per (annotator, item)."""
    if not store.exists():
        return []
    by: dict[tuple[str, str], dict[str, Any]] = {}
    for line in store.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            by[(r["annotator"], r["item"])] = r
    return list(by.values())
