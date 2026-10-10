import { type FormEvent, useEffect, useRef, useState } from "react";
import { ErrorOrPending, Loading, PageHead } from "../components/ui";
import { ApiError, type Queue, api, invalidate, postAnnotation, useApi } from "../lib/api";

const SCALES = [
  {
    key: "novelty",
    label: "Novelty",
    anchors: [
      "Already published or textbook knowledge",
      "A minor variation of published work",
      "A new combination of known ideas",
      "A new approach to a known problem, or a known approach to a new problem",
      "A new problem or approach unlike existing work",
    ],
  },
  { key: "relevance", label: "Relevance to the topic", anchors: ["Unrelated", "", "Loosely related", "", "Squarely within it"] },
  {
    key: "meaningfulness",
    label: "Meaningfulness",
    anchors: ["Unclear, infeasible or not worth doing", "", "Reasonable but vague", "", "Clear, feasible and worth doing"],
  },
] as const;
type Scores = Record<(typeof SCALES)[number]["key"], number | null>;
const EMPTY: Scores = { novelty: null, relevance: null, meaningfulness: null };
const PSEUDONYM = /^[A-Za-z0-9_-]{2,32}$/;

function stored(): string {
  try {
    return localStorage.getItem("explorer-annotator") ?? "";
  } catch {
    return "";
  }
}

export function Annotate() {
  const [name, setName] = useState(stored);
  const [draft, setDraft] = useState(stored);
  return (
    <>
      <PageHead title="Annotate ideas">
        Score research ideas for novelty, relevance and meaningfulness. You see only the topic and the idea: not who
        or what wrote it, and no indicator. Use your own knowledge of the field; do not search the web. The full
        protocol is in docs/ANNOTATION_PROTOCOL.md. Scores are stored under a pseudonym you choose, never your name.
      </PageHead>
      {!name ? (
        <form
          className="panel panel-body annot"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (!PSEUDONYM.test(draft)) return;
            try {
              localStorage.setItem("explorer-annotator", draft);
            } catch {
              /* storage unavailable: the pseudonym lasts for this page view */
            }
            setName(draft);
          }}
        >
          <label className="stack-sm">
            <span>Pseudonym (2–32 letters, digits, - or _)</span>
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value.trim())}
              autoComplete="off"
              aria-invalid={draft !== "" && !PSEUDONYM.test(draft)}
              aria-describedby="pseudonym-help"
            />
          </label>
          <p id="pseudonym-help" className="muted small">
            By starting you agree that your scores, comments and time per item are kept with the study's results.
          </p>
          <div>
            <button className="btn" type="submit" disabled={!PSEUDONYM.test(draft)}>
              Start annotating
            </button>
          </div>
        </form>
      ) : (
        <Session
          annotator={name}
          onSwitch={() => {
            setName("");
          }}
        />
      )}
    </>
  );
}

function Session({ annotator, onSwitch }: { annotator: string; onSwitch: () => void }) {
  const { data, error, loading, retry } = useApi<Queue>(api.queue(annotator));
  const [skipped, setSkipped] = useState<string[]>([]);
  const [scores, setScores] = useState<Scores>(EMPTY);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const started = useRef(Date.now());
  const item = data?.queue.find((q) => !skipped.includes(q.id));
  useEffect(() => {
    started.current = Date.now();
    setScores(EMPTY);
    setComment("");
  }, [item?.id]);
  if (loading && !data) return <Loading label="Loading items" />;
  if (error) return <ErrorOrPending error={error} retry={retry} what="the annotation queue" command="make generate" />;
  if (!data) return null;
  const complete = SCALES.every((s) => scores[s.key] !== null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!item || !complete) return;
    setSaving(true);
    try {
      await postAnnotation({
        annotator,
        item: item.id,
        novelty: scores.novelty ?? 0,
        relevance: scores.relevance ?? 0,
        meaningfulness: scores.meaningfulness ?? 0,
        comment,
        seconds: (Date.now() - started.current) / 1000,
      });
      setStatus(`Saved. ${data.done + 1} of ${data.total} done.`);
      invalidate("/api/annotate/queue");
      retry();
    } catch (err) {
      setStatus(err instanceof ApiError ? `Not saved: ${err.message}` : "Not saved.");
    } finally {
      setSaving(false);
    }
  };
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>
          {data.done} of {data.total} done
        </h2>
        <span className="small">
          Annotating as <strong>{annotator}</strong>{" "}
          <button type="button" className="linkish" onClick={onSwitch}>
            Change
          </button>
        </span>
      </div>
      <div className="panel-body">
        <p className="sr-only" aria-live="polite">
          {status}
        </p>
        {status && (
          <p className="small" aria-hidden="true">
            {status}
          </p>
        )}
        {!item ? (
          <p>Nothing left to annotate. Thank you.</p>
        ) : (
          <form className="annot" onSubmit={submit}>
            <div className="stack-sm">
              <p className="muted small">Topic: {item.topic}</p>
              <h3>{item.title}</h3>
              <p className="idea-text">{item.text}</p>
            </div>
            {SCALES.map((s) => (
              <fieldset key={s.key} className="scale">
                <legend>{s.label}</legend>
                <div className="scale-options">
                  {[1, 2, 3, 4, 5].map((v) => (
                    <label key={v} title={s.anchors[v - 1] || undefined}>
                      <input
                        type="radio"
                        name={s.key}
                        value={v}
                        checked={scores[s.key] === v}
                        onChange={() => setScores({ ...scores, [s.key]: v })}
                      />
                      <span>
                        {v}
                        {s.anchors[v - 1] ? ` · ${s.anchors[v - 1]}` : ""}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <label className="stack-sm">
              <span>Comment (optional): why, or what it resembles</span>
              <textarea value={comment} maxLength={1000} onChange={(e) => setComment(e.target.value)} />
            </label>
            <div className="controls">
              <button className="btn" type="submit" disabled={!complete || saving}>
                {saving ? "Saving…" : "Save and next"}
              </button>
              <button className="btn ghost" type="button" onClick={() => setSkipped([...skipped, item.id])}>
                Skip for now
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
