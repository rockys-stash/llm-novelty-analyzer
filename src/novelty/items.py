"""Items under analysis: LLM-generated research ideas and three controls with known provenance.

Every item is a title and a three-to-four sentence idea. ``kind`` says where its content came from:

* ``idea``: a language model asked for a new research idea in the topic (what the study is about);
* ``paraphrase``: a corpus paper restated as an idea (its prior art is in the corpus by construction);
* ``recombination``: two corpus papers combined into one idea (a recombination by construction);
* ``later``: a paper published after the corpus ends, restated as an idea (absent from the prior art).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ITEMS = ROOT / "items" / "items.jsonl"
KINDS = ["paraphrase", "recombination", "idea", "later"]
KIND_LABEL = {"paraphrase": "Paraphrased prior paper", "recombination": "Recombined two prior papers",
              "idea": "LLM-generated idea", "later": "Paper published after the corpus"}  # fmt: skip


@dataclass
class Item:
    id: str
    topic: str
    kind: str
    model: str  # the model that wrote the text
    title: str
    text: str
    sources: list[str] = field(default_factory=list)  # DOIs the text was written from (controls)
    seed: int = 0
    raw: str = ""  # the model's full reply

    @property
    def full(self) -> str:
        return f"{self.title}. {self.text}"


_FORMAT = re.compile(r"Title:\s*(?P<title>.+?)\s*\n+\s*Idea:\s*(?P<idea>.+)", re.DOTALL | re.IGNORECASE)


def parse_reply(reply: str) -> tuple[str, str] | None:
    """Title and idea from a "Title: ... / Idea: ..." reply; None if the format was not followed."""
    m = _FORMAT.search(reply)
    if not m:
        return None
    title = m.group("title").strip().strip("*#\"' ")
    idea = re.sub(r"\s+", " ", m.group("idea")).strip()
    if not title or len(idea.split()) < 20:
        return None
    return title, idea


def read(path: Path = ITEMS) -> list[Item]:
    if not path.exists():
        return []
    return [Item(**json.loads(x)) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def append(item: Item, path: Path = ITEMS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
