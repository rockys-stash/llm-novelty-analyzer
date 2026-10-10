# Data

## Literature corpus (Crossref)

| | |
|---|---|
| Source | Crossref REST API, `https://api.crossref.org/works` (metadata deposited by publishers) |
| Query | per topic, `query.bibliographic=<topic query>` with `has-abstract:true, has-references:true, type:journal-article`, published 2015-01-01 to 2025-12-31 (corpus) or 2026-03-01 to 2026-10-01 (later papers) |
| Retrieved | 2026-10-10; DOIs in `data/corpus_manifest.json` (committed), SHA-256 per topic and part |
| Rebuild | `make data` rehydrates the manifest's DOIs into `data/raw/` (not committed). The DOI set is fixed, but Crossref records can gain references after retrieval, so a later rebuild can differ slightly in reference counts and in numbers that depend on them (measured in [REVIEW](../docs/REVIEW.md): changes of at most 0.01) |
| Licence | Crossref metadata is open (CC0, per Crossref). Abstracts are the publishers' and stay local; titles and DOIs are committed in results. |

| Topic | Query | Corpus papers | Later papers |
|---|---|---:|---:|
| Uncertainty calibration of neural networks | uncertainty calibration deep neural networks confidence | 988 | 40 |
| Battery state-of-health estimation | lithium-ion battery state of health estimation machine learning | 981 | 40 |
| Privacy in federated learning | federated learning privacy preserving | 988 | 40 |
| CRISPR off-target prediction | CRISPR Cas9 off-target prediction | 967 | 40 |
| Urban heat island mitigation | urban heat island mitigation | 993 | 40 |
| Misinformation detection on social media | misinformation fake news detection social media | 980 | 40 |

Fewer than 1,000 per topic because records whose abstract has fewer than 40 words, or whose title
duplicates an earlier record, are dropped. Known biases: journals that deposit abstracts and
references with Crossref (many large publishers; fewer society and regional journals); no
preprints or conference papers; English only in practice.

## Items (committed, `items/items.jsonl`)

204 items, 34 per topic: 16 generated ideas (8 per model), 6 paraphrases, 6 recombinations, 6
later papers restated. Each record keeps the model, seed, full reply and source DOIs. Provenance of
each generation run is in `items/items_meta.json`.

## Judgments (committed)

`items/judgments.jsonl`: the model-judge pilot, two judges × 204 items, each with the 1–5
distribution per criterion. `annotations/human.jsonl`: human annotations (none yet; see
`docs/ANNOTATION_PROTOCOL.md`).

## Models

| Model | Use | Pinned |
|---|---|---|
| Qwen3-4B-Instruct-2507 (Q4_0, GGUF) | ideas, controls, judge | SHA-256 in `configs/models.yaml` |
| Phi-4-mini-instruct (Q4_K_M, GGUF) | ideas, judge | SHA-256 in `configs/models.yaml` |
| sentence-transformers/all-MiniLM-L6-v2 | embeddings (primary) | revision in `configs/embeddings.yaml` |
| BAAI/bge-small-en-v1.5 | embeddings (E5 variant) | revision in `configs/embeddings.yaml` |

Licences: Qwen3 Apache-2.0; Phi-4-mini MIT; all-MiniLM-L6-v2 Apache-2.0; bge-small-en-v1.5 MIT.
