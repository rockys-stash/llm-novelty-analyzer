"""E4 Similarity is not novelty: where the indicators disagree, and what kind of ideas the models wrote.

Two analyses. First, the rank correlation between every pair of indicators over all items: if they
measured one thing they would agree. Second, each generated idea is placed in one of three groups
using thresholds taken from the controls only (never from the ideas themselves):

* **near-duplicate**: its highest similarity to a prior paper is at least as high as that of the
  ``near_duplicate_quantile`` quantile of paraphrased papers (as close to a paper as most restatements);
* **known combination**: otherwise, if the share of its concept pairs already seen together is at least
  the ``known_pairs_quantile`` quantile of the recombination controls;
* **new combination**: everything else, i.e. it puts together concepts the corpus has not.

The groups describe how an idea relates to this corpus. They are not a verdict on its novelty,
which is what E3 tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from novelty import corpus
from novelty import indicators as I
from novelty.experiments.common import fmt, latest_run, result_dir, table
from novelty.stats import spearman

DESCRIPTION = "Agreement between indicators, and generated ideas grouped by thresholds set on the controls"
GROUPS = ["near-duplicate", "known combination", "new combination"]


def run(cfg: dict[str, Any], results: Path | None = None, items_path: Path | None = None) -> Path:
    e1 = latest_run("e1_indicators", results)
    rows: list[dict[str, Any]] = json.loads((e1 / "items.json").read_text(encoding="utf-8"))
    with result_dir("e4_disagreement", cfg, DESCRIPTION, results) as (rd, s):
        X = {k: np.array([r["values"][k] for r in rows], dtype=np.float64) for k in I.INDICATORS}
        matrix = [[spearman(X[a], X[b]) for b in I.INDICATORS] for a in I.INDICATORS]
        para = [r["values"]["semantic_max"] for r in rows if r["kind"] == "paraphrase"]
        rec = [r["values"]["kg_known_pairs"] for r in rows if r["kind"] == "recombination"]
        t_sem = float(np.quantile(para, float(cfg["near_duplicate_quantile"]))) if para else float("nan")
        t_kg = float(np.nanquantile(rec, float(cfg["known_pairs_quantile"]))) if rec else float("nan")

        def group(r: dict[str, Any]) -> str:
            v = r["values"]
            if v["semantic_max"] >= t_sem:
                return "near-duplicate"
            if v["kg_known_pairs"] == v["kg_known_pairs"] and v["kg_known_pairs"] >= t_kg:
                return "known combination"
            return "new combination"

        ideas = [r for r in rows if r["kind"] == "idea"]
        assigned = [{"id": r["id"], "topic": r["topic"], "model": r["model"], "title": r["title"], "group": group(r),
                     "semantic_max": r["values"]["semantic_max"], "kg_known_pairs": r["values"]["kg_known_pairs"],
                     "nearest": r["neighbours"][0]["title"]} for r in ideas]  # fmt: skip
        counts: list[dict[str, Any]] = []
        for model in sorted({a["model"] for a in assigned}):
            mine = [a for a in assigned if a["model"] == model]
            counts.append({"model": model, "n": len(mine), **{g: sum(a["group"] == g for a in mine) for g in GROUPS}})
        # disagreements: ideas the semantic indicator calls far from prior art but whose concept pairs are all known
        sem_med = float(np.median([a["semantic_max"] for a in assigned])) if assigned else float("nan")
        disagree = [a for a in assigned if a["semantic_max"] < sem_med and a["kg_known_pairs"] == 1.0]
        rd.write_json("matrix.json", {"indicators": I.INDICATORS, "spearman": matrix})
        rd.write_json("groups.json", {"thresholds": {"semantic_max": t_sem, "kg_known_pairs": t_kg}, "ideas": assigned,
                                      "counts": counts, "disagreements": disagree})  # fmt: skip
        s.title = "E4 Similarity is not novelty"
        s.question = "Do the indicators agree with each other, and are the generated ideas new or recombinations of this literature?"
        s.tables.append(table("matrix", "Spearman correlation between indicators over all items",
            [("a", "", "l")] + [(k, I.LABEL[k], "r") for k in I.INDICATORS],
            [{"a": I.LABEL[a], **{b: fmt(matrix[i][j], 2) for j, b in enumerate(I.INDICATORS)}} for i, a in enumerate(I.INDICATORS)]))  # fmt: skip
        s.tables.append(table("groups", f"Generated ideas by group (thresholds from controls: similarity ≥ {t_sem:.3f}; known concept pairs ≥ {t_kg:.2f})",
            [("model", "Model", "l"), ("n", "Ideas", "r")] + [(g, g.capitalize(), "r") for g in GROUPS],
            counts))  # fmt: skip
        sem_kg = matrix[I.INDICATORS.index("semantic_max")][I.INDICATORS.index("kg_known_pairs")]
        s.findings.append(f"Semantic similarity and the share of known concept pairs correlate at ρ = {fmt(sem_kg, 2)} over all items, "
                          "so they do not measure the same thing.")  # fmt: skip
        tot = {g: sum(c[g] for c in counts) for g in GROUPS}
        n = sum(c["n"] for c in counts)
        if n:
            s.findings.append(f"Of {n} generated ideas in {len(corpus.topics())} topics: {tot['near-duplicate']} near-duplicates of a prior "
                              f"paper, {tot['known combination']} known combinations, {tot['new combination']} new combinations of this literature.")  # fmt: skip
        s.findings.append(f"{len(disagree)} ideas are less similar to any paper than the median idea, yet every one of their concept "
                          "pairs already appears together in some prior paper: low similarity without new combinations.")  # fmt: skip
    return rd.path
