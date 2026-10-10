"""E2 Validity against known provenance: do the indicators rank the controls the way they must?

The controls have a known relation to the prior art. A paraphrase restates a corpus paper, a
recombination merges two corpus papers, a *later* paper was published after the corpus ends. Any
indicator that tracks novelty relative to the corpus must place paraphrases below later papers. For
each indicator, oriented so that higher means more novel, the AUROC of each pair of kinds (0.5 = it
cannot tell them apart; 1 = it always ranks the second kind as more novel), with a bootstrap
interval stratified by kind. Also: does the prior-art map find the papers a control was written from?
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from novelty import indicators as I
from novelty.experiments.common import ci, latest_run, result_dir, table
from novelty.items import KIND_LABEL
from novelty.stats import auroc, bootstrap

DESCRIPTION = "AUROC of each indicator between control kinds of known provenance; source recovery of the prior-art map"
COMPARISONS = [("paraphrase", "later"), ("recombination", "later"), ("paraphrase", "recombination"),
               ("paraphrase", "idea"), ("idea", "later")]  # fmt: skip


def oriented(rows: list[dict[str, Any]], k: str) -> np.ndarray:
    return np.array([I.DIRECTION[k] * -r["values"][k] for r in rows], dtype=np.float64)  # higher = more novel


def run(cfg: dict[str, Any], results: Path | None = None, items_path: Path | None = None) -> Path:
    e1 = latest_run("e1_indicators", results)
    rows: list[dict[str, Any]] = json.loads((e1 / "items.json").read_text(encoding="utf-8"))
    with result_dir("e2_validity", cfg, DESCRIPTION, results) as (rd, s):
        out: list[dict[str, Any]] = []
        for a, b in COMPARISONS:
            ra, rb = [r for r in rows if r["kind"] == a], [r for r in rows if r["kind"] == b]
            if not ra or not rb:
                continue
            both = ra + rb
            strata = np.array([0] * len(ra) + [1] * len(rb))
            for k in I.INDICATORS:
                v = oriented(both, k)

                def stat(idx: np.ndarray, v: np.ndarray = v) -> float:
                    return auroc(v[idx][strata[idx] == 0], v[idx][strata[idx] == 1])

                out.append({"a": a, "b": b, "indicator": k, "n_a": len(ra), "n_b": len(rb),
                            "auroc": bootstrap(stat, len(both), int(cfg["bootstrap"]), int(cfg["seed"]), strata)})  # fmt: skip
        rd.write_json("auroc.json", out)
        recovery: dict[str, Any] = {}
        for kind in ("paraphrase", "recombination"):
            ranks = [list(r["source_ranks"].values()) for r in rows if r["kind"] == kind and r["source_ranks"]]
            if ranks:
                recovery[kind] = {"n": len(ranks), "top1_all": float(np.mean([max(x) == 1 for x in ranks])),
                                  "top10_all": float(np.mean([max(x) <= 10 for x in ranks])),
                                  "top10_any": float(np.mean([min(x) <= 10 for x in ranks])),
                                  "median_rank": float(np.median([y for x in ranks for y in x]))}  # fmt: skip
        rd.write_json("recovery.json", recovery)
        s.title = "E2 Validity against known provenance"
        s.question = "Do the indicators place restated prior papers below papers the corpus has never seen?"
        s.tables.append(table("auroc", "AUROC with 95% bootstrap interval (stratified by kind); higher = indicator ranks the second kind as more novel",
            [("cmp", "Comparison", "l")] + [(k, I.LABEL[k], "r") for k in I.INDICATORS],
            [{"cmp": f"{KIND_LABEL[a]} → {KIND_LABEL[b]}",
              **{r["indicator"]: ci(r["auroc"], 2) for r in out if r["a"] == a and r["b"] == b}}
             for a, b in COMPARISONS if any(r["a"] == a and r["b"] == b for r in out)]))  # fmt: skip
        if recovery:
            s.tables.append(table("recovery", "Does the prior-art map find the papers a control was written from? (embedding nearest neighbours)",
                [("kind", "Control", "l"), ("n", "Items", "r"), ("t1", "Source ranked 1st", "r"), ("t10", "All sources in top 10", "r"),
                 ("any", "Any source in top 10", "r"), ("med", "Median source rank", "r")],
                [{"kind": KIND_LABEL[k], "n": v["n"], "t1": f"{v['top1_all']:.0%}", "t10": f"{v['top10_all']:.0%}",
                  "any": f"{v['top10_any']:.0%}", "med": f"{v['median_rank']:.0f}"} for k, v in recovery.items()]))  # fmt: skip
        main = [r for r in out if r["a"] == "paraphrase" and r["b"] == "later"]
        if main:
            best = max(main, key=lambda r: r["auroc"]["value"])
            weak = [I.LABEL[r["indicator"]] for r in main if r["auroc"]["lo"] is not None and r["auroc"]["lo"] <= 0.5]
            s.findings.append(
                f"Paraphrased prior papers vs papers published after the corpus: best indicator {I.LABEL[best['indicator']]} "
                f"(AUROC {ci(best['auroc'], 2)}). Indicators whose interval includes chance: {', '.join(weak) or 'none'}."
            )
        for k, v in recovery.items():
            s.findings.append(f"{KIND_LABEL[k]}: the source paper is the nearest neighbour for {v['top1_all']:.0%} of items; "
                              f"every source is in the top 10 for {v['top10_all']:.0%}.")  # fmt: skip
    return rd.path
