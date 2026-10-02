---
objective: "A cloud batch's retry budget is derived from its item count by a configured rule and written on its rows, a cloud failure mid-batch persists the items already produced as a partial batch naming the failing provider and item, and `--resume` on a partly written batch issues calls only for the items it never wrote, in both CLIs that write quality rows."
status: implemented
---

# Plan: A publication-size cloud batch survives its rate limits and resumes per item

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Replace the fixed batch retry total with a per-item rule, persist a cloud batch interrupted mid-way as a marked partial batch, and resume it per item, with the suite score, agreement and contested set of a resumed batch equal to an uninterrupted one |
| **Source** | `aidd_docs/backlog/stories/a-publication-size-cloud-batch-survives-its-rate-limits-and-resumes-per-item.md` on branch `docs/slice-remaining-epics` (read-only); parent epic `any-open-ended-output-carries-two-judges-or-an-honest-flag`; owner answer Q3 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` on that branch |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The budget rule and the two row fields (schema "17") | [`phase-1.md`](./phase-1.md) |
| 2   | Per-item resume and partial persistence in the suite CLI | [`phase-2.md`](./phase-2.md) |
| 3   | The same rule in the judged probe | [`phase-3.md`](./phase-3.md) |
| 4   | Docs and the 100-item evidence | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision   | Why   |
| ---------- | ----- |
| The budget rule is `max(CLOUD_RETRY_MIN_RETRIES, ceil(items * CLOUD_RETRY_RETRIES_PER_ITEM))`, defaults `4` and `0.2`, replacing `CLOUD_RETRY_MAX_ATTEMPTS`. | A 20-item development batch keeps exactly the 4 the shipped story validated; a 100-item batch gets 20 and a 300-item one 60, so the budget per item is constant instead of shrinking with the suite. Both knobs are settings, so the rule is configuration. |
| The item count the rule reads is the number of items the invocation issues calls for (the whole batch on a fresh run, the missing items on a resume). | The budget tracks the calls actually issued; a resume of 5 missing items does not get a 300-item budget. Each row records the budget it ran under, so two segments of one batch stay distinguishable. |
| New quality-row field `retry_budget`: an object mapping each cloud provider whose calls the row's batch issued (subject and judges) to the retry total its calls drew from; `{}` for a batch with no cloud call. | One scalar cannot describe a judged probe row, whose subject and two judges drew from three budgets; a map covers both CLIs with one shape. The gate refuses a malformed map, a cloud row missing its own provider, and per-item `retries` above that provider's budget. |
| New quality-row field `partial_failure`: `null` when the batch the row belongs to was complete when the row was written, else `{provider, item_id, reason}` naming the call that stopped it. A partial row carries no suite-level score: `suite_accuracy`, `language_breakdown`, `suite_score`, `score_breakdown` and `judged_headline_score` are `null`, enforced by the gate. | The PRD AC ("marked partial, naming the failing provider and item") and the story's "publishes no headline score": a mean over the items that happened to finish is a biased sample. `failure_counts` stays a tally of the items written, a count not a rate. |
| Schema "16" -> "17", additive on quality rows only. No committed store is edited. | Runtime rows have no cloud call and no resume. |
| A cloud failure mid-batch (the provider's error type, a transport error, an exhausted budget) now writes the rows of the items already answered, marked partial, instead of discarding them. A failure before any item answered still writes nothing and prints `skipped`. Local subject failures still abort the run unchanged. | The PRD AC requires every produced row to persist. The local path has no rate limit and its failures are not paid for. |
| `results.resume_skip_reason` is replaced by `results.resume_missing_items`, which returns the batch's item ids not yet written under `(run_id, provider, task_suite)`, in suite order; an empty list means complete. | The story; the triple stays the key, so another suite's rows under the same `run_id` never count. |
| A batch completed by resume computes its suite-level fields over the prior rows' per-item outcomes plus the new ones, through one aggregation function per scoring rule (`scoring_rules.BATCH_AGGREGATES`) that the uninterrupted path also uses. The registry refuses a rule with no aggregate. | Same function on both paths makes "same suite score as an uninterrupted batch" structural, not coincidental. Rows carry every input the aggregate reads (`correct`/`item_score`, `failure_reason`, `language`). |
| Cost, token and energy totals on a resumed segment's rows cover that invocation's calls only. | Rows already written are never edited; summing the segments gives the batch cost, and no call is counted twice. Recorded as a tradeoff: a reader taking one row's `cost_total` as the batch cost undercounts a resumed batch. |
| The read model's subject card takes its suite-level score from a row of the run whose `partial_failure` is null when one exists. | Otherwise a batch completed by resume would render the null score of its first, partial segment. |
| The judged probe persists the items judged before a judge failure as partial rows, re-raises (exit 1, unchanged), and on `--resume` regenerates locally and judges only the missing items. Calibration calls do not exist in code yet, so there is nothing to skip. | Story acceptance "one rule over every CLI"; a regenerated local output is free, a judge call is not, and no judge call whose result is on a row is issued again. |
| A resume is refused, naming the field and writing nothing, when any earlier row of the batch differs from this invocation on `model_id`, `suite_version`, `prompt_set_hash`, `prompt_variant_id`/`_version`, `sampling`, `roster_entry_id`, `endpoint`, `thinking_policy`, or (probe) the judge model ids; a field an old row lacks counts as different (review round 1). | Per-item resume folds earlier rows into the published score, so a model retired mid-batch and replaced before the resume would otherwise publish one score over two models. |
| A comparison side whose batch never completed (every row carries `partial_failure`) is an observation naming it, not a test; a batch completed by resume is a test (review round 1). | The comparison story keeps "a partially observed row set is not a refusal", but a failure-truncated batch is a run-order prefix, not a random subset, so its p is kept and never read as a verdict. |
