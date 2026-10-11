import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, StripPlot } from "../components/charts";
import { KindTag } from "../components/KindTag";
import { Empty, ErrorOrPending, Loading, PageHead, ProvenanceLine } from "../components/ui";
import { type ItemPage, type Neighbour, type Overview, type Paper, api, useApi } from "../lib/api";
import {
  GROUP_LABEL,
  INDICATORS,
  INDICATOR_HELP,
  INDICATOR_LABEL,
  KINDS,
  KIND_LABEL,
  MODEL_LABEL,
  num,
} from "../lib/format";

const PROVENANCE: Record<string, string> = {
  idea: "A language model was asked for a new research idea in this topic. Whether it is new is what the indicators and judgments try to tell.",
  paraphrase: "A prior paper from the corpus, restated in the same format as the ideas. Its prior art is in the corpus by construction.",
  recombination: "Two prior papers from the corpus, combined into one idea by a language model. A recombination by construction.",
  later: "A paper published after the literature snapshot ends, restated in the same format. Its content is absent from the corpus.",
};

export function Item() {
  const { id = "" } = useParams();
  const item = useApi<ItemPage>(api.item(id));
  const overview = useApi<Overview>(api.overview);
  const [open, setOpen] = useState<string | null>(null);
  if (item.loading && !item.data) return <Loading label="Loading item" />;
  if (item.error || !item.data)
    return (
      <>
        <PageHead title="Item" />
        {item.error && <ErrorOrPending error={item.error} retry={item.retry} what="this item" command="make e1" />}
      </>
    );
  const d = item.data;
  const points = overview.data?.items ?? [];
  return (
    <>
      <PageHead title={d.title}>
        <span className="muted">
          {d.topic_label} · <KindTag kind={d.kind} /> · written by {MODEL_LABEL[d.model] ?? d.model}
          {d.group ? ` · ${GROUP_LABEL[d.group]}` : ""}
        </span>
      </PageHead>
      <section className="panel">
        <div className="panel-body stack">
          <p className="idea-text">{d.text}</p>
          <p className="muted small">
            <strong>{KIND_LABEL[d.kind]}.</strong> {PROVENANCE[d.kind]}
          </p>
        </div>
      </section>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-head">
            <h2>Prior-art map</h2>
            <span className="muted small">10 most similar papers in the topic's literature</span>
          </div>
          <div className="panel-body">
            <ol className="neighbours">
              {d.neighbours.map((n) => (
                <NeighbourCard key={n.doi} n={n} open={open === n.doi} onToggle={() => setOpen(open === n.doi ? null : n.doi)} />
              ))}
            </ol>
          </div>
        </section>
        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <h2>Indicators</h2>
              <span className="muted small">this item (ringed) against every item, by kind</span>
            </div>
            <div className="panel-body stack">
              {INDICATORS.map((k) => (
                <div key={k} className="stack-sm">
                  <h3 className="small">
                    {INDICATOR_LABEL[k]} <span className="mono">{num(d.values[k])}</span>
                  </h3>
                  <p className="muted small">{INDICATOR_HELP[k]}</p>
                  {points.length > 0 && (
                    <StripPlot
                      title={`${INDICATOR_LABEL[k]} of every item by kind`}
                      points={points.map((p) => ({ id: p.id, kind: p.kind, v: p.values[k] ?? null }))}
                      selected={d.id}
                      kinds={KINDS}
                    />
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-head">
            <h2>Concepts</h2>
            <span className="muted small">
              {d.concepts.length} concepts, {d.n_pairs} pairs, {d.unseen_pairs.length >= 40 ? "40+" : d.unseen_pairs.length} pairs no
              paper combines
            </span>
          </div>
          <div className="panel-body stack">
            <h3 className="small">Concepts the literature uses</h3>
            <ul className="chips">
              {d.concepts.map((c) => (
                <li key={c} className="chip">
                  {c}
                </li>
              ))}
            </ul>
            <h3 className="small">Phrases no prior paper contains</h3>
            {d.new_phrases.length ? (
              <ul className="chips">
                {d.new_phrases.map((c) => (
                  <li key={c} className="chip new">
                    {c}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small">None.</p>
            )}
            <h3 className="small">Concept pairs never seen together</h3>
            {d.unseen_pairs.length ? (
              <ul className="chips">
                {d.unseen_pairs.slice(0, 24).map(([a, b]) => (
                  <li key={`${a}|${b}`} className="chip new">
                    {a} + {b}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small">Every pair of its concepts already appears together in some prior paper.</p>
            )}
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h2>Judgments</h2>
          </div>
          <div className="panel-body stack">
            <p className="small">
              <strong>Human annotations:</strong>{" "}
              {d.human.length
                ? `${d.human.length} (mean novelty ${num(d.human.reduce((a, h) => a + h.novelty, 0) / d.human.length, 1)})`
                : "none yet."}{" "}
              <Link to="/annotate">Annotate items</Link>
            </p>
            {d.judgments.length ? (
              <>
                <p className="muted small">
                  Model judges (a pilot, not human judgments): local language models answering the annotation rubric
                  without seeing the item's kind or any indicator. Score = expected value of the judge's 1–5 distribution.
                </p>
                <div className="table-wrap" tabIndex={0} role="region" aria-label="Model-judge scores">
                <table className="compact">
                  <caption className="sr-only">Model-judge scores for this item</caption>
                  <thead>
                    <tr>
                      <th scope="col">Judge</th>
                      <th scope="col" className="num">
                        Novelty
                      </th>
                      <th scope="col" className="num">
                        Relevance
                      </th>
                      <th scope="col" className="num">
                        Meaningfulness
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.judgments.map((j) => (
                      <tr key={j.judge}>
                        <td>{MODEL_LABEL[j.judge] ?? j.judge}</td>
                        <td className="num">{num(j.novelty, 2)}</td>
                        <td className="num">{num(j.relevance, 2)}</td>
                        <td className="num">{num(j.meaningfulness, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </>
            ) : (
              <Empty title="No model judgments yet">
                <p>Run make judge.</p>
              </Empty>
            )}
          </div>
        </section>
      </div>
      <ProvenanceLine p={d.provenance} />
    </>
  );
}

function NeighbourCard({ n, open, onToggle }: { n: Neighbour; open: boolean; onToggle: () => void }) {
  const paper = useApi<Paper>(open ? api.paper(n.doi) : null);
  return (
    <li className="neighbour" data-source={n.source}>
      <div className="neighbour-head">
        <span>
          {n.title} <span className="muted small">({n.year ?? "n.d."})</span>
          {n.source && <strong className="small"> · written from this paper</strong>}
        </span>
        <span className="mono small">
          <Bar value={n.similarity} label={`Similarity ${num(n.similarity, 2)}`} /> {num(n.similarity, 2)}
        </span>
      </div>
      {n.shared_concepts.length > 0 && (
        <ul className="chips" aria-label="Shared concepts">
          {n.shared_concepts.slice(0, 12).map((c) => (
            <li key={c} className="chip">
              {c}
            </li>
          ))}
        </ul>
      )}
      <div className="small">
        <button type="button" className="linkish" aria-expanded={open} onClick={onToggle}>
          {open ? "Hide abstract" : "Show abstract"}
        </button>{" "}
        · <a href={`https://doi.org/${n.doi}`}>doi.org/{n.doi}</a>
        {n.venue && <span className="muted"> · {n.venue}</span>}
      </div>
      {open && (
        <div aria-live="polite">
          {paper.loading && <p className="muted small">Loading abstract…</p>}
          {paper.error && <p className="muted small">Abstract not available locally ({paper.error.message}).</p>}
          {paper.data && <p className="abstract">{paper.data.abstract}</p>}
        </div>
      )}
    </li>
  );
}
