import { PageHead } from "../components/ui";
import { INDICATORS, INDICATOR_HELP, INDICATOR_LABEL } from "../lib/format";

export function Method() {
  return (
    <>
      <PageHead title="Method">How items are written, compared with the literature, and judged.</PageHead>
      <section className="panel">
        <div className="panel-head">
          <h2>Pipeline</h2>
        </div>
        <ol className="panel-body stack-sm">
          <li>
            <strong>Literature.</strong> For six topics, the up-to-1,000 most relevant journal articles in Crossref
            (2015–2025) with an abstract and a reference list. A DOI manifest fixes the snapshot; abstracts stay local.
          </li>
          <li>
            <strong>Items.</strong> Two local language models (Qwen3-4B, Phi-4-mini) each propose 8 research ideas per
            topic. Three controls are written in the same format: 6 restated prior papers, 6 combinations of two prior
            papers, and 6 restated papers published after the snapshot (2026).
          </li>
          <li>
            <strong>Concept extraction.</strong> Candidate phrases (runs of up to three content words); a concept is one
            that occurs in at least 3 papers of the topic and is specific to it.
          </li>
          <li>
            <strong>Retrieval and semantic comparison.</strong> Sentence embeddings (all-MiniLM-L6-v2) of every paper and
            item; the 10 nearest papers form the item's prior-art map.
          </li>
          <li>
            <strong>Novelty indicators.</strong> Eight measures of closeness to the literature, below.
          </li>
          <li>
            <strong>Judgments.</strong> Human annotation (this console; the study) and a model-judge pilot (two language
            models answering the same rubric). Correlations are reported separately and never pooled.
          </li>
        </ol>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Indicators</h2>
        </div>
        <dl className="panel-body stack-sm">
          {INDICATORS.map((k) => (
            <div key={k}>
              <dt>
                <strong>{INDICATOR_LABEL[k]}</strong>
              </dt>
              <dd className="muted">{INDICATOR_HELP[k]}</dd>
            </div>
          ))}
        </dl>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Limits</h2>
        </div>
        <ul className="panel-body stack-sm">
          <li>Semantic similarity does not prove novelty. Every indicator measures closeness to one literature snapshot.</li>
          <li>The literature is one search per topic in one index; work outside it (other venues, preprints, patents) is invisible.</li>
          <li>Model judges are not people. Their scores test the analysis; only human judgments answer the question.</li>
          <li>Small models (4 billion parameters, 4-bit) wrote the ideas; larger models may write different ones.</li>
        </ul>
      </section>
    </>
  );
}
