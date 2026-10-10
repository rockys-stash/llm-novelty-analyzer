export const KIND_LABEL: Record<string, string> = {
  paraphrase: "Paraphrased prior paper",
  recombination: "Recombined two prior papers",
  idea: "LLM-generated idea",
  later: "Published after the corpus",
};
export const KIND_SHORT: Record<string, string> = {
  paraphrase: "Paraphrase",
  recombination: "Recombination",
  idea: "Generated idea",
  later: "Later paper",
};
export const KIND_SERIES: Record<string, string> = {
  paraphrase: "var(--series-a)",
  recombination: "var(--series-d)",
  idea: "var(--series-b)",
  later: "var(--series-c)",
};
export const KINDS = ["paraphrase", "recombination", "idea", "later"] as const;

export const INDICATORS = [
  "semantic_max",
  "semantic_top10",
  "keyword_overlap",
  "concept_overlap",
  "citation_overlap",
  "kg_known_pairs",
  "kg_npmi",
  "new_phrase_share",
] as const;
export const INDICATOR_LABEL: Record<string, string> = {
  semantic_max: "Semantic similarity (max)",
  semantic_top10: "Semantic similarity (top 10)",
  keyword_overlap: "Keyword overlap",
  concept_overlap: "Concept overlap",
  citation_overlap: "Citation overlap",
  kg_known_pairs: "Known concept pairs (graph)",
  kg_npmi: "Concept-pair association (graph)",
  new_phrase_share: "New phrases",
};
export const INDICATOR_HELP: Record<string, string> = {
  semantic_max: "Highest cosine similarity of the item's embedding to any prior paper. Higher = closer to prior art.",
  semantic_top10: "Mean similarity to the 10 nearest prior papers. Higher = closer to prior art.",
  keyword_overlap: "Highest Jaccard overlap of content words with any prior paper. Higher = closer to prior art.",
  concept_overlap: "Share of the item's concepts found in its 10 nearest papers. Higher = closer to prior art.",
  citation_overlap: "How much the 10 nearest papers cite the same sources (bibliographic coupling). Higher = the item sits in one established literature.",
  kg_known_pairs: "Share of the item's concept pairs that some prior paper already combines. Higher = a combination already made.",
  kg_npmi: "Mean association (normalised PMI) of the item's concept pairs in the literature; −1 for pairs never seen together.",
  new_phrase_share: "Share of the item's multi-word phrases no prior paper contains. Higher = more new wording (not necessarily new ideas).",
};
/** +1: higher = closer to prior art; −1: higher = more novel. */
export const DIRECTION: Record<string, number> = {
  semantic_max: 1,
  semantic_top10: 1,
  keyword_overlap: 1,
  concept_overlap: 1,
  citation_overlap: 1,
  kg_known_pairs: 1,
  kg_npmi: 1,
  new_phrase_share: -1,
};
export const MODEL_LABEL: Record<string, string> = {
  "qwen3-4b": "Qwen3-4B",
  "phi-4-mini": "Phi-4-mini",
};
export const GROUP_LABEL: Record<string, string> = {
  "near-duplicate": "Near-duplicate",
  "known combination": "Known combination",
  "new combination": "New combination",
};

export function num(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return v.toFixed(digits);
}

export function pct(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return `${(v * 100).toFixed(digits)}%`;
}

export function interval(i: { value: number | null; lo: number | null; hi: number | null } | undefined, digits = 2): string {
  if (!i || i.value === null) return "–";
  if (i.lo === null || i.hi === null) return num(i.value, digits);
  return `${num(i.value, digits)} [${num(i.lo, digits)}, ${num(i.hi, digits)}]`;
}

export function cell(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "boolean") return v ? "yes" : "";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString("en");
    return Math.abs(v) < 100 ? v.toFixed(3) : v.toLocaleString("en", { maximumFractionDigits: 1 });
  }
  return String(v);
}

/** Round axis ticks (steps of 1, 2, 2.5 or 5 × 10^k) covering [lo, hi]; returns the ticks and the widened domain. */
export function niceTicks(lo: number, hi: number, count = 4): { ticks: number[]; lo: number; hi: number; digits: number } {
  const raw = (hi - lo) / count || 1;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * mag >= raw) ?? 10) * mag;
  const a = Math.floor(lo / step + 1e-9) * step;
  const b = Math.ceil(hi / step - 1e-9) * step;
  const ticks = Array.from({ length: Math.round((b - a) / step) + 1 }, (_, i) => a + i * step);
  const digits = Math.max(0, -Math.floor(Math.log10(step) + 1e-9) + (Number.isInteger(step / mag) ? 0 : 1));
  return { ticks, lo: a, hi: b, digits };
}
