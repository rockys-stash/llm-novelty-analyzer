import json

import numpy as np
import pytest

from novelty import concepts, corpus, generate
from novelty import indicators as I
from novelty.experiments.common import ROOT, load_config
from novelty.items import Item
from tests.conftest import needs_data


def _index() -> I.TopicIndex:
    papers = tuple(
        corpus.Paper(f"10.1/p{i}", t, "abstract " * 40, 2020, "J", refs)
        for i, (t, refs) in enumerate(
            [
                ("temperature scaling for deep ensemble calibration", ["r1", "r2"]),
                ("focal loss reduces calibration error", ["r1", "r3"]),
                ("soil moisture sensing with drones", ["r9"]),
            ]
        )
    )
    vecs = np.eye(3, dtype=np.float32)
    texts = [p.text for p in papers] * 3
    vocab = concepts.build(texts, min_df=2, max_share=0.9)
    from novelty.text import content_words

    return I.TopicIndex("calibration", papers, vecs, vocab, [frozenset(content_words(p.text)) for p in papers],
                        [frozenset(p.references) for p in papers])  # fmt: skip


def test_score_maps_prior_art_and_ranks_sources() -> None:
    ix = _index()
    it = Item(
        "x", "calibration", "paraphrase", "m", "Temperature scaling", "for deep ensemble calibration " * 5, ["10.1/p0"]
    )
    r = I.score(it, np.array([0.9, 0.3, 0.0], dtype=np.float32), ix)
    assert r["neighbours"][0]["doi"] == "10.1/p0" and r["neighbours"][0]["source"] is True
    assert r["source_ranks"] == {"10.1/p0": 1}
    v = r["values"]
    assert v["semantic_max"] == pytest.approx(0.9) and v["concept_overlap"] == 1.0
    assert v["citation_overlap"] == pytest.approx((1 / 3 + 0 + 0) / 3)  # p0-p1 share r1 of {r1,r2,r3}
    assert "temperature scaling" in r["concepts"]


def test_generation_plan_is_deterministic_and_balanced(monkeypatch: pytest.MonkeyPatch) -> None:
    papers = tuple(corpus.Paper(f"10.1/{i}", f"Paper {i}", "words " * 50, 2020, "J") for i in range(400))
    monkeypatch.setattr(corpus, "load", lambda topic, part="corpus": papers[:40] if part == "later" else papers)
    cfg = load_config(ROOT / "configs" / "generate.yaml")
    a, b = generate.plan(cfg), generate.plan(cfg)
    assert [j["id"] for j in a] == [j["id"] for j in b] and [j["sources"] for j in a] == [j["sources"] for j in b]
    per_topic = len(a) // len(corpus.topics())
    assert per_topic == 2 * 8 + 6 + 6 + 6
    ideas = [j for j in a if j["kind"] == "idea"]
    assert len({(j["topic"], j["model"], j["seed"]) for j in ideas}) == len(ideas)  # every idea has its own seed
    rec = [j for j in a if j["kind"] == "recombination"]
    assert all(len(set(j["sources"])) == 2 for j in rec)
    assert "Title:" in a[0]["prompt"] and "Idea:" in a[0]["prompt"]


@needs_data
def test_corpus_matches_its_manifest() -> None:
    m = json.loads(corpus.MANIFEST.read_text())
    for t in corpus.topics():
        for part in ("corpus", "later"):
            papers = corpus.load(t, part)
            assert [p.doi for p in papers] == m["topics"][t][part]["dois"]
            years = {p.year for p in papers if p.year is not None}
            assert (max(years) <= 2025) if part == "corpus" else (min(years) >= 2026)
            assert all(len(p.abstract.split()) >= 40 and "<" not in p.title for p in papers)
