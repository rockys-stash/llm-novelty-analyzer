import { KIND_SERIES, KIND_SHORT } from "../lib/format";

export function KindTag({ kind }: { kind: string }) {
  return (
    <span className="kind-tag">
      <span className="kind-dot" style={{ background: KIND_SERIES[kind] }} aria-hidden="true" />
      {KIND_SHORT[kind] ?? kind}
    </span>
  );
}
