"""E3 Indicators against judgments of novelty.

The research question: do computational indicators correlate with judgments of novelty? Two
sources of judgments are analysed separately and never pooled:

* **human annotations** (the study): collected with the console's annotation page under
  ``docs/ANNOTATION_PROTOCOL.md``. Reported only when at least ``min_human_items`` items have a score;
  otherwise the human analysis is *pending* and says how many scores exist.
* **model judges** (a pilot, not human data): the same rubric answered by two local language models.

For each source: Spearman correlation of each indicator (oriented so higher = more novel) with the
mean novelty score, over all items and over generated ideas only, with a bootstrap interval. For
the model judges also: agreement between the two judges, how each scores the control kinds, and
whether a judge favours ideas written by its own model.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from novelty import annotations as human_store
from novelty import indicators as I
from novelty import judge
from novelty.experiments.common import ci, fmt, latest_run, result_dir, table
from novelty.items import KIND_LABEL, KINDS
from novelty.stats import auroc, bootstrap, spearman, weighted_kappa

DESCRIPTION = (
    "Spearman correlation of each indicator with human (pending until collected) and model-judge novelty scores"
)


def _rho_of(x: np.ndarray, y: np.ndarray) -> Callable[[np.ndarray], float]:
    return lambda b: spearman(x[b], y[b])


def correlations(rows: list[dict[str, Any]], scores: dict[str, float], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for subset in ("all", "idea"):
        rs = [r for r in rows if r["id"] in scores and (subset == "all" or r["kind"] == "idea")]
        if len(rs) < 5:
            continue
        y = np.array([scores[r["id"]] for r in rs])
        for k in I.INDICATORS:
            x = np.array([-I.DIRECTION[k] * r["values"][k] for r in rs], dtype=np.float64)
            rho = bootstrap(_rho_of(x, y), len(rs), int(cfg["bootstrap"]), int(cfg["seed"]))
            out.append({"subset": subset, "indicator": k, "n": len(rs), "rho": rho})
    return out


def run(cfg: dict[str, Any], results: Path | None = None, items_path: Path | None = None) -> Path:
    e1 = latest_run("e1_indicators", results)
    rows: list[dict[str, Any]] = json.loads((e1 / "items.json").read_text(encoding="utf-8"))
    ids = {r["id"] for r in rows}
    kind = {r["id"]: r["kind"] for r in rows}
    model_of = {r["id"]: r["model"] for r in rows}
    with result_dir("e3_judgments", cfg, DESCRIPTION, results) as (rd, s):
        # human study
        human = [h for h in human_store.latest() if h["item"] in ids]
        h_items: dict[str, list[int]] = {}
        for h in human:
            h_items.setdefault(h["item"], []).append(h["novelty"])
        annotators = sorted({h["annotator"] for h in human})
        status = "complete" if len(h_items) >= int(cfg["min_human_items"]) else "pending"
        human_out: dict[str, Any] = {"status": status, "records": len(human), "items": len(h_items), "annotators": len(annotators),
                     "correlations": correlations(rows, {k: float(np.mean(v)) for k, v in h_items.items()}, cfg)
                     if status == "complete" else []}  # fmt: skip
        rd.write_json("human.json", human_out)
        # model judges
        js = [j for j in judge.read_judgments() if j["item"] in ids]
        judges = sorted({j["judge"] for j in js})
        per: dict[str, dict[str, dict[str, Any]]] = {
            name: {j["item"]: j for j in js if j["judge"] == name} for name in judges
        }
        common = sorted(set.intersection(*(set(v) for v in per.values()))) if per else []
        mean_novelty = {i: float(np.mean([per[n][i]["novelty"] for n in judges])) for i in common}
        model_out: dict[str, Any] = {"judges": judges, "items": len(common),
                                     "correlations": correlations(rows, mean_novelty, cfg), "per_judge": {}}  # fmt: skip
        for name in judges:
            sc = {i: per[name][i]["novelty"] for i in common}
            by_kind = {k: float(np.mean([v for i, v in sc.items() if kind[i] == k])) for k in KINDS
                       if any(kind[i] == k for i in sc)}  # fmt: skip
            own = [v for i, v in sc.items() if kind[i] == "idea" and model_of[i] == name]
            other = [v for i, v in sc.items() if kind[i] == "idea" and model_of[i] != name]
            para = np.array([v for i, v in sc.items() if kind[i] == "paraphrase"])
            later = np.array([v for i, v in sc.items() if kind[i] == "later"])
            model_out["per_judge"][name] = {
                "novelty_by_kind": by_kind,
                "auroc_paraphrase_later": auroc(para, later),
                "own_ideas": float(np.mean(own)) if own else None,
                "other_ideas": float(np.mean(other)) if other else None,
                "relevance": float(np.mean([per[name][i]["relevance"] for i in common])),
                "meaningfulness": float(np.mean([per[name][i]["meaningfulness"] for i in common])),
                "correlations": correlations(rows, sc, cfg),
            }
        if len(judges) == 2:
            a, b = judges
            agree: dict[str, Any] = {}
            for crit in ("novelty", "relevance", "meaningfulness"):
                x = np.array([per[a][i][crit] for i in common])
                y = np.array([per[b][i][crit] for i in common])
                xa = np.array([int(np.argmax(per[a][i][crit + "_dist"])) + 1 for i in common])
                ya = np.array([int(np.argmax(per[b][i][crit + "_dist"])) + 1 for i in common])
                agree[crit] = {"spearman": spearman(x, y), "weighted_kappa": weighted_kappa(xa, ya)}
            model_out["agreement"] = agree
        rd.write_json("model_judges.json", model_out)

        s.title = "E3 Indicators against judgments of novelty"
        s.question = "Do the computational indicators correlate with judgments of novelty?"
        s.notes.append(f"Human study: {status}. {len(human)} annotation records from {len(annotators)} annotators on "
                       f"{len(h_items)} items (analysis needs at least {cfg['min_human_items']} items).")  # fmt: skip
        s.notes.append("Model judges are language models answering the human rubric. They are a pilot that exercises "
                       "the analysis; they are not human judgments and do not answer the research question.")  # fmt: skip
        for label, res in (("Human", human_out), ("Model judges (pilot)", model_out)):
            corr = res["correlations"]
            if not corr:
                continue
            s.tables.append(table(f"corr_{label[:5].lower()}", f"{label}: Spearman ρ of each indicator (higher = more novel) with mean novelty score, 95% bootstrap interval",
                [("indicator", "Indicator", "l"), ("all", "All items", "r"), ("idea", "Generated ideas only", "r")],
                [{"indicator": I.LABEL[k], **{c["subset"]: ci(c["rho"], 2) for c in corr if c["indicator"] == k}}
                 for k in I.INDICATORS]))  # fmt: skip
        if judges:
            s.tables.append(table("judges", "Model judges: mean novelty (1–5) by item kind; AUROC paraphrase → later; own-model preference",
                [("judge", "Judge", "l")] + [(k, KIND_LABEL[k], "r") for k in KINDS] +
                [("auc", "AUROC paraphrase → later", "r"), ("own", "Own ideas", "r"), ("other", "Other model's ideas", "r")],
                [{"judge": n, **{k: fmt(v["novelty_by_kind"].get(k), 2) for k in KINDS}, "auc": fmt(v["auroc_paraphrase_later"], 2),
                  "own": fmt(v["own_ideas"], 2), "other": fmt(v["other_ideas"], 2)} for n, v in model_out["per_judge"].items()]))  # fmt: skip
            corr = [c for c in model_out["correlations"] if c["subset"] == "all"]
            if corr:
                best = max(corr, key=lambda c: abs(c["rho"]["value"]) if c["rho"]["value"] == c["rho"]["value"] else -1)
                s.findings.append(f"Model-judge pilot over {len(common)} items: strongest indicator {I.LABEL[best['indicator']]} "
                                  f"(ρ = {ci(best['rho'], 2)}).")  # fmt: skip
            if "agreement" in model_out:
                ag = model_out["agreement"]["novelty"]
                s.findings.append(f"Agreement between the two model judges on novelty: Spearman {fmt(ag['spearman'], 2)}, "
                                  f"quadratic-weighted κ {fmt(ag['weighted_kappa'], 2)}.")  # fmt: skip
        s.findings.append(f"Human study {status}: {len(h_items)} items scored by {len(annotators)} annotators.")
    return rd.path
