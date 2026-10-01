---
type: story
status: ready
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
order: 1
---

# Story: Every quality batch publishes its interval and what it could resolve

**As** an academic or technical reviewer reading a published quality score
**I want** the score to arrive with its bootstrap confidence interval, the n it was computed over and the smallest difference that suite could have resolved, or a named reason where any of these is undefined
**So that** I can tell how much a 20-item score can be trusted, and never read "not distinguishable" as "the same" or a zero-width interval as certainty

Maps to: PRD AC "Given a published quality score, it is shown with a bootstrap confidence interval"; PRD User Story "As an academic or technical reviewer, I want the sample size, the confidence interval and the significance test behind every published claim"; Methodology 9, 24; epic decisions "A seed alone does not reproduce an interval", "Failed generations resample with everything else", "The interval is published at both levels", "An undefined statistic publishes a named reason, never a number", "A detection limit is published beside the interval", "The statistics ship in-repo on the standard library, with scipy as a dev-only oracle"; epic success checks 3, 4, 5 (interval and cell reasons) and 6.

Needs: none. Every check runs on constructed batches and fixtures; no model run, API key, hardware or operator is required.

Current state: no interval exists anywhere in the codebase. `scoring.py` publishes `SuiteScore`, `GradedSuiteScore` and per-language cells; `score_suite_by_language` returns `accuracy=0.0, n=0` for an empty cell; `agreement.py` already carries the value-plus-one-reason shape this story reuses.

## Acceptance

- Every quality batch written from now on carries, on the suite score and on each per-language cell, a bootstrap confidence interval, for the exact-match and the graded scorer alike, at the development level as well as at any later publication level. A development-level score keeps its `indicative` marking beside its interval. [Methodology 24; epic decision "The interval is published at both levels"]
- The interval block carries six values beside the score it qualifies: confidence level 95%, resample count 10 000, method `percentile`, the seed, the random generator's identity and version, and a versioned draw-procedure id whose published definition covers draw order, tie handling and percentile interpolation. The suite score resamples unstratified; a per-language cell resamples stratified within its language. [Methodology 24]
- A failed generation stays in the resampled item set as the zero Methodology 9 makes it; an interval over the successes alone is never published.
- Every row of one batch carries the identical interval block, the way `language_breakdown` already rides every row of a batch. No already-published row is rewritten with an interval it was never written with.
- Beside every interval, the batch publishes a minimum detectable effect for its suite and scoring kind, read off the same resample rather than computed a second way.
- Each undefined or misleading case publishes a value and exactly one non-null reason, never both, and each reason is produced by the state that names it and by no other: a suite scored 1.0 or 0.0 returns a zero-width reason rather than `[1.0, 1.0]`; a language cell at n=0 returns its reason rather than an interval around 0.0.
- Replaying a recorded interval block (seed, generator identity and version, draw-procedure id, resample count, method, confidence level) over the same items returns the identical interval, bit for bit.
- On a proportion, the bootstrap agrees with the Wilson 95% reference interval to within 0.01 on each bound at n=20, p=0.80 and at n=100, p=0.80. Wilson is the one reference, named in advance.
- Three invariants hold on every batch and fail loudly when broken: the point estimate lies inside its own interval; the n the interval was computed over equals the n already published in `language_breakdown` or `score_breakdown`; every row of the batch carries the identical block. A resumed batch whose interval and score were computed over different item sets fails them.
- The statistics run on the standard library at runtime; `scipy` is added as a dev-only test oracle and never imported by `src/`.
- The new contract fields are declared unrendered in the view partition (`QUALITY_FIELDS_NOT_RENDERED`), so the build passes without any view rendering them; whether the pitch renders them is that epic's call.

## Code it changes

- `src/wave_local_ai_v2/` (new statistics module): the percentile bootstrap, the draw procedure and its versioned id, the minimum detectable effect, the named null reasons.
- `src/wave_local_ai_v2/scoring.py`, `quality_rows.py`, `quality_cli.py`: the interval block computed once per batch over the scored items and attached to every row.
- `src/wave_local_ai_v2/row_contract.py`: the interval block fields and their validation; `SCHEMA_VERSION` bump.
- `src/wave_local_ai_v2/read_model.py`: the new fields declared unrendered.
- `pyproject.toml`: `scipy` in the `dev` dependency group only.

## Tests it needs

- A hand-computed interval on a small fixture; the Wilson agreement at both sizes; scipy's bootstrap as an independent oracle where its convention matches, and a test documenting the convention where it does not.
- Bit-for-bit replay of a recorded block; a changed seed changes the interval.
- Each null reason produced by its own state and by no other.
- The three batch invariants, including a constructed resumed batch that breaks the n invariant.
- `src/` imports no `scipy` (asserted, not assumed).

## Evidence it publishes

- The interval and minimum detectable effect the new code computes over the committed `classification-support-routing` rows of `aidd_docs/results/quality-reference.jsonl`, recorded in `aidd_docs/results/README.md` as an analysis over existing rows, never written back onto them.

## Cancellation

n/a: not cancelled.
