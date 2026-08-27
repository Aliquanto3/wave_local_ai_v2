---
type: story
status: ready
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/two-judges-of-different-families-or-an-honest-single-judge-flag.md
order: 5
---

# Story: A rate-limited run persists, resumes, and never re-pays

**As** a consultant running a judged suite on free-tier credentials
**I want** a rate limit to cost me the calls that remain rather than the whole run
**So that** a full-roster judged run is a slow question instead of an impossible one, and nothing already paid for is paid for twice

## Acceptance

- PRD acceptance: a cloud provider failure mid-suite — quota, rate limit, or retired model — persists every row already produced, marks the run partial, and names the failing provider and the item it failed on.
- A rate-limited call is retried with backoff before it is treated as a failure. The backoff honours the provider's retry-after hint where the spike found one, and falls back to exponential backoff where it did not; the run records how many retries each call took.
- The retry path covers both the judge calls orders 3 and 4 add and the existing Mistral subject path, which states "no retries" in its own first line and dies on a free-tier 429 today.
- Retries never mask a refusal. A model id absent from the live catalog, a judge-family collision, and a judge response that cannot be parsed each fail immediately and are not retried — a retry loop around a deterministic refusal turns a named error into a timeout.
- A resumed run is keyed by `run_id`: it reads back what that run already wrote, re-issues only the calls that never completed, and never re-issues a judge call whose result is already recorded.
- A resumed run's already-written rows are unchanged by the resume, and a resumed judged suite produces the same suite-level statistic and the same contested set as an uninterrupted run over the same responses.
- A partial run is distinguishable from a complete one when the results are read back, and a partial run publishes no headline score — a headline computed over the items that happened to complete before the limit is a biased sample, not a partial one.

## Code it changes

- `src/wave_local_ai_v2/retry.py` (new) — backoff over the shared HTTP boundary, driven by the status code and retry-after shape the spike recorded, with the retryable/non-retryable split explicit rather than inferred from the status alone.
- `src/wave_local_ai_v2/mistral_client.py`, `src/wave_local_ai_v2/google_client.py` — a rate-limit response raises a distinct retryable error subclass; both keep "no SDK, no streaming" and neither retries internally.
- `src/wave_local_ai_v2/results.py` — reading back the rows one `run_id` already wrote, so a resume knows what exists.
- `src/wave_local_ai_v2/judge.py` — judge results recorded per `(run_id, item_id, judge_model_id)`, so a resume can skip a call that already returned.
- `src/wave_local_ai_v2/quality_cli.py` — the resume entry point, the partial marking, and the failing provider and item named on it.

## Tests it needs

- `tests/test_retry.py` (new, HTTP stubbed) — a stubbed 429 followed by a 200 succeeds after backoff without sleeping in real time; a persistent 429 gives up and reports the provider and the item; a 400, an unavailable-model error and an unparseable judge response are not retried.
- `tests/test_quality_cli.py` (HTTP stubbed) — a run whose stub returns 429 partway through a judged suite persists the rows it produced, marks itself partial, names the provider and item, and publishes no headline score; resuming that `run_id` re-issues only the missing calls, asserted on the stub's per-call count, and leaves the already-written rows unchanged. The assertion is on the persisted rows and the call count, not on the backoff function.

## Evidence it publishes

- A forced mid-suite 429 producing a partial run that resumes and completes, with the stub's call count showing no judge call was paid for twice — the epic's fifth success check.

## Cancellation

n/a — not cancelled.
