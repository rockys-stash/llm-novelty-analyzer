# Design: LLM Idea Novelty Explorer

**Purpose.** A literature and knowledge exploration system for one question: is this idea new? For
any item, see the literature nearest to it, the concepts it shares with that literature, the
phrases and concept pairs the literature has never used, and where each indicator places it
relative to items whose novelty is known by construction. Then see whether the indicators pass a
test with known answers and whether they agree with judgments.

**Users.** A researcher assessing generated ideas; an annotator scoring them; a reviewer of the
study.

**Pages.** Ideas (indicator by item kind with intervals; filterable item table; the literature per
topic) → Item (the idea, its provenance, a prior-art map of the ten nearest papers with similarity,
shared concepts and an expandable abstract, a strip plot per indicator placing the item among all
items by kind, concepts / new phrases / unseen concept pairs, and judgments); Validity (AUROC per
indicator between control kinds, source recovery, robustness); Judgments (human study status;
model-judge pilot correlations, judge behaviour); Similarity vs novelty (indicator correlation heat
map, ideas grouped by control-derived thresholds, ideas where similarity and concept novelty
disagree); Annotate (blind annotation, one item at a time); Experiments; Method.

**Visual language.** Paper or graphite surfaces, hairline rules, one amber accent for selection and
focus. Item kinds have fixed colours (paraphrase blue, recombination violet, generated idea orange,
later paper green) and always appear with their name. New phrases and unseen concept pairs are
dashed chips, so they differ from known concepts in more than colour.

**Accessibility.** Every chart has a text alternative with its values; controls are buttons with
`aria-pressed` or native form controls with labels; the annotation form uses fieldsets with
legends for each scale and announces saves in a live region. Tested with axe in both themes and at
phone width.

**Honesty rules.** The human study is labelled pending until it has data; model judgments are
always called a pilot and never human. Nothing is drawn without a result; every page with numbers
shows the result directory and commit.
