"""Concept vocabulary and co-occurrence graph of a topic's literature.

A *concept* is a candidate phrase (``text.phrases``) that appears in at least ``min_df`` corpus papers
and in at most ``max_share`` of them (more common phrases are the topic itself, not a concept in it).
A single word must also be specific to the topic: at least ``specificity`` times more frequent in this
topic's papers than in the other topics' papers (so "additional" or "called" are not concepts, while
"overconfidence" is). Multi-word phrases need no such test.
The knowledge graph links two concepts when they occur in the same paper; edge weight = number of
such papers. An item's concepts are its candidate phrases that are in the vocabulary; its *new
phrases* are multi-word candidates that no corpus paper contains.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import combinations

from novelty.text import phrases


@dataclass
class Vocabulary:
    df: dict[str, int]  # papers containing the concept
    n_docs: int
    doc_concepts: list[frozenset[str]]
    all_phrases: frozenset[str]  # every candidate phrase seen in the corpus, concept or not
    pair_counts: Counter[tuple[str, str]] = field(default_factory=Counter)

    def concepts_of(self, text: str) -> set[str]:
        return {p for p in phrases(text) if p in self.df}

    def new_phrases(self, text: str) -> set[str]:
        return {p for p in phrases(text) if " " in p and p not in self.all_phrases}

    def cooccur(self, a: str, b: str) -> int:
        return self.pair_counts.get((a, b) if a < b else (b, a), 0)

    def npmi(self, a: str, b: str) -> float:
        """Normalised pointwise mutual information of two concepts over papers, in [-1, 1]; -1 if never together."""
        n_ab = self.cooccur(a, b)
        if n_ab == 0:
            return -1.0
        p_ab = n_ab / self.n_docs
        p_a, p_b = self.df[a] / self.n_docs, self.df[b] / self.n_docs
        if p_ab >= 1.0:
            return 1.0
        return math.log(p_ab / (p_a * p_b)) / -math.log(p_ab)


def build(texts: Sequence[str], background: Sequence[str] = (), min_df: int = 3, max_share: float = 0.3,
          specificity: float = 3.0) -> Vocabulary:  # fmt: skip
    docs = [phrases(t) for t in texts]
    df_all: Counter[str] = Counter()
    for d in docs:
        df_all.update(d)
    bg: Counter[str] = Counter()
    for t in background:
        bg.update(w for w in phrases(t, max_len=1))
    n_bg = max(len(background), 1)
    limit = max_share * len(docs)

    def specific(p: str, c: int) -> bool:
        if " " in p or not background:
            return True
        return c / len(docs) >= specificity * (bg[p] + 1) / n_bg

    df = {p: c for p, c in df_all.items() if min_df <= c <= limit and specific(p, c)}
    doc_concepts = [frozenset(p for p in d if p in df) for d in docs]
    pairs: Counter[tuple[str, str]] = Counter()
    for dc in doc_concepts:
        pairs.update(combinations(sorted(dc), 2))
    return Vocabulary(df, len(docs), doc_concepts, frozenset(df_all), pairs)
