from pathlib import Path

import numpy as np
import pytest

from novelty import annotations
from novelty.stats import auroc, bootstrap, spearman, weighted_kappa


def test_auroc_spearman_kappa() -> None:
    assert auroc(np.array([0.1, 0.2]), np.array([0.8, 0.9])) == 1.0
    assert auroc(np.array([0.5, np.nan]), np.array([0.5])) == 0.5
    assert spearman(np.arange(10.0), np.arange(10.0) ** 2) == pytest.approx(1.0)
    assert np.isnan(spearman(np.ones(10), np.arange(10.0)))
    a = np.array([1, 2, 3, 4, 5, 5])
    assert weighted_kappa(a, a) == pytest.approx(1.0)
    assert weighted_kappa(a, 6 - a) < 0


def test_bootstrap_interval_contains_the_mean() -> None:
    x = np.random.default_rng(0).normal(3, 1, 200)
    b = bootstrap(lambda i: float(x[i].mean()), 200, 300, 0)
    assert b["lo"] < 3 < b["hi"] and b["value"] == pytest.approx(x.mean())
    strata = np.array([0] * 100 + [1] * 100)
    s = bootstrap(lambda i: float((strata[i] == 1).mean()), 200, 50, 0, strata)
    assert s["lo"] == s["hi"] == 0.5  # stratified resampling keeps the group sizes


def test_annotation_validation_and_latest(tmp_path: Path) -> None:
    ok = {"annotator": "rater_1", "item": "x", "novelty": 4, "relevance": 5, "meaningfulness": 3, "comment": " fine "}
    rec = annotations.validate(ok, {"x"})
    assert rec["comment"] == "fine"
    for bad in ({**ok, "annotator": "a b"}, {**ok, "item": "y"}, {**ok, "novelty": 6}, {**ok, "novelty": True},
                {**ok, "relevance": "5"}, {**ok, "comment": "x" * 1001}, {**ok, "seconds": -1}):  # fmt: skip
        with pytest.raises(annotations.InvalidAnnotationError):
            annotations.validate(bad, {"x"})
    store = tmp_path / "h.jsonl"
    annotations.append(rec, store)
    annotations.append({**rec, "novelty": 2}, store)
    latest = annotations.latest(store)
    assert len(latest) == 1 and latest[0]["novelty"] == 2
