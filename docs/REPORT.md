# Report: are LLM-generated research ideas new, or recombinations?

Numbers are quoted from `docs/generated/results.md`, generated from the result directories
`e1_indicators/20261010T213114Z-a39f542`, `e2_validity/20261010T213844Z-a39f542`,
`e3_judgments/20261010T213957Z-a39f542`, `e4_disagreement/20261010T222402Z-a900ca1` and
`e5_robustness/20261010T214017Z-a39f542` (all on clean commits). Intervals are 95% bootstrap
intervals over items.

## 1. Question and set-up

Language models can write fluent research ideas. Whether those ideas are *new* is a different
question, and similarity to prior papers does not settle it: an idea can be worded unlike any paper
and still pair concepts that are routinely paired, or sit close to a paper and still add something.
The study therefore asks two things: do computational indicators of novelty behave sensibly on
material whose relation to the literature is known, and do they agree with judgments of novelty?

**Literature.** Six topics (uncertainty calibration, battery state of health, federated-learning
privacy, CRISPR off-target prediction, urban heat islands, misinformation detection); per topic
967–993 Crossref journal articles from 2015–2025 with abstract and reference list (5,897 in all),
fixed by a committed DOI manifest (D1, D2).

**Items (204).** 96 generated ideas: Qwen3-4B-Instruct and Phi-4-mini-instruct, 8 per topic each,
run locally. 108 controls, written by Qwen3-4B in the same Title/Idea format (D3): 36 *paraphrases*
of a corpus paper, 36 *recombinations* of two corpus papers, 36 *later papers* (published March–
October 2026, after the corpus) restated as ideas (D4).

**Indicators (8).** Highest and top-10 mean semantic similarity (embeddings), keyword overlap,
concept overlap with the nearest papers, citation overlap (bibliographic coupling of the nearest
papers, D7), share of the item's concept pairs already co-occurring in some paper and their mean
association (a concept co-occurrence graph per topic), and the share of multi-word phrases no paper
contains. All are oriented so that higher means more novel when compared.

**Judgments.** The human study (blind 1–5 ratings of novelty, relevance, meaningfulness; protocol
in `ANNOTATION_PROTOCOL.md`) is built but **pending**: no annotations have been collected. A
model-judge pilot, with both local models answering the same rubric, exercises the analysis (D8,
D9). It is not a substitute for human judgment.

## 2. Results by research question

### RQ1. How close are generated ideas to the literature?

Highest similarity to any prior paper: paraphrases 0.882 [0.865, 0.897], recombinations 0.779,
generated ideas 0.748 [0.729, 0.767], later papers 0.744 [0.717, 0.768]. Generated ideas are as
far from the literature as genuinely later papers by this measure, not between restatements and
later papers as hypothesised. On the concept graph the picture changes: 71% of a generated idea's
concept pairs already co-occur in some prior paper, against 66% for later papers and 80% for
paraphrases.

### RQ2. Do the indicators pass a test with known answers?

Paraphrase vs later paper is the cleanest test: one restates the corpus, the other postdates it.

| Indicator | AUROC (paraphrase → later) |
|---|---:|
| Semantic similarity (max) | 0.96 [0.91, 0.99] |
| Keyword overlap | 0.95 [0.89, 1.00] |
| Known concept pairs (graph) | 0.85 [0.76, 0.92] |
| Concept-pair association (graph) | 0.85 [0.76, 0.93] |
| Concept overlap | 0.84 [0.75, 0.92] |
| New phrases | 0.80 [0.69, 0.89] |
| Semantic similarity (top 10) | 0.62 [0.48, 0.75] |
| Citation overlap | 0.51 [0.38, 0.65] |

Six indicators pass; top-10 similarity and citation overlap do not beat chance, so the hypothesis
that every indicator passes is rejected. Recombinations are harder: against later papers the best
indicator (keyword overlap) reaches 0.77 [0.67, 0.86], and semantic similarity only 0.65. The
prior-art map finds a paraphrase's source paper first for 89% of paraphrases; for recombinations
both sources are in the top 10 for 61%, at least one for 100%.

### RQ3. Do the indicators agree with judgments of novelty?

**Human study: pending** (0 annotators, 0 items). The question cannot be answered yet.

In the model-judge pilot, the strongest indicator is highest semantic similarity, ρ = 0.33
[0.20, 0.44] with mean novelty over 204 items; new phrases reaches ρ = 0.46 [0.29, 0.61] on the
generated ideas alone. The two judges rank items similarly (Spearman 0.71) but use the scale
differently (quadratic-weighted κ 0.08). Both rate restatements of prior papers as fairly novel
(3.55 and 3.72 of 5) and separate paraphrases from later papers poorly (AUROC 0.64 and 0.68,
against 0.96 for the best indicator). Qwen3-4B rates its own ideas higher than Phi's (4.49 vs
3.92); Phi does not favour its own (3.88 vs 3.99). These are properties of small model judges, and
a reason not to treat them as a stand-in for people.

### RQ4. Do the indicators measure the same thing?

No. Highest similarity and the share of known concept pairs correlate at ρ = 0.41; the two graph
indicators correlate at 0.94 and are effectively one measure. With thresholds set on the controls
(similarity ≥ 0.805 = near-duplicate; known pairs ≥ 0.71 = known combination; D10), the 96 ideas
split into 32 near-duplicates of a prior paper, 27 known combinations and 37 new combinations of
this literature. The models differ: Phi-4-mini wrote 24 of the 32 near-duplicates, Qwen3-4B 24 of
the 37 new combinations. The hypothesised "dissimilar wording, already-combined concepts" group is
nearly empty (1 idea): ideas that are dissimilar in wording also tend to pair new concepts.

### RQ5. Robustness

Swapping the embedding model (bge-small) keeps rank agreement at 0.78–1.00 and the validity AUROCs
within their intervals (semantic similarity 0.96 → 0.92). Halving the corpus keeps agreement at
0.71–0.99; the graph indicators move most (0.71, 0.74), as expected when half the co-occurrences
disappear. Whether a smaller corpus raises apparent novelty in level was not measured.

## 3. What this means

- Single-number "novelty scores" from similarity are not enough: similarity and concept-pair
  novelty disagree, and the validity test shows which indicators carry signal at all.
- By similarity, these small models' ideas look like new papers; by concept pairs, about a third are
  near-restatements and a further quarter recombine pairs the literature already combines.
- Whether any of this matches what researchers would call novel is the open question; the
  annotation study is what answers it.

## 4. Threats to validity

- **No human labels.** RQ3 is unanswered; the pilot shares training data and biases with the
  generators, and one judge wrote the controls.
- **Corpus coverage.** One index, journal articles only, English in practice; ideas may duplicate
  preprints or conference papers the corpus lacks, which would make them look newer than they are.
- **Controls.** Later papers restated by a model are a proxy for genuinely new ideas; their topics
  are those already active in 2025.
- **Concept extraction** is a transparent phrase heuristic (D6), not an expert ontology.
- **Scale.** 204 items over six topics from two 4-bit models.

## 5. Reproducibility

`make data` rehydrates the corpus from the DOI manifest; `make experiments` reruns E1–E5 on the
committed items and judgments into `results/<experiment>/<UTC>-<sha7>` with config, commit, dirty
flag and input hashes, then renders the results file. Regenerating items and judgments needs the
local models (`make setup-llm models generate judge`). Fresh-clone checks are recorded in
[REVIEW.md](REVIEW.md).
