"""Write the items: generated ideas and the three controls (``items/items.jsonl``, resumable)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from novelty import corpus
from novelty.items import ITEMS, Item, append, parse_reply, read

FORMAT = ("Reply in exactly this format and nothing else:\nTitle: <one line>\n"
          "Idea: <three to four sentences: the problem, the proposed approach, and how it would be evaluated>")  # fmt: skip
PROMPT_VERSION = "items-v1"


def idea_prompt(label: str) -> str:
    return (f"You are a researcher working on {label.lower()}. Propose one new research idea in this area that, "
            f"as far as you know, has not been published.\n\n{FORMAT}")  # fmt: skip


def restate_prompt(p: corpus.Paper) -> str:
    return (f"Here is a published paper.\n\nTitle: {p.title}\nAbstract: {p.abstract}\n\n"
            "Rewrite it as a short research idea, as if you were proposing it. Keep its content; do not add anything "
            f"that is not in the abstract.\n\n{FORMAT}")  # fmt: skip


def combine_prompt(a: corpus.Paper, b: corpus.Paper) -> str:
    return (f"Here are two published papers.\n\nPaper 1\nTitle: {a.title}\nAbstract: {a.abstract}\n\n"
            f"Paper 2\nTitle: {b.title}\nAbstract: {b.abstract}\n\n"
            "Propose one research idea that combines the two papers, for example by applying the method of one to "
            f"the problem of the other. Use only what is in these two abstracts.\n\n{FORMAT}")  # fmt: skip


def plan(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Every item to write, with its prompt and source papers; deterministic given the config."""
    rng = np.random.default_rng(int(cfg["seed"]))
    jobs: list[dict[str, Any]] = []
    for topic, label in corpus.topics().items():
        pool = corpus.load(topic)[: int(cfg["source_pool"])]
        for model in cfg["idea_models"]:
            for k in range(int(cfg["ideas_per_model"])):
                jobs.append({"id": f"{topic}-idea-{model}-{k}", "topic": topic, "kind": "idea", "model": model,
                             "prompt": idea_prompt(label), "sources": [], "temperature": float(cfg["temperature"]),
                             "seed": int(cfg["seed"]) + 100 * k})  # fmt: skip
        picks = rng.choice(len(pool), size=int(cfg["paraphrase"]) + 2 * int(cfg["recombination"]), replace=False)
        para, comb = picks[: int(cfg["paraphrase"])], picks[int(cfg["paraphrase"]) :].reshape(-1, 2)
        later = corpus.load(topic, "later")
        later_idx = rng.choice(len(later), size=int(cfg["later"]), replace=False)
        ctl = {"model": cfg["control_model"], "temperature": 0.0, "topic": topic, "seed": int(cfg["seed"])}
        for k, i in enumerate(sorted(para.tolist())):
            jobs.append({**ctl, "id": f"{topic}-paraphrase-{k}", "kind": "paraphrase",
                         "prompt": restate_prompt(pool[i]), "sources": [pool[i].doi]})  # fmt: skip
        for k, (i, j) in enumerate(comb.tolist()):
            jobs.append({**ctl, "id": f"{topic}-recombination-{k}", "kind": "recombination",
                         "prompt": combine_prompt(pool[i], pool[j]), "sources": [pool[i].doi, pool[j].doi]})  # fmt: skip
        for k, i in enumerate(sorted(later_idx.tolist())):
            jobs.append({**ctl, "id": f"{topic}-later-{k}", "kind": "later",
                         "prompt": restate_prompt(later[i]), "sources": [later[i].doi]})  # fmt: skip
    return jobs


def write_meta(path: Path, kind: str, cfg: dict[str, Any], extra: dict[str, Any]) -> None:
    """Provenance of a generation or judging run, next to its output (one entry per run, appended)."""
    from importlib import metadata

    from novelty import llm
    from novelty.experiments.common import git_commit

    sha, dirty = git_commit()
    entry = {"kind": kind, "commit": sha, "dirty": dirty, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "config": cfg, "models": {k: {"file": v["file"], "sha256": v["sha256"]} for k, v in llm.config()["models"].items()},
             "llama_cpp_python": metadata.version("llama-cpp-python"), **extra}  # fmt: skip
    runs = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([*runs, entry], indent=1), encoding="utf-8")


def run(cfg: dict[str, Any], out: Path = ITEMS, models: list[str] | None = None, limit: int | None = None) -> int:
    from novelty.llm import LocalModel

    done = {i.id for i in read(out)}
    jobs = [j for j in plan(cfg) if j["id"] not in done and (not models or j["model"] in models)]
    if limit:
        jobs = jobs[:limit]
    if jobs:
        write_meta(out.parent / "items_meta.json", "generate", cfg,
                   {"prompt_version": PROMPT_VERSION, "jobs": len(jobs), "threads": os.environ.get("NOVELTY_LLM_THREADS")})  # fmt: skip
    added = 0
    for name in dict.fromkeys(j["model"] for j in jobs):
        model = LocalModel(name)
        mine = [j for j in jobs if j["model"] == name]
        for n, j in enumerate(mine, 1):
            seed = int(j["seed"])
            for attempt in range(4):  # resample (new seed) only if the reply ignored the format
                raw = model.generate([{"role": "user", "content": j["prompt"]}], "Title:", int(cfg["max_tokens"]),
                                     j["temperature"] if attempt == 0 else max(j["temperature"], 0.7), seed + attempt)  # fmt: skip
                parsed = parse_reply(raw)
                if parsed:
                    break
            if parsed is None:
                print(f"{j['id']}: no usable reply after 4 attempts; skipped", file=sys.stderr, flush=True)
                continue
            append(
                Item(j["id"], j["topic"], j["kind"], name, parsed[0], parsed[1], j["sources"], seed + attempt, raw), out
            )
            added += 1
            print(f"{name}: {n}/{len(mine)} {j['id']}", file=sys.stderr, flush=True)
    return added
