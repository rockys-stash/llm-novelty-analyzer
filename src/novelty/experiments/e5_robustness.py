"""E5 Robustness: do the indicators, and E2's validity result, depend on choices we made?

Each variant recomputes every indicator with one choice changed: a different embedding model
(bge-small-en-v1.5 instead of all-MiniLM-L6-v2) or half the corpus (the 500 most relevant papers per
topic). Reported: the Spearman correlation of each indicator with its primary value across items,
and the paraphrase → later AUROC under the variant next to the primary one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from novelty import indicators as I
from novelty.experiments.common import ci, fmt, latest_run, result_dir, table
from novelty.experiments.e2_validity import oriented
from novelty.items import read
from novelty.stats import auroc, bootstrap, spearman

DESCRIPTION = "Indicators recomputed with another embedding model and with half the corpus"


def paraphrase_later(rows: list[dict[str, Any]], k: str, cfg: dict[str, Any]) -> dict[str, Any]:
    ra, rb = [r for r in rows if r["kind"] == "paraphrase"], [r for r in rows if r["kind"] == "later"]
    v = oriented(ra + rb, k)
    strata = np.array([0] * len(ra) + [1] * len(rb))
    return bootstrap(lambda idx: auroc(v[idx][strata[idx] == 0], v[idx][strata[idx] == 1]), len(v),
                     int(cfg["bootstrap"]), int(cfg["seed"]), strata)  # fmt: skip


def run(cfg: dict[str, Any], results: Path | None = None, items_path: Path | None = None) -> Path:
    e1 = latest_run("e1_indicators", results)
    primary: list[dict[str, Any]] = json.loads((e1 / "items.json").read_text(encoding="utf-8"))
    items = read(items_path) if items_path else read()
    by_id = {r["id"]: r for r in primary}
    items = [i for i in items if i.id in by_id]
    with result_dir("e5_robustness", cfg, DESCRIPTION, results) as (rd, s):
        out: list[dict[str, Any]] = []
        for name, v in cfg["variants"].items():
            scored = I.compute(items, v["embedding"], v.get("limit"))
            rows = [{"id": i.id, "kind": i.kind, "values": scored[i.id]["values"]} for i in items]
            for k in I.INDICATORS:
                a = np.array([by_id[r["id"]]["values"][k] for r in rows], dtype=np.float64)
                b = np.array([r["values"][k] for r in rows], dtype=np.float64)
                out.append({"variant": name, "indicator": k, "rank_agreement": spearman(a, b),
                            "auroc_primary": paraphrase_later([by_id[r["id"]] for r in rows], k, cfg),
                            "auroc_variant": paraphrase_later(rows, k, cfg)})  # fmt: skip
        rd.write_json("variants.json", out)
        s.title = "E5 Robustness of the indicators"
        s.question = "Would another embedding model or a smaller corpus change the indicators or their validity?"
        s.tables.append(table("variants", "Rank agreement with the primary indicator over all items, and paraphrase → later AUROC (95% CI)",
            [("variant", "Variant", "l"), ("indicator", "Indicator", "l"), ("rho", "Spearman with primary", "r"),
             ("p", "AUROC primary", "r"), ("v", "AUROC variant", "r")],
            [{"variant": r["variant"], "indicator": I.LABEL[r["indicator"]], "rho": fmt(r["rank_agreement"], 2),
              "p": ci(r["auroc_primary"], 2), "v": ci(r["auroc_variant"], 2)} for r in out]))  # fmt: skip
        for name in cfg["variants"]:
            rs = [r for r in out if r["variant"] == name]
            lo = min(rs, key=lambda r: r["rank_agreement"] if r["rank_agreement"] == r["rank_agreement"] else 2)
            s.findings.append(f"{name}: rank agreement with the primary indicators ranges from {fmt(lo['rank_agreement'], 2)} "
                              f"({I.LABEL[lo['indicator']]}) to {fmt(max(r['rank_agreement'] for r in rs), 2)}.")  # fmt: skip
    return rd.path
