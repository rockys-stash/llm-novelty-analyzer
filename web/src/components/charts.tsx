import type { Interval } from "../lib/api";
import { KIND_SERIES, KIND_SHORT, niceTicks, num } from "../lib/format";

/** Means with 95% intervals on a shared horizontal axis: one row per group. */
export function IntervalDots({
  rows,
  title,
  domain,
  digits = 2,
}: {
  rows: { key: string; label: string; color: string; v: Interval }[];
  title: string;
  domain?: [number, number];
  digits?: number;
}) {
  const W = 580;
  const L = 236;
  const R = 16;
  const rowH = 26;
  const H = rows.length * rowH + 28;
  const vals = rows.flatMap((r) => [r.v.lo, r.v.hi, r.v.value]).filter((v): v is number => v !== null);
  const axis = niceTicks(domain?.[0] ?? Math.min(0, ...vals), domain?.[1] ?? Math.max(...vals, 1e-6));
  const { lo, hi, ticks } = axis;
  const x = (v: number) => L + ((v - lo) / (hi - lo || 1)) * (W - L - R);
  return (
    <svg
      className="chart-svg"
      style={{ maxWidth: W }}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`${title}. ${rows.map((r) => `${r.label}: ${num(r.v.value, digits)} (95% interval ${num(r.v.lo, digits)} to ${num(r.v.hi, digits)})`).join("; ")}`}
    >
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={4} y2={H - 22} stroke="var(--rule)" />
          <text x={x(t)} y={H - 8} textAnchor="middle" className="tick">
            {num(t, axis.digits)}
          </text>
        </g>
      ))}
      {rows.map((r, i) => {
        const cy = 16 + i * rowH;
        return (
          <g key={r.key}>
            <text x={L - 8} y={cy + 4} textAnchor="end" className="label">
              {r.label}
            </text>
            {r.v.lo !== null && r.v.hi !== null && (
              <line x1={x(r.v.lo)} x2={x(r.v.hi)} y1={cy} y2={cy} stroke={r.color} strokeWidth={2} />
            )}
            {r.v.value !== null && <circle cx={x(r.v.value)} cy={cy} r={5} fill={r.color} />}
          </g>
        );
      })}
    </svg>
  );
}

/** Every item's value for one indicator, one row per kind; the selected item is ringed. */
export function StripPlot({
  points,
  selected,
  title,
  kinds,
}: {
  points: { id: string; kind: string; v: number | null }[];
  selected?: string;
  title: string;
  kinds: readonly string[];
}) {
  const W = 360;
  const L = 104;
  const R = 14;
  const rowH = 18;
  const H = kinds.length * rowH + 22;
  const vals = points.map((p) => p.v).filter((v): v is number => v !== null);
  const axis = niceTicks(Math.min(...vals, 0), Math.max(...vals, 1e-6), 2);
  const { lo, hi } = axis;
  const x = (v: number) => L + ((v - lo) / (hi - lo || 1)) * (W - L - R);
  const sel = points.find((p) => p.id === selected);
  return (
    <svg
      className="chart-svg"
      style={{ maxWidth: W }}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`${title}. ${sel ? `This item: ${num(sel.v)}. ` : ""}${kinds
        .map((k) => {
          const v = points.filter((p) => p.kind === k && p.v !== null).map((p) => p.v as number);
          return v.length ? `${KIND_SHORT[k]}: ${v.length} items from ${num(Math.min(...v))} to ${num(Math.max(...v))}` : "";
        })
        .filter(Boolean)
        .join("; ")}`}
    >
      {kinds.map((k, i) => {
        const cy = 10 + i * rowH;
        return (
          <g key={k}>
            <text x={L - 6} y={cy + 4} textAnchor="end" className="tick">
              {KIND_SHORT[k]}
            </text>
            <line x1={L} x2={W - R} y1={cy} y2={cy} stroke="var(--rule)" />
            {points
              .filter((p) => p.kind === k && p.v !== null && p.id !== selected)
              .map((p) => (
                <circle key={p.id} cx={x(p.v as number)} cy={cy} r={2.6} fill={KIND_SERIES[k]} opacity={0.55} />
              ))}
          </g>
        );
      })}
      {sel && sel.v !== null && (
        <circle
          cx={x(sel.v)}
          cy={10 + kinds.indexOf(sel.kind) * rowH}
          r={6}
          fill="none"
          stroke="var(--ink)"
          strokeWidth={2}
        />
      )}
      {axis.ticks.map((t, i) => (
        <text
          key={t}
          x={x(t)}
          y={H - 4}
          textAnchor={i === 0 ? "start" : i === axis.ticks.length - 1 ? "end" : "middle"}
          className="tick"
        >
          {num(t, axis.digits)}
        </text>
      ))}
    </svg>
  );
}

/** Correlation matrix as a heat map (blue negative, orange positive) with the values written in. */
export function Heatmap({ labels, values, title }: { labels: string[]; values: (number | null)[][]; title: string }) {
  const cell = 46;
  const L = 196;
  const T = 8;
  const W = L + labels.length * cell + 4;
  const H = T + labels.length * cell + 4;
  const color = (v: number | null) =>
    v === null ? "var(--surface-2)" : v >= 0 ? `rgba(235, 104, 52, ${Math.abs(v) * 0.85})` : `rgba(42, 120, 214, ${Math.abs(v) * 0.85})`;
  return (
    <svg className="chart-svg" style={{ maxWidth: W }} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
      {labels.map((a, i) => (
        <g key={a}>
          <text x={L - 8} y={T + i * cell + cell / 2 + 4} textAnchor="end" className="label">
            {a}
          </text>
          {labels.map((b, j) => {
            const v = values[i]?.[j] ?? null;
            return (
              <g key={b}>
                <rect x={L + j * cell} y={T + i * cell} width={cell - 2} height={cell - 2} fill={color(v)} rx={3} />
                <text x={L + j * cell + cell / 2 - 1} y={T + i * cell + cell / 2 + 4} textAnchor="middle" className="tick strong">
                  <title>{`${a} × ${b}: ${num(v, 2)}`}</title>
                  {num(v, 2)}
                </text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

/** A thin horizontal bar for a value in [0, 1]. */
export function Bar({ value, label }: { value: number; label: string }) {
  return (
    <span className="bar" role="img" aria-label={label}>
      <span className="bar-fill" style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </span>
  );
}
