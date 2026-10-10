import pytest

from novelty import concepts
from novelty.items import parse_reply
from novelty.text import content_words, norm, phrases


def test_phrases_split_at_stopwords_and_normalise_plurals() -> None:
    p = phrases("We propose temperature scaling for deep neural networks, evaluated on image classification.")
    assert {"temperature scaling", "deep neural network", "image classification"} <= p
    assert not any("propose" in x or "evaluated" in x for x in p)
    assert norm("networks") == "network" and norm("studies") == "study" and norm("class") == "class"
    assert "neural" in content_words("Neural networks are used.") and "used" not in content_words(
        "Neural networks are used."
    )


def test_vocabulary_keeps_specific_concepts_and_counts_pairs() -> None:
    texts = ["temperature scaling calibrates deep ensemble outputs"] * 3 + ["focal loss improves calibration error"] * 3 + [
        "isotonic regression and temperature scaling compared"] * 2 + ["unrelated soil moisture sensing"] * 6  # fmt: skip
    background = ["additional results were obtained"] * 10 + ["soil moisture sensing networks"] * 10
    v = concepts.build(texts, background, min_df=2, max_share=0.5)
    assert "temperature scaling" in v.df and "focal loss" in v.df
    assert "soil" not in v.df  # a single word as common in the background is not specific to the topic
    assert v.cooccur("deep ensemble", "temperature scaling") == 3
    assert v.npmi("focal loss", "temperature scaling") == -1.0
    assert v.npmi("deep ensemble", "temperature scaling") > 0
    assert {"temperature scaling", "focal loss"} <= v.concepts_of("Temperature scaling with focal loss")
    assert "with" not in " ".join(v.concepts_of("Temperature scaling with focal loss"))
    assert v.new_phrases("tree ring calibration of crop yield") == {"tree ring calibration", "crop yield", "tree ring",
                                                                   "ring calibration"}  # fmt: skip


@pytest.mark.parametrize(
    ("reply", "ok"),
    [
        ("Title: Calibrated forests\nIdea: " + "We do this. " * 8, True),
        ("Title: **Calibrated forests**\n\nIdea: " + "word " * 25, True),
        ("Here is an idea about forests and calibration.", False),
        ("Title: Too short\nIdea: Just this.", False),
    ],
)
def test_parse_reply(reply: str, ok: bool) -> None:
    parsed = parse_reply(reply)
    assert (parsed is not None) == ok
    if parsed:
        assert parsed[0] == "Calibrated forests" and "**" not in parsed[0]
