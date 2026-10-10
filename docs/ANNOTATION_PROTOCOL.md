# Annotation protocol: human judgments of novelty

Status: **ready, not yet run.** No human annotations have been collected. Until they are, E3
reports the human analysis as pending and nothing in this repository presents model judgments as
human ones.

## Purpose

The research question is whether computational novelty indicators correlate with human judgments
of novelty. This protocol produces those judgments.

## Who annotates

People with at least graduate-level familiarity with the topic they score (for example, a
researcher who has published or reviewed in that area). Each annotator scores only topics they
know; three annotators per item are the target. Annotators are identified only by a pseudonym they
choose; no name, e-mail or other identifier is stored.

## What annotators see

The console's **Annotate** page (`make serve`, then `/annotate`) shows one item at a time: the
topic, a title and a three-to-four sentence idea. It never shows who or what wrote the item, its
kind (generated idea or control), its sources, any indicator, or other annotators' scores. Items
come in an order fixed per annotator (a seeded shuffle of all items), so annotators do not all see
the same sequence. An annotator may skip an item.

## What annotators do

For each item, three ratings from 1 to 5:

| Criterion | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Novelty | Already published or textbook knowledge | A minor variation of published work | A new combination of known ideas | A new approach to a known problem, or a known approach to a new problem | A new problem or approach unlike existing work |
| Relevance | Unrelated to the topic | | Loosely related | | Squarely within the topic |
| Meaningfulness | Unclear, infeasible or not worth doing | | Reasonable but vague | | Clear, feasible and worth doing |

Annotators use their own knowledge and do not search the literature while scoring (the indicators
search the literature; the point is to compare them with expert judgment, not with a second
search). An optional comment can say why, or what published work the idea resembles. The time
spent per item is recorded.

## Before scoring

Each annotator reads this rubric in full. A short group discussion of the scale anchors before
starting is recommended; it is not recorded.

## Storage and quality

Each submission is validated (pseudonym format, known item, integer scores 1-5, comment of at most
1,000 characters) and appended to `annotations/human.jsonl`; nothing is ever edited or deleted, and
the latest record per annotator and item counts. An item's human score is the mean over its
annotators.

## Analysis (pre-specified)

`make e3` computes, once at least 20 items have a human score: the Spearman correlation between
each indicator (oriented so higher means more novel) and the mean human novelty score, over all
items and over generated ideas only, with 95% bootstrap intervals. The model-judge pilot is
analysed with the same code but reported separately and labelled as model judgments.

## Ethics

Annotators are volunteers, may stop at any time, and can ask for their records to be removed (the
only edit the store allows, made by the maintainer and noted in the repository history). Items are
research ideas; none contain personal data.
