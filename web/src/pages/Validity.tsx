import { useState } from "react";
import { IntervalDots } from "../components/charts";
import { DataTable } from "../components/DataTable";
import { ErrorOrPending, Loading, PageHead, ProvenanceLine, Segmented } from "../components/ui";
import { type Robustness, type Validity as ValidityData, api, useApi } from "../lib/api";
import { INDICATORS, INDICATOR_LABEL, KIND_SHORT, interval, num, pct } from "../lib/format";

const COMPARISONS = [
  ["paraphrase", "later"],
  ["recombination", "later"],
  ["paraphrase", "recombination"],
  ["paraphrase", "idea"],
  ["idea", "later"],
] as const;

export function Validity() {
  const v = useApi<ValidityData>(api.validity);
  const r = useApi<Robustness>(api.robustness);
  const [cmp, setCmp] = useState("paraphrase|later");
  const [a, b] = cmp.split("|");
  return (
    <>
      <PageHead title="Do the indicators pass a test with known answers?">
        The controls have a known relation to the literature: a paraphrase restates a prior paper, a later paper
        was published after the snapshot. An indicator that tracks novelty relative to the literature must rank
        later papers above paraphrases. AUROC 0.5 means it cannot tell the two kinds apart; 1 means it always ranks
        the second kind as more novel.
      </PageHead>
      {v.loading && !v.data && <Loading label="Loading validity" />}
      {v.error && <ErrorOrPending error={v.error} retry={v.retry} what="validity" command="make e2" />}
      {v.data && (
        <>
          <section className="panel">
            <div className="panel-head">
              <h2>AUROC by indicator</h2>
              <span className="muted small">95% bootstrap interval, resampling within each kind</span>
            </div>
            <div className="panel-body stack">
              <Segmented
                label="Comparison"
                value={cmp}
                onChange={setCmp}
                options={COMPARISONS.filter(([x, y]) => v.data?.auroc.some((row) => row.a === x && row.b === y)).map(([x, y]) => ({
                  id: `${x}|${y}`,
                  label: `${KIND_SHORT[x]} → ${KIND_SHORT[y]}`,
                }))}
              />
              <IntervalDots
                title={`AUROC, ${KIND_SHORT[a ?? ""]} versus ${KIND_SHORT[b ?? ""]}`}
                domain={[0, 1]}
                rows={INDICATORS.map((k) => {
                  const row = v.data?.auroc.find((x) => x.a === a && x.b === b && x.indicator === k);
                  return {
                    key: k,
                    label: INDICATOR_LABEL[k] ?? k,
                    color: "var(--accent)",
                    v: row?.auroc ?? { value: null, lo: null, hi: null },
                  };
                })}
              />
              <p className="muted small">Chance is 0.5. Indicators are oriented so that higher means more novel.</p>
            </div>
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Does the prior-art map find the source?</h2>
              <span className="muted small">rank of the paper(s) a control was written from among all papers in its topic</span>
            </div>
            <DataTable
              caption="Source recovery"
              rows={Object.entries(v.data.recovery)}
              rowKey={([k]) => k}
              columns={[
                { key: "k", label: "Control", render: ([k]) => KIND_SHORT[k] ?? k },
                { key: "n", label: "Items", align: "r", render: ([, x]) => x.n },
                { key: "t1", label: "Source ranked 1st", align: "r", render: ([, x]) => pct(x.top1_all) },
                { key: "t10", label: "All sources in top 10", align: "r", render: ([, x]) => pct(x.top10_all) },
                { key: "any", label: "Any source in top 10", align: "r", render: ([, x]) => pct(x.top10_any) },
                { key: "med", label: "Median rank", align: "r", render: ([, x]) => num(x.median_rank, 0) },
              ]}
            />
          </section>
          <ProvenanceLine p={v.data.provenance} />
        </>
      )}
      <section className="panel">
        <div className="panel-head">
          <h2>Robustness</h2>
          <span className="muted small">another embedding model, or half the corpus</span>
        </div>
        {r.error && <ErrorOrPending error={r.error} retry={r.retry} what="robustness" command="make e5" />}
        {r.data && (
          <DataTable
            caption="Indicators under variants"
            rows={r.data.variants}
            rowKey={(x) => `${x.variant}-${x.indicator}`}
            columns={[
              { key: "v", label: "Variant", render: (x) => x.variant },
              { key: "i", label: "Indicator", render: (x) => INDICATOR_LABEL[x.indicator] ?? x.indicator },
              { key: "rho", label: "Rank agreement with primary", align: "r", render: (x) => num(x.rank_agreement, 2) },
              { key: "p", label: "AUROC paraphrase → later, primary", align: "r", render: (x) => interval(x.auroc_primary) },
              { key: "q", label: "Under the variant", align: "r", render: (x) => interval(x.auroc_variant) },
            ]}
          />
        )}
      </section>
      {r.data && <ProvenanceLine p={r.data.provenance} />}
    </>
  );
}
