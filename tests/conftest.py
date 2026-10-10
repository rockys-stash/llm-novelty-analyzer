"""Shared fixtures. Unit tests use synthetic items and results so they run without the corpus;
tests marked ``needs_data`` read the real corpus (``make data``)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pytest

from novelty import corpus
from novelty.indicators import INDICATORS

HAVE_DATA = all((corpus.RAW / "corpus" / f"{t}.jsonl.gz").exists() for t in corpus.topics())
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="corpus not fetched (make data)")
KIND_SHIFT = {"paraphrase": 0.85, "recombination": 0.7, "idea": 0.6, "later": 0.5}


def synthetic_rows(n_per_kind: int = 12, seed: int = 0) -> list[dict[str, Any]]:
    """E1-shaped item rows whose similarity falls from paraphrase to later, as a valid indicator's would."""
    rng = np.random.default_rng(seed)
    rows = []
    for kind, base in KIND_SHIFT.items():
        for k in range(n_per_kind):
            model = "qwen3-4b" if k % 2 else "phi-4-mini"
            values = {i: float(np.clip(base + rng.normal(0, 0.05), 0, 1)) for i in INDICATORS}
            values["new_phrase_share"] = float(1 - values["semantic_max"])
            sources = [f"10.1/{kind}{k}"] if kind != "idea" else []
            rows.append({"id": f"calibration-{kind}-{k}", "topic": "calibration", "kind": kind, "model": model,
                         "title": f"{kind} {k}", "text": "An idea.", "sources": sources, "values": values,
                         "concepts": ["a", "b"], "new_phrases": [], "unseen_pairs": [], "n_pairs": 1,
                         "neighbours": [{"doi": f"10.1/{kind}{k}", "title": "Prior", "year": 2020, "venue": "J",
                                         "similarity": values["semantic_max"], "shared_concepts": ["a"], "source": bool(sources)}],
                         "source_ranks": {s: 1 if kind == "paraphrase" else 3 for s in sources}})  # fmt: skip
    return rows


def write_e1(results: Path, rows: list[dict[str, Any]]) -> Path:
    run = results / "e1_indicators" / "20260101T000000Z-abcdef0"
    run.mkdir(parents=True)
    (run / "items.json").write_text(json.dumps(rows))
    (run / "corpus.json").write_text(json.dumps([{"topic": "calibration", "label": "Calibration", "papers": 10,
                                                  "years": [2015, 2025], "concepts": 5, "edges": 4,
                                                  "median_references": 20, "later": 2}]))  # fmt: skip
    (run / "by_kind.json").write_text(json.dumps([]))
    (run / "summary.json").write_text(
        json.dumps({"title": "E1", "question": "?", "findings": [], "tables": [], "notes": []})
    )
    (run / "provenance.json").write_text(json.dumps({"experiment": "e1_indicators", "run_id": run.name, "commit": "abcdef0",
                                                     "dirty": False, "created_at": "", "runtime_seconds": 1, "cpus": 4}))  # fmt: skip
    (results / "e1_indicators" / "LATEST").write_text(run.name + "\n")
    return run
