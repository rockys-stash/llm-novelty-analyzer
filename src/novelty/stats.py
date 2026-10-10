"""Rank correlations, AUROC and bootstrap intervals over items."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

Array = NDArray[np.float64]


def spearman(x: Array, y: Array) -> float:
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5 or np.ptp(x[m]) == 0 or np.ptp(y[m]) == 0:
        return float("nan")
    return float(spearmanr(x[m], y[m]).statistic)


def auroc(neg: Array, pos: Array) -> float:
    """P(a positive scores above a negative), ties counted half; NaN values dropped."""
    neg, pos = neg[np.isfinite(neg)], pos[np.isfinite(pos)]
    if len(neg) == 0 or len(pos) == 0:
        return float("nan")
    y = np.r_[np.zeros(len(neg)), np.ones(len(pos))]
    return float(roc_auc_score(y, np.r_[neg, pos]))


def bootstrap(stat: Callable[[NDArray[np.int64]], float], n: int, reps: int, seed: int,
              strata: NDArray[np.int64] | None = None) -> dict[str, Any]:  # fmt: skip
    """Point estimate and 95% percentile interval, resampling items (within strata if given)."""
    rng = np.random.default_rng(seed)
    point = stat(np.arange(n))
    groups = [np.flatnonzero(strata == g) for g in np.unique(strata)] if strata is not None else [np.arange(n)]
    vals = []
    for _ in range(reps):
        idx = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups])
        vals.append(stat(idx))
    v = np.array(vals, dtype=np.float64)
    v = v[np.isfinite(v)]
    if len(v) < reps // 2:
        return {"value": point, "lo": None, "hi": None}
    return {"value": point, "lo": float(np.quantile(v, 0.025)), "hi": float(np.quantile(v, 0.975))}


def weighted_kappa(a: NDArray[np.int64], b: NDArray[np.int64], k: int = 5) -> float:
    """Cohen's kappa with quadratic weights for ratings 1..k."""
    o = np.zeros((k, k))
    for x, y in zip(a, b, strict=True):
        o[x - 1, y - 1] += 1
    if o.sum() == 0:
        return float("nan")
    o /= o.sum()
    e = np.outer(o.sum(axis=1), o.sum(axis=0))
    i, j = np.indices((k, k))
    w = (i - j) ** 2 / (k - 1) ** 2
    den = (w * e).sum()
    return float(1 - (w * o).sum() / den) if den > 0 else float("nan")
