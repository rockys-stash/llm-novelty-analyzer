"""Model judges: the human rubric (docs/ANNOTATION_PROTOCOL.md) answered by local language models.

These are *model judgments*, a pilot that exercises the analysis while the human study is pending.
They are never reported as human labels. Each judge sees only the topic and the item (title and
idea), never its kind, its source or any indicator. For each criterion the judge's next-token
distribution over the digits 1-5 is read; the score is its expected value, and the most likely
digit is written into the conversation before the next criterion is asked.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from novelty import corpus
from novelty.items import Item, read

ROOT = Path(__file__).resolve().parents[2]
JUDGMENTS = ROOT / "items" / "judgments.jsonl"
CRITERIA = ["Novelty", "Relevance", "Meaningfulness"]
PROMPT_VERSION = "judge-v1"
RUBRIC = """Rate this research idea in the area of {topic}.

Title: {title}
Idea: {text}

Use these scales:
Novelty: 1 = already published or textbook knowledge; 2 = a minor variation of published work; 3 = a new combination of known ideas; 4 = a new approach to a known problem, or a known approach to a new problem; 5 = a new problem or approach unlike existing work.
Relevance: 1 = unrelated to {topic}; 3 = loosely related; 5 = squarely within it.
Meaningfulness: 1 = unclear, infeasible or not worth doing; 3 = reasonable but vague; 5 = clear, feasible and worth doing.

Reply with three lines, each a single digit from 1 to 5:
Novelty: <1-5>
Relevance: <1-5>
Meaningfulness: <1-5>"""


def prompt(item: Item) -> str:
    return RUBRIC.format(topic=corpus.topics()[item.topic].lower(), title=item.title, text=item.text)


def run(judges: list[str], out: Path = JUDGMENTS, limit: int | None = None) -> int:
    from novelty.generate import write_meta
    from novelty.llm import LocalModel

    done = {(j["judge"], j["item"]) for j in read_judgments(out)}
    items = read()
    write_meta(out.parent / "judgments_meta.json", "judge", {"judges": judges}, {"prompt_version": PROMPT_VERSION})
    added = 0
    for name in judges:
        todo = [i for i in items if (name, i.id) not in done][:limit]
        if not todo:
            continue
        model = LocalModel(name)
        with out.open("a", encoding="utf-8") as f:
            for n, it in enumerate(todo, 1):
                dists = model.rate([{"role": "user", "content": prompt(it)}], CRITERIA)
                rec: dict[str, Any] = {"judge": name, "item": it.id, "prompt_version": PROMPT_VERSION}
                for c, p in zip(CRITERIA, dists, strict=True):
                    rec[c.lower()] = round(float((p * [1, 2, 3, 4, 5]).sum()), 4)
                    rec[c.lower() + "_dist"] = [round(float(x), 5) for x in p]
                f.write(json.dumps(rec) + "\n")
                f.flush()
                added += 1
                if n % 10 == 0 or n == len(todo):
                    print(f"{name}: {n}/{len(todo)}", file=sys.stderr, flush=True)
    return added


def read_judgments(path: Path = JUDGMENTS) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
