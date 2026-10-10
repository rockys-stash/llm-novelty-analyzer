"""E1 Indicators: every item scored against its topic's prior art, with its prior-art map.

For every item (generated ideas and the three controls) the eight indicators of
``novelty.indicators`` are computed against the corpus of its topic, together with its ten nearest
papers, the concepts it shares with each, its new phrases and its concept pairs that no paper has
combined. The summary shows each indicator's mean by item kind with a 95% bootstrap interval.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from novelty import corpus
from novelty import indicators as I
from novelty.experiments.common import ci, result_dir, table
from novelty.items import KIND_LABEL, KINDS, read
from novelty.stats import bootstrap

DESCRIPTION = "Eight novelty indicators and a prior-art map for every item against its topic's literature"


def _mean_of(v: np.ndarray) -> Callable[[np.ndarray], float]:
    return lambda b: float(np.nanmean(v[b]))


def run(cfg: dict[str, Any], results: Path | None = None, items_path: Path | None = None) -> Path:
    items = read(items_path) if items_path else read()
    if not items:
        raise RuntimeError("no items: run `make generate`")
    with result_dir("e1_indicators", cfg, DESCRIPTION, results) as (rd, s):
        scored = I.compute(items, cfg["embedding"])
        rows = [{"id": it.id, "topic": it.topic, "kind": it.kind, "model": it.model, "title": it.title, "text": it.text,
                 "sources": it.sources, **scored[it.id]} for it in items]  # fmt: skip
        rd.write_json("items.json", rows)
        stats = [corpus_stats for corpus_stats in (I.corpus_stats(t, cfg["embedding"]) for t in corpus.topics())]
        rd.write_json("corpus.json", stats)
        by_kind: list[dict[str, Any]] = []
        for kind in KINDS:
            rs = [r for r in rows if r["kind"] == kind]
            if not rs:
                continue
            entry: dict[str, Any] = {"kind": kind, "n": len(rs)}
            for k in I.INDICATORS:
                v = np.array([r["values"][k] for r in rs], dtype=np.float64)
                entry[k] = bootstrap(_mean_of(v), len(v), int(cfg["bootstrap"]), int(cfg["seed"]))
            by_kind.append(entry)
        rd.write_json("by_kind.json", by_kind)
        s.title = "E1 Novelty indicators"
        s.question = "How close is each item to its topic's existing literature, by each indicator?"
        s.tables.append(table("corpus", "Prior-art corpus per topic (Crossref journal articles with abstract and references)",
            [("label", "Topic", "l"), ("papers", "Papers", "r"), ("years", "Years", "l"), ("concepts", "Concepts", "r"),
             ("edges", "Concept pairs seen together", "r"), ("refs", "Median references", "r"), ("later", "Later papers", "r")],
            [{"label": c["label"], "papers": c["papers"], "years": f"{c['years'][0]}–{c['years'][1]}", "concepts": c["concepts"],
              "edges": c["edges"], "refs": f"{c['median_references']:.0f}", "later": c["later"]} for c in stats]))  # fmt: skip
        s.tables.append(table("by_kind", "Mean indicator by item kind, 95% bootstrap interval over items",
            [("kind", "Item kind", "l"), ("n", "Items", "r")] + [(k, I.LABEL[k], "r") for k in I.INDICATORS],
            [{"kind": KIND_LABEL[e["kind"]], "n": e["n"], **{k: ci(e[k]) for k in I.INDICATORS}} for e in by_kind]))  # fmt: skip
        ideas = [r for r in rows if r["kind"] == "idea"]
        para = [r for r in rows if r["kind"] == "paraphrase"]
        later = [r for r in rows if r["kind"] == "later"]

        def mean(rs: list[dict[str, Any]], k: str) -> float:
            return float(np.nanmean([r["values"][k] for r in rs])) if rs else float("nan")

        s.findings.append(
            f"{len(items)} items in {len(corpus.topics())} topics. Highest similarity to any prior paper: paraphrased "
            f"papers {mean(para, 'semantic_max'):.3f}, generated ideas {mean(ideas, 'semantic_max'):.3f}, papers "
            f"published after the corpus {mean(later, 'semantic_max'):.3f}."
        )
        s.findings.append(
            f"Generated ideas: {mean(ideas, 'kg_known_pairs'):.0%} of their concept pairs already co-occur in some prior "
            f"paper (paraphrases {mean(para, 'kg_known_pairs'):.0%}, later papers {mean(later, 'kg_known_pairs'):.0%})."
        )
    return rd.path
