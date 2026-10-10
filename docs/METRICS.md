# Metrics

Code: `src/novelty/indicators.py`, `concepts.py`, `stats.py`. All indicators are computed against
the corpus of the item's own topic.

## Indicators

| Indicator | Definition | Higher means |
|---|---|---|
| Semantic similarity (max) | Highest cosine similarity between the item's sentence embedding (all-MiniLM-L6-v2 of "title. idea") and any corpus paper's ("title. abstract"). | closer to prior art |
| Semantic similarity (top 10) | Mean cosine similarity to the 10 nearest papers. | closer to prior art |
| Keyword overlap | Highest Jaccard overlap between the item's content words and any paper's (stopwords and generic academic words removed, plurals normalised). | closer to prior art |
| Concept overlap | Share of the item's concepts that occur in its 10 nearest papers. | closer to prior art |
| Citation overlap | Mean pairwise Jaccard overlap of the deposited reference lists (DOIs) of the 10 nearest papers: bibliographic coupling of the item's prior art. | the item sits inside one established literature |
| Known concept pairs (graph) | Share of pairs of the item's concepts that co-occur in at least one corpus paper (edges of the concept co-occurrence graph). | a combination already made |
| Concept-pair association (graph) | Mean normalised pointwise mutual information of those pairs over papers; −1 for a pair never seen together. | a more conventional combination |
| New phrases | Share of the item's multi-word candidate phrases that no corpus paper contains. | more new wording |

A **concept** is a candidate phrase (a run of one to three content words between stopwords or
punctuation, as in RAKE) that occurs in at least 3 papers of the topic and in at most 30% of them;
a single word must also be at least 3 times more frequent in the topic than in the other five
topics. The **prior-art map** is the 10 nearest papers by embedding similarity, each with the
concepts it shares with the item.

## Validity and agreement

| Measure | Definition |
|---|---|
| AUROC between kinds (E2) | Probability that an item of the second kind gets a higher novelty-oriented indicator value than an item of the first; ties count half. 0.5 = no separation. |
| Source recovery (E2) | Rank of the paper(s) a control was written from among all papers in its topic, by embedding similarity. |
| Spearman ρ (E3, E4, E5) | Rank correlation over items, ignoring undefined values. |
| Quadratic-weighted κ (E3) | Agreement between two raters' integer scores 1–5, weighting disagreements by squared distance. |

Model-judge scores are the expected value of the judge's next-token distribution over the digits
1–5 after "Novelty:" (and likewise for relevance and meaningfulness). Human scores are integers 1–5,
averaged over annotators per item.

## Intervals

95% percentile bootstrap over items (1,000 resamples; E5 500). For AUROC the resampling is
stratified by kind so each resample keeps both groups' sizes.
