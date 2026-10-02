---
objective: "Every quality batch written from now on carries, beside its suite score and each per-language cell, a replayable percentile-bootstrap interval block and the minimum detectable effect read off the same resample, or a named reason where either is undefined."
status: implemented
---

# Plan: Every quality batch publishes its interval and what it could resolve

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A stdlib `score_interval` module (draw procedure, percentile bootstrap, minimum detectable effect, named null reasons, replay, batch invariants), wired into both scoring rules' batch aggregates as one `score_interval` row field under row schema "21" |
| **Source** | `aidd_docs/backlog/stories/every-quality-batch-publishes-its-interval-and-what-it-could-resolve.md` (acceptance as amended by commit `ec8839b`) |

## Phases

| #   | Phase                                                                 | File                          |
| --- | --------------------------------------------------------------------- | ----------------------------- |
| 1   | The statistics module and its oracle tests                            | [`phase-1.md`](./phase-1.md)  |
| 2   | The interval block on every quality row (schema "21")                 | [`phase-2.md`](./phase-2.md)  |
| 3   | Evidence over the committed classification rows                       | [`phase-3.md`](./phase-3.md)  |

## Decisions

| Decision | Why |
| -------- | --- |
| One new top-level row field, `score_interval`, holding the six-value header (`confidence_level`, `resamples`, `method`, `seed`, `generator`, `draw_procedure_id`) plus a `suite` cell and a `by_language` cell per language; `language_breakdown`/`score_breakdown` are left untouched. | Adding keys inside the existing breakdown cells would change a shape `row_contract`, `read_model` and `bundle_export` already validate and render; a separate block is additive, declared unrendered in one line, and leaves every older row readable as it is. |
| Each cell is `{n, lower, upper, minimum_detectable_effect, null_reason}`: the three values are all numbers and `null_reason` null, or all null and `null_reason` one of `zero_width` (every item carries the same value, so every resample is identical: a suite scored 1.0 or 0.0) or `no_items` (n=0). | "A value and exactly one non-null reason, never both", and each reason is decided by its own state on the item values, never by the observed width. The minimum detectable effect is undefined exactly when the interval is, so one reason covers both. |
| Draw procedure `stdlib-getrandbits-percentile/1`: items in ascending `item_id` order; each interval (suite, then each language) from a fresh `random.Random(seed)`; each draw `getrandbits(n.bit_length())` rejected until below n; the statistic is `math.fsum(values)/n`; the sorted resample means read at q = (1 - level)/2 and 1 - q by linear interpolation (Hyndman-Fan type 7, scipy's and numpy's default). | `getrandbits` on a seeded Mersenne Twister is stable across Python versions, unlike `choices`/`randrange`, whose internals Python does not promise; `item_id` order makes the replay independent of row order in a file; a fresh generator per interval lets any one cell replay from the block alone. Ties are equal floats, so their order cannot move an interpolated bound. |
| A fixed module seed (`DEFAULT_SEED`), recorded on every block; the generator is recorded through `subset_sampler.drawing_generator()` and printed on replay, not enforced. | Reuses the sampler's convention for generator identity; the draw procedure id, not the generator string, is what replay refuses on, because only `getrandbits` is drawn. |
| The interval is computed inside both scoring rules' batch aggregates, over the same item set the score is. | A resumed batch already reaches its score through the aggregate over prior rows plus new ones, so the interval follows the same item set by construction; the invariant check is the guard for a writer that breaks this. |
| `score_interval` is null exactly when the row publishes no suite score: a partial batch (added to `PARTIAL_NULL_SCORE_FIELDS`) and a judge-probe row (whose judged headline is not an exact-match or graded score and is outside this story). | No score, nothing to qualify; a block beside a null score would be an interval around nothing. |
| The three batch invariants run in `quality_cli._score_and_write` over the batch's prior rows plus the new ones before any row is appended, restricted to rows carrying a block; rows written partial before a resume keep their null block and are never rewritten. | "No already-published row is rewritten"; checking before writing keeps a broken block off disk. |
| The epic's Success Evidence still names Wilson within 0.01; the amended story governs (owner decision 2026-10-02, commit `ec8839b`). The epic is not edited here. | The implementer brief forbids editing an epic. |
