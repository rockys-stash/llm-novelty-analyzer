import { Link } from "react-router-dom";
import { Heatmap } from "../components/charts";
import { DataTable } from "../components/DataTable";
import { ErrorOrPending, Loading, PageHead, ProvenanceLine } from "../components/ui";
import { type Disagreement as DisagreementData, type GroupedIdea, api, useApi } from "../lib/api";
import { GROUP_LABEL, INDICATOR_LABEL, MODEL_LABEL, num, pct } from "../lib/format";

const GROUPS = ["near-duplicate", "known combination", "new combination"];

export function Disagreement() {
  const { data, error, loading, retry } = useApi<DisagreementData>(api.disagreement);
  return (
    <>
      <PageHead title="Similarity is not novelty">
        If the indicators measured one thing they would agree. Below, how they relate to each other, and how the
        generated ideas fall into three groups whose thresholds are set on the controls only.
      </PageHead>
      {loading && !data && <Loading label="Loading" />}
      {error && <ErrorOrPending error={error} retry={retry} what="the indicator comparison" command="make e4" />}
      {data && (
        <>
          <section className="panel">
            <div className="panel-head">
              <h2>Generated ideas by group</h2>
              <span className="muted small">
                near-duplicate: similarity ≥ {num(data.groups.thresholds.semantic_max, 3)}; known combination: known concept pairs ≥{" "}
                {pct(data.groups.thresholds.kg_known_pairs)}
              </span>
            </div>
            <DataTable
              caption="Generated ideas by group and model"
              rows={data.groups.counts}
              rowKey={(c) => c.model}
              columns={[
                { key: "m", label: "Model", render: (c) => MODEL_LABEL[c.model] ?? c.model },
                { key: "n", label: "Ideas", align: "r", render: (c) => c.n },
                ...GROUPS.map((g) => ({
                  key: g,
                  label: GROUP_LABEL[g] ?? g,
                  align: "r" as const,
                  render: (c: DisagreementData["groups"]["counts"][number]) => `${c[g]} (${pct(Number(c[g]) / c.n)})`,
                })),
              ]}
            />
            <p className="muted small panel-body">
              Near-duplicate: as close to a prior paper as most restated papers are. Known combination: its concept
              pairs are combined in the literature at least as often as in the recombination controls. New combination:
              neither. The groups describe the relation to this literature snapshot; they are not a verdict on novelty.
            </p>
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Low similarity, every concept pair already combined</h2>
              <span className="muted small">{data.groups.disagreements.length} generated ideas</span>
            </div>
            <DataTable
              caption="Ideas the semantic indicator calls distant but whose concept pairs are all known"
              rows={data.groups.disagreements}
              rowKey={(r) => r.id}
              columns={[
                { key: "t", label: "Idea", render: (r: GroupedIdea) => <Link to={`/items/${r.id}`}>{r.title}</Link> },
                { key: "s", label: "Similarity (max)", align: "r", render: (r) => num(r.semantic_max, 3) },
                { key: "n", label: "Nearest prior paper", render: (r) => r.nearest },
              ]}
            />
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>How the indicators relate</h2>
              <span className="muted small">Spearman correlation over all items</span>
            </div>
            <div className="panel-body">
              <Heatmap
                title="Spearman correlation between indicators"
                labels={data.matrix.indicators.map((k) => INDICATOR_LABEL[k] ?? k)}
                values={data.matrix.spearman}
              />
            </div>
          </section>
          <ProvenanceLine p={data.provenance} />
        </>
      )}
    </>
  );
}
