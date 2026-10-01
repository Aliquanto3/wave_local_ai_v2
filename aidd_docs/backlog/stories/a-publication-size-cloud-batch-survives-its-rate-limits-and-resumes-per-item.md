---
type: story
status: ready
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
order: 12
---

# Story: A publication-size cloud batch survives its rate limits and resumes per item

**As** a consultant running a 100-plus item publication suite against a cloud subject or the judge pair
**I want** the retry budget a cloud batch gets to grow with its item count, and an interrupted batch to resume from the items it never wrote
**So that** a publication-size cloud batch is a slow run rather than a coin flip, and a partly written batch is completed rather than refused or paid for twice

Maps to: PRD AC "Given a cloud provider failure mid-suite (quota, rate limit, or retired model), every row already produced is persisted and the run is marked partial, naming the failing provider and item"; Methodology 11 ("Judge calls stay retryable and resumable: rate limits exist on paid tiers too, and a partially judged run resumes rather than restarting"); Methodology 4 (a publication suite holds 300 items, never fewer than 100); PRD Dependencies "rate-limit survival, retry and partial resume, still does"; the Dependencies row "The cloud retry budget and resume granularity at 100-item scale" of `aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md`; owner answer Q3 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`.

Needs: none. Stubbed HTTP proves the budget and the resume; no model run, API key, hardware or operator is required.

Current state: `settings.DEFAULT_CLOUD_RETRY_MAX_ATTEMPTS = 4` is a batch total, because `retry.RetryBudget` is one instance per provider batch shared across every item. `results.resume_skip_reason` reasons per `(run_id, provider, task_suite)` batch: a batch with no rows re-runs from item 1, a complete one is skipped, and a partly written one is refused ("per-item resume is out of scope"). A 100-item Google batch is 200 paced requests drawing on that budget of 4. The `done` story `a-rate-limited-run-persists-resumes-and-never-re-pays` shipped this behaviour at development-suite size and is not reopened: this story is the changed need at publication size.

## Acceptance

- The retry budget a cloud batch runs under grows with the batch's item count: a 100-item batch is not held to the total a 20-item batch gets. The rule deriving it is configuration, and the budget a batch actually ran under is readable off its rows.
- Budget scaling never masks a refusal: a model id absent from the live catalog, a judge-family collision and an unparseable judge response still fail immediately and are never retried, whatever the budget.
- `--resume` on a partly written batch issues calls only for the items that batch never wrote, and appends their rows. The `(run_id, provider, task_suite, item_id)` key stays unique: no item already on disk gets a second row, and no subject, judge or calibration call whose result is already recorded is issued again.
- A resume leaves every already-written row unchanged, and a batch completed by resume yields the same suite-level score, agreement figure and contested set as an uninterrupted batch over the same responses.
- A batch still incomplete after a resume stays marked partial, names the failing provider and item, and publishes no headline score.
- The rule is one rule over every CLI that writes quality rows, the suite CLI and the judged probe alike.

## Code it changes

- `src/wave_local_ai_v2/settings.py`: the budget rule replacing the fixed batch total, with its default and the reason for it.
- `src/wave_local_ai_v2/retry.py`: the budget derived from the batch's item count.
- `src/wave_local_ai_v2/results.py`: `resume_skip_reason` returns the items still to run instead of refusing a partly written batch.
- `src/wave_local_ai_v2/quality_cli.py`, `src/wave_local_ai_v2/judge_probe.py`: a resumed batch runs only its missing items; the budget a batch ran under is written onto its rows.
- `src/wave_local_ai_v2/row_contract.py`: the budget field and its `SCHEMA_VERSION` bump, with its reason in the version comment block.

## Tests it needs

- `tests/test_retry.py`: the derived budget grows with item count; a refusal is not retried under any budget.
- `tests/test_results.py`: a partly written batch returns exactly its missing item ids; a complete batch returns none; a batch of another suite under the same `run_id` is not counted.
- `tests/test_quality_cli.py` (HTTP stubbed): a 100-item cloud batch with injected 429s completes under the derived budget where the fixed total of 4 would have exhausted; a batch interrupted at item N resumes with calls issued for the missing items only, asserted on the stub's per-call count, and no item carries two rows; a judged batch resumed mid-way issues no judge call already recorded.

## Evidence it publishes

- The stubbed 100-item interrupted-and-resumed batch, its per-call count showing no item paid for twice, recorded in the story's plan: the precondition the interval epic names for a cloud batch on either publication suite.

## Cancellation

n/a: not cancelled.
