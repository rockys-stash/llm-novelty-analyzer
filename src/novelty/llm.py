"""Local open-weights language models through llama.cpp: sampled generation and scored ratings.

Both models run on CPU from GGUF files pinned by SHA-256 (``configs/models.yaml``). Generation uses
llama.cpp's sampler with an explicit seed, so a rerun with the same file and build reproduces the
text. Ratings read the next-token distribution over the digits 1-5 instead of sampling a digit, so a
judgment is a deterministic expected score with its full distribution kept.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any, cast

import numpy as np
import yaml
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
CONFIG = ROOT / "configs" / "models.yaml"


def config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_models(names: list[str] | None = None) -> list[Path]:
    cfg = config()
    MODELS.mkdir(exist_ok=True)
    out = []
    for name in names or list(cfg["models"]):
        m = cfg["models"][name]
        path = MODELS / m["file"]
        if not path.exists():
            tmp = path.with_suffix(".part")
            with urllib.request.urlopen(m["url"], timeout=120) as r, tmp.open("wb") as f:
                shutil.copyfileobj(r, f)
            tmp.replace(path)
        if sha256(path) != m["sha256"]:
            raise ValueError(f"{path.name}: checksum does not match configs/models.yaml; delete it and retry")
        out.append(path)
    return out


class LocalModel:
    def __init__(self, name: str, seed: int = 0) -> None:
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Jinja2ChatFormatter

        cfg = config()
        m = cfg["models"][name]
        path = MODELS / m["file"]
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing: run `make models`")
        self.name, self.label, self.sha256 = name, m["label"], m["sha256"]
        self.threads = int(os.environ.get("NOVELTY_LLM_THREADS", cfg["threads"]))
        self.llm = Llama(model_path=str(path), n_ctx=cfg["n_ctx"], n_threads=self.threads,
                         n_threads_batch=self.threads, logits_all=False, verbose=False, seed=seed)  # fmt: skip
        md = self.llm.metadata
        self._fmt = Jinja2ChatFormatter(
            template=md["tokenizer.chat_template"],
            eos_token=self.llm.detokenize([self.llm.token_eos()]).decode(errors="ignore"),
            bos_token=self.llm.detokenize([self.llm.token_bos()]).decode(errors="ignore"),
            add_generation_prompt=True,
        )
        # " 3" is one token for some tokenizers; others (Qwen) split digits from the space before them.
        try:
            self.digit_ids, self.digit_sep = [self._single_token(f" {d}") for d in "12345"], ""
        except ValueError:
            self.digit_ids, self.digit_sep = [self._single_token(d) for d in "12345"], " "

    def _single_token(self, s: str) -> int:
        ids = self.llm.tokenize(s.encode(), add_bos=False, special=False)
        if len(ids) != 1:
            raise ValueError(f"{s!r} is not a single token for this model")
        return int(ids[0])

    def render(self, messages: list[dict[str, str]], prefix: str = "") -> list[int]:
        prompt = self._fmt(messages=cast(Any, messages)).prompt + prefix
        return list(self.llm.tokenize(prompt.encode(), add_bos=False, special=True))

    def generate(self, messages: list[dict[str, str]], prefix: str, max_tokens: int, temperature: float,
                 seed: int) -> str:  # fmt: skip
        """Sample a continuation of the assistant turn after ``prefix``."""
        self.llm.set_seed(seed)
        out = self.llm.create_completion(prompt=self.render(messages, prefix), max_tokens=max_tokens,
                                         temperature=temperature, top_p=0.95, top_k=40, seed=seed)  # fmt: skip
        return prefix + str(cast(dict[str, Any], out)["choices"][0]["text"])

    def logits_after(self, tokens: list[int]) -> NDArray[np.float64]:
        """Evaluate ``tokens`` reusing the longest cached prefix; return the next-token logits."""
        import llama_cpp

        llm = self.llm
        cached = list(llm._input_ids[: llm.n_tokens])
        k = 0
        for a, b in zip(cached, tokens, strict=False):
            if a != b:
                break
            k += 1
        k = min(k, len(tokens) - 1)
        llm.n_tokens = k
        llm.eval(tokens[k:])
        ptr = llama_cpp.llama_get_logits_ith(llm.ctx, -1)
        arr = np.ctypeslib.as_array(ctypes.cast(ptr, ctypes.POINTER(ctypes.c_float)), shape=(llm.n_vocab(),))
        return arr.astype(np.float64).copy()

    def rate(self, messages: list[dict[str, str]], fields: list[str]) -> list[NDArray[np.float64]]:
        """Distribution over 1-5 for each field, answered in order ("Field: d" lines)."""
        prefix, out = "", []
        for f in fields:
            prefix += f"{f}:{self.digit_sep}"
            logits = self.logits_after(self.render(messages, prefix))[self.digit_ids]
            p = np.exp(logits - np.max(logits))
            p /= p.sum()
            out.append(p)
            prefix += f"{'' if self.digit_sep else ' '}{int(np.argmax(p)) + 1}\n"
        return out
