import { useCallback, useEffect, useRef, useState } from "react";

/* ---------- types mirrored from the API (src/novelty/api.py) ---------- */
export interface Provenance {
  experiment: string;
  run_id: string;
  commit: string;
  dirty: boolean;
  created_at: string;
  runtime_seconds: number;
  cpus: number;
}

export interface Interval {
  value: number | null;
  lo: number | null;
  hi: number | null;
}

export type Kind = "paraphrase" | "recombination" | "idea" | "later";
export type Values = Record<string, number | null>;

export interface ItemRow {
  id: string;
  topic: string;
  kind: Kind;
  model: string;
  title: string;
  values: Values;
}

export interface CorpusStat {
  topic: string;
  label: string;
  papers: number;
  years: [number, number];
  concepts: number;
  edges: number;
  median_references: number;
  later: number;
}

export interface Overview {
  items: ItemRow[];
  corpus: CorpusStat[];
  by_kind: ({ kind: Kind; n: number } & Record<string, Interval | number | string>)[];
  topics: Record<string, string>;
  groups?: Record<string, string>;
  provenance: Provenance;
}

export interface Neighbour {
  doi: string;
  title: string;
  year: number | null;
  venue: string;
  similarity: number;
  shared_concepts: string[];
  source: boolean;
}

export interface Judgment {
  judge: string;
  item: string;
  novelty: number;
  relevance: number;
  meaningfulness: number;
  novelty_dist: number[];
}

export interface ItemPage extends ItemRow {
  text: string;
  sources: string[];
  topic_label: string;
  concepts: string[];
  new_phrases: string[];
  unseen_pairs: [string, string][];
  n_pairs: number;
  neighbours: Neighbour[];
  source_ranks: Record<string, number>;
  judgments: Judgment[];
  human: { novelty: number; relevance: number; meaningfulness: number }[];
  group?: string | null;
  thresholds?: { semantic_max: number; kg_known_pairs: number };
  provenance: Provenance;
}

export interface Paper {
  doi: string;
  title: string;
  abstract: string;
  year: number | null;
  venue: string;
  topic: string;
  part: "corpus" | "later";
  references: number;
  cited_by: number;
}

export interface AurocRow {
  a: Kind;
  b: Kind;
  indicator: string;
  n_a: number;
  n_b: number;
  auroc: Interval;
}

export interface Validity {
  auroc: AurocRow[];
  recovery: Record<string, { n: number; top1_all: number; top10_all: number; top10_any: number; median_rank: number }>;
  provenance: Provenance;
}

export interface Correlation {
  subset: "all" | "idea";
  indicator: string;
  n: number;
  rho: Interval;
}

export interface Judgments {
  human: { status: "complete" | "pending"; records: number; items: number; annotators: number; correlations: Correlation[] };
  model_judges: {
    judges: string[];
    items: number;
    correlations: Correlation[];
    per_judge: Record<
      string,
      {
        novelty_by_kind: Partial<Record<Kind, number>>;
        auroc_paraphrase_later: number | null;
        own_ideas: number | null;
        other_ideas: number | null;
        relevance: number;
        meaningfulness: number;
        correlations: Correlation[];
      }
    >;
    agreement?: Record<string, { spearman: number | null; weighted_kappa: number | null }>;
  };
  provenance: Provenance;
}

export interface GroupedIdea {
  id: string;
  topic: string;
  model: string;
  title: string;
  group: string;
  semantic_max: number;
  kg_known_pairs: number | null;
  nearest: string;
}

export interface Disagreement {
  matrix: { indicators: string[]; spearman: (number | null)[][] };
  groups: {
    thresholds: { semantic_max: number; kg_known_pairs: number };
    ideas: GroupedIdea[];
    counts: ({ model: string; n: number } & Record<string, number | string>)[];
    disagreements: GroupedIdea[];
  };
  provenance: Provenance;
}

export interface Robustness {
  variants: { variant: string; indicator: string; rank_agreement: number | null; auroc_primary: Interval; auroc_variant: Interval }[];
  provenance: Provenance;
}

export interface QueueItem {
  id: string;
  topic: string;
  title: string;
  text: string;
}

export interface Queue {
  annotator: string;
  done: number;
  total: number;
  queue: QueueItem[];
}

export interface Summary {
  title: string;
  question: string;
  findings: string[];
  tables: {
    id: string;
    caption: string;
    columns: { key: string; label: string; align: "l" | "r" }[];
    rows: Record<string, unknown>[];
  }[];
  notes: string[];
  provenance: Provenance;
}

export interface ExperimentItem {
  experiment: string;
  status: "complete" | "pending";
  title?: string;
  question?: string;
  run_id?: string;
  commit?: string;
  created_at?: string;
  runtime_seconds?: number;
}

/* ---------- fetching ---------- */
export class ApiError extends Error {
  constructor(
    public url: string,
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const cache = new Map<string, unknown>();

export async function getJson<T>(url: string): Promise<T> {
  if (cache.has(url)) return cache.get(url) as T;
  let res: Response;
  try {
    res = await fetch(url, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError(url, 0, "The Explorer API could not be reached.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(url, res.status, detail);
  }
  const data = (await res.json()) as T;
  cache.set(url, data);
  return data;
}

export interface ApiState<T> {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  retry: () => void;
}

export function useApi<T>(url: string | null): ApiState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<ApiError | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(url !== null);
  const [nonce, setNonce] = useState(0);
  const current = useRef(url);

  useEffect(() => {
    current.current = url;
    if (url === null) {
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    setError(undefined);
    getJson<T>(url)
      .then((d) => {
        if (alive && current.current === url) setData(d);
      })
      .catch((e: unknown) => {
        if (alive && current.current === url)
          setError(e instanceof ApiError ? e : new ApiError(url, 0, String(e)));
      })
      .finally(() => {
        if (alive && current.current === url) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [url, nonce]);

  const retry = useCallback(() => {
    if (url) cache.delete(url);
    setNonce((n) => n + 1);
  }, [url]);

  return { data, error, loading, retry };
}

export const api = {
  overview: "/api/overview",
  item: (id: string) => `/api/items/${encodeURIComponent(id)}`,
  paper: (doi: string) => `/api/papers?doi=${encodeURIComponent(doi)}`,
  validity: "/api/validity",
  judgments: "/api/judgments",
  disagreement: "/api/disagreement",
  robustness: "/api/robustness",
  queue: (annotator: string) => `/api/annotate/queue?annotator=${encodeURIComponent(annotator)}`,
  experiments: "/api/experiments",
  experiment: (exp: string) => `/api/experiments/${encodeURIComponent(exp)}`,
};

/** Save one human annotation (the only write the API accepts). */
export async function postAnnotation(body: {
  annotator: string;
  item: string;
  novelty: number;
  relevance: number;
  meaningfulness: number;
  comment: string;
  seconds: number;
}): Promise<void> {
  let res: Response;
  try {
    res = await fetch("/api/annotations", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("/api/annotations", 0, "The Explorer API could not be reached.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const b = (await res.json()) as { detail?: unknown };
      if (typeof b.detail === "string") detail = b.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError("/api/annotations", res.status, detail);
  }
}

/** Forget cached responses (after a write, so the next read is fresh). */
export function invalidate(prefix: string): void {
  for (const k of [...cache.keys()]) if (k.startsWith(prefix)) cache.delete(k);
}
