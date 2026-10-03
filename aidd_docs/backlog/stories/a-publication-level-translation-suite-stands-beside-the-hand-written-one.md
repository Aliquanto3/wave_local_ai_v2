---
type: story
status: proposed
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source.md
  - aidd_docs/backlog/stories/a-publication-subset-redraws-to-the-same-items-from-its-recorded-rule.md
  - aidd_docs/backlog/stories/every-quality-batch-publishes-its-interval-and-what-it-could-resolve.md
order: 8
---

# Story: A publication-level translation suite stands beside the hand-written one

**As** an academic or technical reviewer weighing the translation results
**I want** a chrF score over a seeded subset of a named public translation benchmark, at the publication level, published beside the hand-written 21-item score and never averaged with it
**So that** I can see whether a translation finding survives at a scale where the per-direction cells are no longer seven items each

Maps to: PRD AC "Given a published suite, its rows state whether it was built to the development or the publication level, and a publication-level suite names each public benchmark its subset came from, that benchmark's licence, and the selection rule that produced the subset"; PRD AC "Given a published quality score, it is shown with a bootstrap confidence interval"; PRD Dependencies "Licence and redistribution terms of the public benchmarks whose subsets seed the publication-level suites"; Methodology 4, 5, 24; epic decisions "The two levels coexist", "The licence spike returns one of three verdicts, each with its consequence written in advance"; epic Dependencies "The publication-level translation suite also stands beside `translation-business-short-form`"; epic success check 12 (translation half).

Needs: a real local model run (one published batch on the bench machine), after Q106 is answered; the network fetch of the source at its pinned revision.

Blocked: by Q106 in `aidd_docs/tasks/2026_10/2026_10_02_backlog-refinement/owner-questions.md` (accept Google's Apache-2.0 label over the WMT24 source text and publish WMT24++ on the permissive rung, publish it on the no-redistribution rung, or take NTREX-128 on the share-alike rung), on which the spike `aidd_docs/backlog/spikes/which-public-translation-benchmark-seeds-the-publication-suite-and-on-what-terms.md` is `blocked` (no live run remains). Also by Q118 and Q119, two acceptance doubts the spike leaves to this story's own definition: Q118, the suite's `max_output_tokens` (the hand-written suite's 128 truncates WMT24++ paragraph-level segments, which Methodology 9 scores 0 as a suite-cap failure), and Q119, whether the draw is stratified by `domain` as well as by language (sampler version `"1"` accepts only `['language']` on a translation rule, so domain strata need a sampler version `"2"`). Every `depends_on` story, the suite seam `aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md` included, is `done`.

Scope note: a cloud batch on this suite runs under the item-scaled retry budget (`retry.derived_retry_budget`) and the per-item `--resume` of `aidd_docs/backlog/stories/a-publication-size-cloud-batch-survives-its-rate-limits-and-resumes-per-item.md` (`done`). It is not a `depends_on`, because the published batch this story requires can be a local one.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- Suites are data: `suite_registry.resolve` loads `src/wave_local_ai_v2/suite_data/*.json`, and `quality_cli._run` resolves `--suite` through it. `translation-business-short-form` is `suite_version` `"3"`, 21 items, seven per direction (`en`->`fr`, `fr`->`de`, `de`->`en`; an item's `language` is its source language), `level` `development`, `max_output_tokens` 128, scored by `chrf_against_reference`.
- `suite_gate.gate_suite` certifies `publication`: at least `MIN_PUBLICATION_SUITE_ITEMS` (100), a `size_target` in `PUBLICATION_SIZE_TARGETS` (100, 300) with a `size_target_reason`, every item declaring `licence`, `source`, `source_revision`, and `contamination_risk` true exactly when `provenance` is `public`.
- `subset_sampler` (sampler version `"1"`): a translation rule's `stratify_by` must be exactly `['language']` (`_stratify_problems`), split equally across EN, FR and DE. An item id is `<source>:<stable key>` and `canonical_order` refuses a key repeated within one source, so a source table offering one WMT24++ segment in all three directions under the bare `segment_id` the spike names is refused: the loader either computes a direction-qualified key (as the spike does for MASSIVE's `locale/id`) or assigns each segment to one direction before the draw. The rule's keys are closed (`RULE_KEYS`): the `is_bad_source` exclusion, the pair join and the post-filter pool size live in the loader and the README, not in the rule, which records the loader as library and version only. No loader for any public benchmark exists.
- A quality row copies `suite_level`, `item_licence`, `item_source` and `item_source_revision` (`quality_rows.suite_item_fields`) and, from schema `"21"`, the `score_interval` block; it carries no item `content_hash`.
- `use_case_coverage.json`: the translation entry is `exercised` with `suite_ids` `["translation-business-short-form"]`, a list a second id joins.
- The hand-written suite's "published rows" are its suite-definition snapshots (`aidd_docs/results/suite-definitions/translation-business-short-form@1.json` to `@3.json`) only: the committed `quality-reference.jsonl` holds no translation row, and the 2026-09-06 translation runs live in the untracked live store (`aidd_docs/results/README.md`, "The translation suite's first live run").
- `LICENSE-DATA` section 2 excludes drawn items from the CC-BY 4.0 grant and names no drawn source; section 3 holds two declarations.

## Acceptance

- A new translation suite id exists beside `translation-business-short-form`. The hand-written suite keeps its id, its items, its CC-BY 4.0 licence, its published rows and its `development` level.
- The new suite certifies at `publication` (order 4): it holds 300 items where its source supplies them and never fewer than 100, records which target it was built to and why, and each of EN, FR and DE holds at least 25% of its items.
- Its items are drawn by order 5's sampler from the benchmark the spike names, stratified by language, with the selection rule, each item's licence, source, source revision and content hash recorded. Replaying the rule returns the same item ids in the same order.
- Every drawn item is marked contamination-risk under Methodology 5.
- Rows are graded rows carrying the metric triple (`metric_id`, `metric_version`, `metric_params`) as the hand-written translation suite's do, so the interval and any paired test route to the graded path.
- The spike's verdict is applied as the epic wrote it in advance: permissive ships items and rows unchanged; share-alike segregates the drawn items and their derived rows under their own licence file; no-redistribution carries `prompt` and `reference_output` on the rows redacted to the per-item content hash. Whichever applies is written into `aidd_docs/results/README.md`.
- The coverage record's `exercised` entry for translation gains this second suite id, on the shape `no-use-case-is-silently-absent` agrees; no new use-case entry is created.
- At least one batch over the new suite is published in the reference bundle as new rows, carrying its level and its interval block, under the supersede-don't-backfill discipline.
- No published table averages the two levels: the development-level score leads and the publication-level score sits beside it as the scale check. [Methodology 4]

## Code it changes

- A new suite definition with its items and selection rule as JSON under `src/wave_local_ai_v2/suite_data/` (the seam settled data, Q1 (a)), and the loader that writes the source as the JSONL table `subset_replay` reads.
- `use_case_coverage.json`: the second suite id. `quality_cli.py` already resolves `--suite` through `suite_registry`; no change is expected there.

## Tests it needs

- The suite certifies at `publication`; its replay returns the recorded ids; every item carries licence, source, revision, content hash and contamination-risk; the hand-written suite's snapshot and `prompt_set_hash` are unchanged.

## Evidence it publishes

- The selection-rule record, the published batch with its intervals, and the README section stating the licence rung applied.

## Cancellation

n/a: not cancelled.
