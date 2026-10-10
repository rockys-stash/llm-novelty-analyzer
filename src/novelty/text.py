"""Tokens, content words and candidate concept phrases (no external NLP models).

Candidate phrases follow RAKE (Rose et al., 2010): split the text at stopwords and punctuation; each
remaining run of one to three words is a candidate. Words are lower-cased and lightly normalised
(plural "s" removed) so "neural networks" and "neural network" are one concept.
"""

from __future__ import annotations

import re
from functools import lru_cache

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Words that say something about the writing, not the research content.
ACADEMIC = {
    "paper", "study", "studies", "approach", "approaches", "method", "methods", "propose", "proposed", "proposes",
    "present", "presents", "presented", "result", "results", "show", "shows", "shown", "new", "novel", "based",
    "using", "used", "use", "uses", "evaluate", "evaluated", "evaluation", "performance", "research", "idea",
    "work", "framework", "model", "models", "data", "existing", "different", "various", "significant",
    "significantly", "improve", "improved", "improves", "improvement", "effective", "effectively", "high",
    "higher", "low", "lower", "provide", "provides", "including", "compared", "demonstrate",
    "demonstrates", "experimental", "experiments", "experiment", "analysis", "problem", "problems", "task", "tasks",
    "achieve", "achieves", "achieved", "state", "art", "however", "also", "well", "way", "via", "first", "second",
    "address", "addresses", "aim", "aims", "investigate", "investigates", "explore", "explores", "potential",
    "key", "main", "important", "challenge", "challenges", "accuracy", "methodology", "techniques",
    "technique", "applications", "application", "develop", "developed", "development", "introduce", "introduces",
    "finally", "furthermore", "moreover", "specifically", "particular", "particularly", "e", "g", "et", "al",
}  # fmt: skip
STOP = frozenset(ENGLISH_STOP_WORDS) | ACADEMIC
_WORD = re.compile(r"[a-z][a-z0-9\-]*[a-z0-9]|[a-z]")
_SPLIT = re.compile(r"[.,;:!?()\[\]{}\"“”‘’/]|\s-\s|\n")


@lru_cache(maxsize=200_000)
def norm(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def words(text: str) -> list[str]:
    return [norm(w) for w in _WORD.findall(text.lower())]


def content_words(text: str) -> set[str]:
    return {w for w in words(text) if w not in STOP and len(w) > 2}


def phrases(text: str, max_len: int = 3) -> set[str]:
    """Candidate concept phrases (RAKE runs, one to ``max_len`` words; longer runs give their sub-runs)."""
    out: set[str] = set()
    for chunk in _SPLIT.split(text.lower()):
        run: list[str] = []
        for w in [*_WORD.findall(chunk), ""]:
            if w and w not in STOP and len(w) > 1:
                run.append(norm(w))
                continue
            for n in range(1, max_len + 1):
                for i in range(len(run) - n + 1):
                    ph = run[i : i + n]
                    if n == 1 and len(ph[0]) < 4:
                        continue
                    out.add(" ".join(ph))
            run = []
    return out
