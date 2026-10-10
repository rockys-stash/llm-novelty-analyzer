"""Novelty indicators of an item against its topic's prior-art corpus.

Each indicator measures closeness to existing literature in one way; none of them *is* novelty
(the study asks whether they track judgments of it). Higher values mean closer to prior art, except
``new_phrase_share`` and the knowledge-graph pair measures, whose directions are noted.

| Indicator | Definition |
|---|---|
| semantic_max | Highest cosine similarity of the item's embedding to any corpus paper. |
| semantic_top10 | Mean cosine similarity to the 10 nearest papers. |
| keyword_overlap | Highest Jaccard overlap of content words with any corpus paper. |
| concept_overlap | Share of the item's concepts that appear in its 10 nearest papers. |
| citation_overlap | Mean pairwise Jaccard overlap of the reference lists of the 10 nearest papers (bibliographic coupling of the item's prior art). |
| kg_known_pairs | Share of pairs of the item's concepts that already co-occur in some corpus paper. |
| kg_npmi | Mean normalised PMI of those concept pairs (-1 for a pair never seen together). |
| new_phrase_share | Share of the item's multi-word phrases that no corpus paper contains (higher = more new wording). |
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np
from numpy.typing import NDArray

from novelty import concepts as C
from novelty import corpus as K
from novelty import embed
from novelty.items import Item
from novelty.text import content_words, phrases

INDICATORS = ["semantic_max", "semantic_top10", "keyword_overlap", "concept_overlap", "citation_overlap",
              "kg_known_pairs", "kg_npmi", "new_phrase_share"]  # fmt: skip
LABEL = {"semantic_max": "Semantic similarity (max)", "semantic_top10": "Semantic similarity (top 10)",
         "keyword_overlap": "Keyword overlap", "concept_overlap": "Concept overlap",
         "citation_overlap": "Citation overlap", "kg_known_pairs": "Known concept pairs (graph)",
         "kg_npmi": "Concept-pair association (graph)", "new_phrase_share": "New phrases"}  # fmt: skip
# +1: higher means closer to prior art (less novel by that indicator); -1: higher means more novel.
DIRECTION = {k: 1 for k in INDICATORS} | {"new_phrase_share": -1}
NEIGHBOURS = 10


@dataclass
class TopicIndex:
    topic: str
    papers: tuple[K.Paper, ...]
    vectors: NDArray[np.float32]
    vocab: C.Vocabulary
    words: list[frozenset[str]]
    refs: list[frozenset[str]]


def build_index(topic: str, embedding: str = "minilm", limit: int | None = None) -> TopicIndex:
    papers = K.load(topic)[:limit] if limit else K.load(topic)
    texts = [p.text for p in papers]
    background = [p.text for t in K.topics() if t != topic for p in (K.load(t)[:limit] if limit else K.load(t))]
    return TopicIndex(topic, papers, embed.encode(texts, embedding), C.build(texts, background),
                      [frozenset(content_words(t)) for t in texts], [frozenset(p.references) for p in papers])  # fmt: skip


def _jaccard(a: frozenset[str] | set[str], b: frozenset[str] | set[str]) -> float:
    u = len(a | b)
    return len(a & b) / u if u else float("nan")


def score(item: Item, vec: NDArray[np.float32], ix: TopicIndex) -> dict[str, Any]:
    sims = ix.vectors @ vec
    top = np.argsort(-sims, kind="stable")[:NEIGHBOURS]
    words = content_words(item.full)
    item_concepts = ix.vocab.concepts_of(item.full)
    near_concepts = frozenset().union(*(ix.vocab.doc_concepts[i] for i in top))
    pairs = list(combinations(sorted(item_concepts), 2))
    ref_pairs = [_jaccard(ix.refs[i], ix.refs[j]) for i, j in combinations(top.tolist(), 2) if ix.refs[i] or ix.refs[j]]
    multi = {p for p in phrases(item.full) if " " in p}
    kw = [_jaccard(words, w) for w in ix.words]
    values = {
        "semantic_max": float(sims[top[0]]),
        "semantic_top10": float(sims[top].mean()),
        "keyword_overlap": float(np.nanmax(kw)),
        "concept_overlap": len(item_concepts & near_concepts) / len(item_concepts) if item_concepts else float("nan"),
        "citation_overlap": float(np.mean(ref_pairs)) if ref_pairs else float("nan"),
        "kg_known_pairs": float(np.mean([ix.vocab.cooccur(a, b) > 0 for a, b in pairs])) if pairs else float("nan"),
        "kg_npmi": float(np.mean([ix.vocab.npmi(a, b) for a, b in pairs])) if pairs else float("nan"),
        "new_phrase_share": len(ix.vocab.new_phrases(item.full)) / len(multi) if multi else float("nan"),
    }
    neighbours = [{"doi": ix.papers[i].doi, "title": ix.papers[i].title, "year": ix.papers[i].year,
                   "venue": ix.papers[i].venue, "similarity": float(sims[i]),
                   "shared_concepts": sorted(item_concepts & ix.vocab.doc_concepts[i]),
                   "source": ix.papers[i].doi in item.sources} for i in top]  # fmt: skip
    unseen = [(a, b) for a, b in pairs if ix.vocab.cooccur(a, b) == 0]
    return {
        "values": values,
        "concepts": sorted(item_concepts),
        "new_phrases": sorted(ix.vocab.new_phrases(item.full)),
        "unseen_pairs": unseen[:40],
        "n_pairs": len(pairs),
        "neighbours": neighbours,
        "source_ranks": source_ranks(item, sims, ix),
    }


def source_ranks(item: Item, sims: NDArray[np.float32], ix: TopicIndex) -> dict[str, int]:
    """Rank (1 = most similar) of each corpus paper the item was written from."""
    order = np.argsort(-sims, kind="stable")
    rank = np.empty(len(order), dtype=np.int64)
    rank[order] = np.arange(1, len(order) + 1)
    pos = {p.doi: k for k, p in enumerate(ix.papers)}
    return {d: int(rank[pos[d]]) for d in item.sources if d in pos}


def compute(items: list[Item], embedding: str = "minilm", limit: int | None = None) -> dict[str, dict[str, Any]]:
    """Indicators and prior-art map for every item, against its own topic's corpus."""
    out: dict[str, dict[str, Any]] = {}
    for topic in dict.fromkeys(i.topic for i in items):
        mine = [i for i in items if i.topic == topic]
        ix = build_index(topic, embedding, limit)
        vecs = embed.encode([i.full for i in mine], embedding)
        for it, v in zip(mine, vecs, strict=True):
            out[it.id] = score(it, v, ix)
    return out


def corpus_stats(topic: str, embedding: str = "minilm") -> dict[str, Any]:
    ix = build_index(topic, embedding)
    refs = [len(r) for r in ix.refs]
    return {"topic": topic, "label": K.topics()[topic], "papers": len(ix.papers),
            "years": [min(p.year or 9999 for p in ix.papers), max(p.year or 0 for p in ix.papers)],
            "concepts": len(ix.vocab.df), "edges": len(ix.vocab.pair_counts),
            "median_references": float(np.median(refs)), "later": len(K.load(topic, "later"))}  # fmt: skip
