import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { IntervalDots } from "../components/charts";
import { DataTable } from "../components/DataTable";
import { KindTag } from "../components/KindTag";
import { ErrorOrPending, Loading, PageHead, ProvenanceLine, Segmented } from "../components/ui";
import { type Interval, type ItemRow, type Overview, api, useApi } from "../lib/api";
import { GROUP_LABEL, INDICATOR_LABEL, KINDS, KIND_LABEL, KIND_SERIES, MODEL_LABEL, num } from "../lib/format";

const SHOWN = ["semantic_max", "kg_known_pairs", "new_phrase_share"] as const;

export function Ideas() {
  const { data, error, loading, retry } = useApi<Overview>(api.overview);
  const [topic, setTopic] = useState("all");
  const [kind, setKind] = useState("idea");
  const [indicator, setIndicator] = useState<string>("semantic_max");
  const rows = useMemo(
    () =>
      (data?.items ?? [])
        .filter((r) => (topic === "all" || r.topic === topic) && (kind === "all" || r.kind === kind))
        .sort((a, b) => (b.values.semantic_max ?? 0) - (a.values.semantic_max ?? 0)),
    [data, topic, kind],
  );
  return (
    <>
      <PageHead title="Are the generated ideas new?">
        Language models proposed research ideas in six topics. Each idea is compared with that topic's
        published literature, alongside three controls whose relation to the literature is known: restated
        prior papers, combinations of two prior papers, and papers published after the literature snapshot.
        Similarity to prior work does not prove an idea is old, and low similarity does not prove it is new.
      </PageHead>
      {loading && !data && <Loading label="Loading ideas" />}
      {error && <ErrorOrPending error={error} retry={retry} what="the indicators" command="make experiments" />}
      {data && (
        <>
          <section className="panel">
            <div className="panel-head">
              <h2>Indicators by item kind</h2>
              <span className="muted small">mean with 95% bootstrap interval over items</span>
            </div>
            <div className="panel-body stack">
              <Segmented
                label="Indicator"
                value={indicator}
                onChange={setIndicator}
                options={SHOWN.map((k) => ({ id: k, label: INDICATOR_LABEL[k] ?? k }))}
              />
              <IntervalDots
                title={`${INDICATOR_LABEL[indicator]} by item kind`}
                rows={data.by_kind.map((b) => ({
                  key: b.kind,
                  label: `${KIND_LABEL[b.kind]?.replace("Published after the corpus", "Later paper") ?? b.kind} (${b.n})`,
                  color: KIND_SERIES[b.kind] ?? "var(--ink)",
                  v: b[indicator] as Interval,
                }))}
              />
            </div>
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Items</h2>
              <span className="muted small">{rows.length} shown, most similar to prior work first</span>
            </div>
            <div className="panel-body stack">
              <div className="filters">
                <label>
                  Topic
                  <select value={topic} onChange={(e) => setTopic(e.target.value)}>
                    <option value="all">All topics</option>
                    {Object.entries(data.topics).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Kind
                  <select value={kind} onChange={(e) => setKind(e.target.value)}>
                    <option value="all">All kinds</option>
                    {KINDS.map((k) => (
                      <option key={k} value={k}>
                        {KIND_LABEL[k]}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
            <DataTable
              caption="Items with their indicators"
              rows={rows}
              rowKey={(r) => r.id}
              columns={[
                {
                  key: "title",
                  label: "Item",
                  render: (r: ItemRow) => <Link to={`/items/${r.id}`}>{r.title}</Link>,
                },
                { key: "topic", label: "Topic", render: (r) => data.topics[r.topic] ?? r.topic },
                { key: "kind", label: "Kind", render: (r) => <KindTag kind={r.kind} /> },
                { key: "model", label: "Written by", render: (r) => MODEL_LABEL[r.model] ?? r.model },
                ...SHOWN.map((k) => ({
                  key: k,
                  label: INDICATOR_LABEL[k] ?? k,
                  align: "r" as const,
                  render: (r: ItemRow) => num(r.values[k], 2),
                })),
                {
                  key: "group",
                  label: "Group",
                  title: "E4: thresholds set on the controls",
                  render: (r) => (data.groups?.[r.id] ? GROUP_LABEL[data.groups[r.id] ?? ""] : ""),
                },
              ]}
            />
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Literature</h2>
              <span className="muted small">Crossref journal articles with an abstract and a reference list</span>
            </div>
            <DataTable
              caption="Prior-art corpus per topic"
              rows={data.corpus}
              rowKey={(c) => c.topic}
              columns={[
                { key: "label", label: "Topic", render: (c) => c.label },
                { key: "papers", label: "Papers", align: "r", render: (c) => c.papers.toLocaleString("en") },
                { key: "years", label: "Published", render: (c) => `${c.years[0]}–${c.years[1]}` },
                { key: "concepts", label: "Concepts", align: "r", render: (c) => c.concepts.toLocaleString("en") },
                { key: "edges", label: "Concept pairs seen together", align: "r", render: (c) => c.edges.toLocaleString("en") },
                { key: "refs", label: "Median references", align: "r", render: (c) => num(c.median_references, 0) },
                { key: "later", label: "Later papers", align: "r", render: (c) => c.later },
              ]}
            />
          </section>
          <ProvenanceLine p={data.provenance} />
        </>
      )}
    </>
  );
}
