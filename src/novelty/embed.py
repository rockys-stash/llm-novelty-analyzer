"""Sentence embeddings of papers and items, cached on disk by content hash.

Vectors are L2-normalised, so a dot product is the cosine similarity. The cache key includes the
model revision and a hash of every text, so a changed corpus or model can never reuse stale vectors.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "var" / "embeddings"
CONFIG = ROOT / "configs" / "embeddings.yaml"
Matrix = NDArray[np.float32]


def config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


@lru_cache(maxsize=2)
def _model(key: str) -> Any:
    import torch
    from sentence_transformers import SentenceTransformer

    cfg = config()
    torch.set_num_threads(int(os.environ.get("NOVELTY_TORCH_THREADS", cfg["threads"])))
    m = cfg["models"][key]
    return SentenceTransformer(m["name"], revision=m["revision"], device="cpu")


def encode(texts: Sequence[str], key: str = "minilm", cache: Path | None = CACHE) -> Matrix:
    m = config()["models"][key]
    h = hashlib.sha256(m["revision"].encode())
    for t in texts:
        h.update(hashlib.sha256(t.encode()).digest())
    path = (cache / key / f"{h.hexdigest()[:24]}.npy") if cache else None
    if path and path.exists():
        return np.load(path)
    vecs = _model(key).encode(list(texts), batch_size=int(config()["batch"]), normalize_embeddings=True,
                              show_progress_bar=False, convert_to_numpy=True).astype(np.float32)  # fmt: skip
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, vecs)
    return vecs
