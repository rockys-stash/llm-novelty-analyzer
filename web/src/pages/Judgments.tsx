import { Link } from "react-router-dom";
import { IntervalDots } from "../components/charts";
import { DataTable } from "../components/DataTable";
import { ErrorOrPending, Loading, PageHead, ProvenanceLine } from "../components/ui";
import { type Correlation, type Judgments as JudgmentsData, api, useApi } from "../lib/api";
import { INDICATORS, INDICATOR_LABEL, KINDS, KIND_SHORT, MODEL_LABEL, interval, num } from "../lib/format";

function CorrelationChart({ corr, subset, title }: { corr: Correlation[]; subset: "all" | "idea"; title: string }) {
  return (
    <IntervalDots
      title={title}
      domain={[-1, 1]}
      rows={INDICATORS.map((k) => ({
        key: k,
        label: INDICATOR_LABEL[k] ?? k,
        color: "var(--series-a)",
        v: corr.find((c) => c.indicator === k && c.subset === subset)?.rho ?? { value: null, lo: null, hi: null },
      }))}
    />
  );
}

export function Judgments() {
  const { data, error, loading, retry } = useApi<JudgmentsData>(api.judgments);
  return (
    <>
      <PageHead title="Do the indicators agree with judgments of novelty?">
        This is the research question. Human judgments answer it; they are collected with the annotation page and
        analysed once enough items are scored. Until then, two local language models answer the same rubric as a
        pilot. Their scores test the analysis, not the question: a model's view of novelty is not a person's.
      </PageHead>
      {loading && !data && <Loading label="Loading judgments" />}
      {error && <ErrorOrPending error={error} retry={retry} what="judgments" command="make judge e3" />}
      {data && (
        <>
          <section className="panel">
            <div className="panel-head">
              <h2>Human study</h2>
              <span className={`pill-status ${data.human.status}`}>Status: {data.human.status}</span>
            </div>
            <div className="panel-body stack">
              <p>
                {data.human.records} annotation records from {data.human.annotators} annotators on {data.human.items} items.{" "}
                {data.human.status === "pending" ? (
                  <>
                    The correlation analysis runs once enough items have a human score. <Link to="/annotate">Annotate items</Link>.
                  </>
                ) : null}
              </p>
              {data.human.status === "complete" && (
                <CorrelationChart corr={data.human.correlations} subset="all" title="Spearman correlation with human novelty, all items" />
              )}
            </div>
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Model-judge pilot: indicators against model novelty scores</h2>
              <span className="muted small">
                {data.model_judges.items} items · Spearman ρ, 95% bootstrap interval · higher indicator = more novel
              </span>
            </div>
            <div className="grid-2 panel-body">
              <div className="stack-sm">
                <h3 className="small">All items</h3>
                <CorrelationChart corr={data.model_judges.correlations} subset="all" title="Spearman correlation with model-judge novelty, all items" />
              </div>
              <div className="stack-sm">
                <h3 className="small">Generated ideas only</h3>
                <CorrelationChart corr={data.model_judges.correlations} subset="idea" title="Spearman correlation with model-judge novelty, generated ideas" />
              </div>
            </div>
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>The judges themselves</h2>
              <span className="muted small">mean novelty (1–5) by item kind</span>
            </div>
            <DataTable
              caption="Model judges"
              rows={Object.entries(data.model_judges.per_judge)}
              rowKey={([k]) => k}
              columns={[
                { key: "j", label: "Judge", render: ([k]) => MODEL_LABEL[k] ?? k },
                ...KINDS.map((kind) => ({
                  key: kind,
                  label: KIND_SHORT[kind] ?? kind,
                  align: "r" as const,
                  render: ([, v]: [string, JudgmentsData["model_judges"]["per_judge"][string]]) => num(v.novelty_by_kind[kind], 2),
                })),
                { key: "auc", label: "AUROC paraphrase → later", align: "r", render: ([, v]) => num(v.auroc_paraphrase_later, 2) },
                { key: "own", label: "Own model's ideas", align: "r", render: ([, v]) => num(v.own_ideas, 2) },
                { key: "other", label: "Other model's ideas", align: "r", render: ([, v]) => num(v.other_ideas, 2) },
              ]}
            />
            {data.model_judges.agreement && (
              <p className="panel-body small">
                Agreement between the two judges: novelty Spearman {num(data.model_judges.agreement.novelty?.spearman, 2)}, quadratic-weighted κ{" "}
                {num(data.model_judges.agreement.novelty?.weighted_kappa, 2)}; relevance κ{" "}
                {num(data.model_judges.agreement.relevance?.weighted_kappa, 2)}; meaningfulness κ{" "}
                {num(data.model_judges.agreement.meaningfulness?.weighted_kappa, 2)}.
              </p>
            )}
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Per judge</h2>
            </div>
            <DataTable
              caption="Correlation of each indicator with each judge, all items"
              rows={INDICATORS.map((k) => k)}
              rowKey={(k) => k}
              columns={[
                { key: "i", label: "Indicator", render: (k) => INDICATOR_LABEL[k] ?? k },
                ...data.model_judges.judges.map((j) => ({
                  key: j,
                  label: MODEL_LABEL[j] ?? j,
                  align: "r" as const,
                  render: (k: string) =>
                    interval(data.model_judges.per_judge[j]?.correlations.find((c) => c.indicator === k && c.subset === "all")?.rho),
                })),
              ]}
            />
          </section>
          <ProvenanceLine p={data.provenance} />
        </>
      )}
    </>
  );
}
