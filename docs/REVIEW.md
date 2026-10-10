# Internal review board

Reviewed 2026-10-10 against [REPORT.md](REPORT.md) and the result directories it cites (all on
clean commits). **Overall: pass, with the human study pending.** RQ3 (do indicators agree with
human judgments?) cannot be answered until annotations are collected; the repository says so
everywhere it matters.

| Reviewer | Verdict | Required fixes |
|---|---|---|
| Research | Pass, one pending item | Human annotation study not run (protocol ready) |
| Engineering | Pass | None open |
| QA | Pass | None open |
| Security | Pass | None open |
| UX | Pass | Chart labels clipped and non-round ticks (fixed during review) |
| Release | Pass | None open |

## Research reviewer

- Indicators are tested on material whose relation to the corpus is known (paraphrases,
  recombinations, papers published after the corpus) before they are applied to generated ideas;
  two of eight indicators fail that test and the report says so instead of dropping them.
- The model-judge pilot is labelled a pilot everywhere (README, report, console) and is not used
  to answer RQ3. Its known weaknesses are reported: judges rate paraphrases as novel, use the scale
  differently (κ 0.08) and one judge favours its own ideas.
- Negative results are stated: generated ideas are as far from the corpus as genuinely later papers
  by similarity, contrary to the hypothesis; the "dissimilar wording, known combinations" group
  is nearly empty.
- Pending: the human study ([ANNOTATION_PROTOCOL.md](ANNOTATION_PROTOCOL.md)). No participant data
  were simulated.

## Engineering reviewer

- `make data` rehydrates the corpus from a committed DOI manifest; `make experiments` reruns E1–E5
  into versioned result directories with config, commit, dirty flag and input hashes.
- ruff, mypy strict over `src`, `tests`, `scripts`, ESLint and `tsc`. CI runs the unit tests, a
  smoke run, the console build, npm audit and the browser tests.

## QA reviewer

- 18 unit, pipeline and API tests and 26 browser tests pass (`make test`, `make test-ui`), including
  keyboard navigation and axe-core (WCAG 2.1 A/AA) on every page in both themes and at mobile width.
- 21 screenshots taken from the running console.
- **Fresh clone** (2026-10-10): a new clone of `85df0c8` ran `make setup data test lint experiments`
  and passed. The rendered tables differed from the committed ones in small ways, all traced to the
  corpus rehydration: Crossref had added a few references to some records since the committed
  corpus was built (e.g. CRISPR: 3,625 → 3,634 cited works; 586,186 → 589,291 reference links). As
  a result, a handful of interval bounds moved by 0.01, two correlations by 0.01, one robustness
  agreement by 0.01, and one tie in the lowest rank agreement (0.78) is now reported under a
  different indicator. No point estimate used in the report changed beyond the second decimal, and
  no conclusion changed. The committed results stay those of the committed corpus snapshot; the
  difference is recorded here as a known property of rehydrating from a live index ([DATASET](../data/DATASET.md)).

## Security reviewer

- Read-only API, rate limited per client, token required for non-loopback binding
  (`NOVELTY_API_TOKEN`), CSP and related headers. No secrets; public metadata only.

## UX reviewer

- Every claim on a page links to the experiment it comes from; pending items are shown as pending
  rather than as empty charts.
- Chart axis labels were clipped and ticks were not round numbers; fixed during review.
