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
order: 7
---

# Story: A publication-level classification suite stands beside the hand-written one

**As** an academic or technical reviewer weighing the classification results
**I want** a classification score over a seeded subset of a named public benchmark, at the publication level, published beside the hand-written 20-item score and never averaged with it
**So that** I can see whether a finding on the small, uncontaminated suite survives at a scale where a 10-point gap can be resolved

Maps to: PRD AC "Given a published suite, its rows state whether it was built to the development or the publication level, and a publication-level suite names each public benchmark its subset came from, that benchmark's licence, and the selection rule that produced the subset"; PRD AC "Given a published quality score, it is shown with a bootstrap confidence interval"; PRD Dependencies "Licence and redistribution terms of the public benchmarks whose subsets seed the publication-level suites"; Methodology 4, 5, 24; epic decisions "The two levels coexist", "The licence spike returns one of three verdicts, each with its consequence written in advance"; epic success check 12 (classification half).

Needs: a real local model run (one published batch on the bench machine) over the source the owner picks in Q105; the network fetch of that source at its pinned revision.

Blocked: by Q105 in `aidd_docs/tasks/2026_10/2026_10_02_backlog-refinement/owner-questions.md`, the owner's choice of source, on which the spike `aidd_docs/backlog/spikes/which-public-classification-benchmark-seeds-the-publication-suite-and-on-what-terms.md` is `blocked` (no live run remains): MInDS-14 (`PolyAI/minds14` @ `40ce77cb32a384e4d50a568e1ec39ac804019d33`) or MASSIVE 1.1 (`AmazonScience/massive` @ `ff6bd8e4b27c3543e4f8fe2108f32bb95a6f8740`), both CC BY 4.0, permissive rung either way. Every `depends_on` story, the suite seam `aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md` included, is `done`.

Scope note: a cloud batch on this suite runs under the item-scaled retry budget (`retry.derived_retry_budget`) and the per-item `--resume` of `aidd_docs/backlog/stories/a-publication-size-cloud-batch-survives-its-rate-limits-and-resumes-per-item.md` (`done`). It is not a `depends_on`, because the published batch this story requires can be a local one.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- Suites are data: `suite_registry.resolve` loads `src/wave_local_ai_v2/suite_data/*.json`, and `quality_cli._run` resolves `--suite` through it. Two suites exist; `classification-support-routing` is `suite_version` `"4"`, 20 items, `level` `development`, `max_output_tokens` 32.
- `suite_gate.gate_suite` certifies `publication`: at least `MIN_PUBLICATION_SUITE_ITEMS` (100), a `size_target` in `PUBLICATION_SIZE_TARGETS` (100, 300) with a `size_target_reason`, every item declaring `licence`, `source`, `source_revision`, and `contamination_risk` true exactly when `provenance` is `public`.
- `subset_sampler` (sampler version `"1"`) draws a classification rule with `stratify_by` `['language', <label field>]`, the label among `content_fields`, split equally per language then per sorted label (MInDS-14 at 300: 100 per language, 8 per intent for the first two intents and 7 for the rest). An item id is `<source>:<stable key>`; `canonical_order` refuses a key repeated within a source, so MASSIVE's repeated `id` needs the loader-computed `locale/id` the spike names. The rule's keys are closed (`RULE_KEYS`): the locale-to-language and label-name mapping live in the loader that writes the JSONL source table, recorded only as `loader` library and version. `subset_replay` replays a rule over that table. No loader for any public benchmark exists.
- A quality row copies `suite_level`, `item_licence`, `item_source` and `item_source_revision` (`quality_rows.suite_item_fields`) and, from schema `"21"`, the `score_interval` block (`score_interval.check_batch_invariants` runs before a batch is appended). A row carries no item `content_hash`.
- `use_case_coverage.json`: the classification entry is `exercised` with `suite_ids` `["classification-support-routing"]`, a list a second id joins; `multilingual-en-fr-de` (`covered-by-dimension`) lists the same id.
- The committed `aidd_docs/results/quality-reference.jsonl` holds 80 rows, all `classification-support-routing`, `schema_version` `"7"`, none with `score_interval`.

## Acceptance

- A new classification suite id exists beside `classification-support-routing`. The hand-written suite keeps its id, its items, its CC-BY 4.0 licence, its published rows and its `development` level.
- The new suite certifies at `publication` (order 4): it holds 300 items where its source supplies them and never fewer than 100, records which target it was built to and why, and each of EN, FR and DE holds at least 25% of its items.
- Its items are drawn by order 5's sampler from the benchmark Q105 picks among the two the spike names, stratified by language and label, with the selection rule, each item's licence, source, source revision and content hash recorded. Replaying the rule returns the same item ids in the same order.
- Every drawn item is marked contamination-risk under Methodology 5.
- The spike's verdict is applied as the epic wrote it in advance. The spike returned permissive (CC BY 4.0) for both qualifying sources, so items and rows ship unchanged, with no segregation and no redaction. `aidd_docs/results/README.md`, beside the statement of what the bundle is, states the rung and the attribution CC BY 4.0 requires: creator, copyright notice, licence link, source link and revision, and that each item was wrapped in a prompt template. When the loader fetches the source it records the licence file the source ships (MInDS-14 zip) or the tarball's SHA-256 (MASSIVE); a licence other than CC BY 4.0 reopens the spike.
- The coverage record's `exercised` entry for classification gains this second suite id, on the shape `no-use-case-is-silently-absent` agrees; no new use-case entry is created.
- At least one batch over the new suite is published in the reference bundle as new rows, carrying its level and its interval block, under the supersede-don't-backfill discipline.
- No published table averages the two levels: the development-level score leads and the publication-level score sits beside it as the scale check. [Methodology 4]

## Code it changes

- A new suite definition with its items and selection rule as JSON under `src/wave_local_ai_v2/suite_data/` (the seam settled data, Q1 (a)), and the loader that writes the chosen source as the JSONL table `subset_replay` reads.
- `use_case_coverage.json`: the second suite id. `quality_cli.py` already resolves `--suite` through `suite_registry`; no change is expected there.

## Tests it needs

- The suite certifies at `publication`; its replay returns the recorded ids; every item carries licence, source, revision, content hash and contamination-risk; the hand-written suite's snapshot and `prompt_set_hash` are unchanged.

## Evidence it publishes

- The selection-rule record, the published batch with its intervals, and the README section stating the licence rung applied.

## Cancellation

n/a: not cancelled.
