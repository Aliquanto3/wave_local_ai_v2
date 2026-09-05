---
objective: "A paced, backing-off retry layer keeps the quality CLI's Mistral and Google batches from dying to a free-tier 429, and `--resume <run_id>` re-runs only the provider batches a prior invocation never finished, never re-paying for one that already completed."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A rate-limited run persists, resumes, and never re-pays (pacing + retry + resume scope)

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Retry-with-backoff and per-provider request pacing for `mistral_client.py`/`google_client.py`, wired through `quality_cli.py`, plus a `--resume <run_id>` flag that skips a provider batch already fully written under that run and re-runs an incomplete one from scratch — never issuing a second HTTP call for a `(run_id, provider)` pair the store already has all rows for. |
| **Source** | `aidd_docs/backlog/stories/a-rate-limited-run-persists-resumes-and-never-re-pays.md`, narrowed by the user's own scoping (see Decisions) |

## Phases

| #   | Phase                                    | File                         |
| --- | ----------------------------------------- | ---------------------------- |
| 1   | The pacing/retry primitives (`retry.py`) | [`phase-1.md`](./phase-1.md) |
| 2   | Clients raise a typed retryable error     | [`phase-2.md`](./phase-2.md) |
| 3   | `quality_cli.py` wiring + `--resume`      | [`phase-3.md`](./phase-3.md) |
| 4   | Live three-provider evidence + docs       | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| `aidd_docs/memory/external/google-ai-studio-api.md` | 429/`RESOURCE_EXHAUSTED`, no `Retry-After` header, hint at `error.details[].RetryInfo.retryDelay`; 429 and 503 retryable, 404/400 are not; 15 RPM free-tier ceiling; "pacing at 4 seconds" is the project's own prior recommendation. |
| `src/wave_local_ai_v2/quality_cli.py`'s own `GOOGLE_REQUEST_PACING_S` comment | Confirms a live run 429'd Google with no pacing at all, and that 4.5s was the value chosen to stay under the 15/min cap with margin — the figure this plan's 4.1s default narrows from; recorded as a risk below, not silently overridden. |
| `tests/test_quality_cli.py:590,596,1085,1095,1140,1143,1161,1164` | Confirms the existing, tested contract: a cloud provider's request failure (429 included) is caught by `_try_run_cloud_provider` and printed as `"<provider> skipped: <reason>"`, `main()` still exits 0, the run continues — this plan preserves that contract rather than making retry-budget exhaustion a hard `exit 1` (user decision, see below). |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision   | Why   |
| ---------- | ----- |
| Scope excludes `judge.py`, `agreement.py`, and the "partial run / no headline score" acceptance criteria from the full story. | The user pulled this story ahead of stories 3-4 specifically because `judge.py` doesn't exist yet; those criteria describe a suite-level statistic (kappa, contested-set headline) this codebase has no concept of today. Building it here would be inventing scope the story's own dependency graph says isn't ready. |
| Resume is per-`(run_id, provider)` batch, not per-`(run_id, provider, item)`. | `suite_accuracy`, `language_breakdown` and `verdict` are computed once, over every item in a provider's batch, at the end of `_run_cloud_batch`/`_score_and_write`. Persisting a real per-item row before those are known would mean writing a row twice per item (a nullable-stats draft, then a final one) or deferring those fields to read-time recomputation — a much larger refactor the user explicitly declined (see the recorded `AskUserQuestion` answer) in favor of: a provider batch with a full set of rows under `run_id` is skipped whole; an incomplete one (today, that means zero rows — a mid-batch failure never got as far as `_score_and_write`) is re-run from item 1, now paced and retried so it is expected to finish. |
| Retry-budget exhaustion still prints `"<provider> skipped: ..."` and lets the run continue (`exit 0`), not `exit 1`. | Confirmed by the user against the existing, tested "cloud providers are optional configuration" contract (`quality_cli.py`'s own docstring, and `tests/test_quality_cli.py`'s existing skip-line assertions) rather than silently breaking it. `RetryBudgetExhausted` is added to the same `except` tuple `_try_run_cloud_provider` already catches provider errors with. |
| `retries` and `resumed` become required fields on the `quality` row kind only (`SCHEMA_VERSION` "7" → "8"), not on `runtime`. | Resume and retry are quality-CLI-only in this story's scope; the runtime harness has no cloud calls and no resume flag, so widening its row contract would be an unrequested, unrelated schema bump. |
| Google's default pacing interval is set at the user-specified 4.1s, not the already-validated 4.5s the current stopgap comment cites. | Recorded as a risk (below): 4.1s (14.6 req/min) leaves less margin under the 15 RPM ceiling than the 4.5s a live run already confirmed safe. Acceptable here because this plan adds real 429 retry-with-backoff behind the pacer for the first time — a margin miss now degrades to a paced retry instead of a hard failure, which was not true when 4.5s was chosen. |

## Risks

- **4.1s Google pacing is tighter than the empirically-confirmed 4.5s.** Mitigated by retry-with-backoff now existing as a second line of defense; if the live-evidence phase (phase 4) still 429s Google under normal operation (not just at suite boundaries), tighten the default back toward 4.5s rather than leaving 4.1s as a false floor.
- **Mistral's retry-after hint is unconfirmed.** No memory file documents whether Mistral sends a `Retry-After` header on 429; `mistral_client.py`'s `RetryableRequestError` reads it opportunistically (standard HTTP header) and degrades to backoff-only when absent — this is not a live-confirmed fact the way Google's `RetryInfo.retryDelay` is, and should be flagged if the live-evidence run's Mistral 429 (if any) carries a header this code doesn't read correctly.
- **A `--resume` given a `run_id` with zero existing rows behaves identically to a fresh run** (nothing to skip), except every row it writes is marked `resumed: true` even though nothing was actually resumed. Documented as the flag's honest behavior in `cli.md`, not treated as an error — the user did not ask for run_id validation against a canonical "known runs" list, and inventing one is out of scope.
