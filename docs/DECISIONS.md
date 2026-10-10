# Decisions

**D1. Crossref journal articles as the literature.** The indicators need abstracts (semantic,
keyword and concept measures) and reference lists (citation overlap). OpenAlex and Semantic Scholar
returned HTTP 429 from this environment without an API key (2026-10-10); arXiv has no reference
lists. Crossref returns both for many journal articles through its public API. The cost: preprints,
conference papers and journals that do not deposit abstracts or references are missing, so every
indicator sees one slice of the literature.

**D2. A DOI manifest fixes the snapshot.** Crossref relevance ranking drifts as its index grows.
The first retrieval (2026-10-10) writes `data/corpus_manifest.json` with every DOI and a hash per
topic; `make data` rehydrates exactly those DOIs, and fails loudly if one no longer resolves.
Abstracts are publishers' text and are never committed; titles and DOIs are.

**D3. Controls written in the same format by the same model.** Comparing generated ideas with raw
abstracts would confound content with style (length, register, jargon), and embedding similarity is
sensitive to both. Every control is rewritten into the same Title/Idea format by Qwen3-4B (greedy
decoding), so controls and ideas differ in where their content came from. Generated ideas are
sampled (temperature 0.8, top-p 0.95, a seed per idea) so that eight ideas per topic are different
ideas.

**D4. "Later" papers as the positive control.** Papers published from March to October 2026, after
the corpus ends (2025) and after both models' training data, are novel *relative to the corpus* by
construction. They are not guaranteed to be novel in any absolute sense; the control only says what
an indicator should do with content that is not in the snapshot.

**D5. Corpus relevance is broad.** Crossref's relevance ranking for a topic query drifts away from
the topic in its lower ranks (for "uncertainty calibration deep neural networks", rank 500 is a
paper on apple-leaf disease detection with CNNs). We keep the ranking as returned rather than
filter it by hand; controls draw their sources from the 300 most relevant papers. The corpus is the
topic's neighbourhood in the index, not a curated bibliography.

**D6. Concepts without an external NLP model.** Candidate phrases follow RAKE (runs between
stopwords and punctuation), plural-normalised, with a topic-specificity test for single words
against the other five topics. This is transparent and needs no model download, at the cost of some
noise ("sampled", "saved" survive as concepts). Concept lists are shown in the console so a reader
can judge them.

**D7. Citation overlap is coupling of the prior art, not of the idea.** A generated idea has no
reference list. The indicator measures how much the idea's 10 nearest papers cite the same sources:
high coupling means the idea sits inside one established literature, low coupling that its nearest
neighbours come from different literatures. Papers without deposited references are skipped in the
pairwise mean.

**D8. Judgments read from token distributions.** The model judges answer the human rubric; their
score is the expected value of the next-token distribution over the digits 1–5, so a judgment is
deterministic and keeps its uncertainty. Qwen's tokenizer splits " 3" into a space and a digit, so
for Qwen the prompt ends with "Novelty: " and the digit tokens are read; for Phi-4-mini " 3" is one
token. Judges see only the topic and the item.

**D9. The human study is pending; the pilot is model judges.** The spec asks for human evaluators,
or a small clearly labelled pilot if a full study cannot be run. No human annotators were available
in this build. The annotation interface and protocol are complete and tested; the E3 analysis runs
on human scores as soon as 20 items have one. The pilot uses two local language models as judges;
it is reported separately, labelled as model judgments everywhere, and never pooled with or
presented as human data.

**D10. Thresholds for the E4 groups come from the controls.** A generated idea is a
"near-duplicate" if its highest similarity reaches the 10th percentile of the paraphrase controls,
and a "known combination" if its share of known concept pairs reaches the median of the
recombination controls. Setting thresholds on the ideas themselves would make the group sizes
arbitrary.

**D11. Escaped markup in Crossref records.** Some records escape their inline markup
(`&lt;i&gt;in situ&lt;/i&gt;`). The first cleaner removed tags before unescaping and left `<i>` in 55
of 6,137 records. The cleaner now removes JATS tags, unescapes, then removes only inline formatting
tags (so "&lt;5 °C" survives as "<5 °C"). The fix was made while item generation was running; the
generation prompts for any control written from one of those 55 papers contained the literal tags.

**D12. Local generation threads.** Items were generated while Project 07's language-model run held
three cores; generation started on one thread and resumed with more once the cores were free. Thread
count changes speed, not output, for greedy decoding; sampled ideas use llama.cpp's seeded sampler.
