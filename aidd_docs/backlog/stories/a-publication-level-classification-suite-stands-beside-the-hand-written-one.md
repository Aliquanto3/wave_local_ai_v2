---
type: story
status: done
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source.md
  - aidd_docs/backlog/stories/a-publication-subset-redraws-to-the-same-items-from-its-recorded-rule.md
  - aidd_docs/backlog/stories/every-quality-batch-publishes-its-interval-and-what-it-could-resolve.md
  - aidd_docs/backlog/stories/the-laptop-proves-both-modes-and-republishes-the-bundle-once.md
order: 7
---

# Story: A publication-level classification suite stands beside the hand-written one

**As** an academic or technical reviewer weighing the classification results
**I want** a classification score over a seeded subset of a named public benchmark, at the publication level, published beside the hand-written 20-item score and never averaged with it
**So that** I can read one subject's classification interval and minimum detectable effect at a scale where a 10-point gap can be resolved, beside the same subject's 20-item interval

Maps to: PRD AC "Given a published suite, its rows state whether it was built to the development or the publication level, and a publication-level suite names each public benchmark its subset came from, that benchmark's licence, and the selection rule that produced the subset"; PRD AC "Given a published quality score, it is shown with a bootstrap confidence interval"; PRD Dependencies "Licence and redistribution terms of the public benchmarks whose subsets seed the publication-level suites"; Methodology 4, 5, 24; epic decisions "The two levels coexist", "The licence spike returns one of three verdicts, each with its consequence written in advance"; epic success check 12 (classification half). Whether the two levels rank the roster the same way is not this story's: it is `aidd_docs/backlog/stories/the-roster-ranks-the-same-way-at-the-development-and-publication-levels.md` (owner answer Q130 (a), 2026-10-03).

Needs: a real local model run (two published batches on the bench machine, in one session and on one subject: the publication suite over MInDS-14, and `classification-support-routing`); the network fetch of MInDS-14 at its pinned revision.

Blocked: through `depends_on` on `aidd_docs/backlog/stories/the-laptop-proves-both-modes-and-republishes-the-bundle-once.md`, `ready` and not yet built, which moves the published bundle's schema once (owner answer Q134 (a), 2026-10-03). The other four `depends_on` stories are `done`.

Scope note: a cloud batch on this suite runs under the item-scaled retry budget (`retry.derived_retry_budget`) and the per-item `--resume` of `aidd_docs/backlog/stories/a-publication-size-cloud-batch-survives-its-rate-limits-and-resumes-per-item.md` (`done`). It is not a `depends_on`, because the published batch this story requires can be a local one.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- Suites are data: `suite_registry.resolve` loads `src/wave_local_ai_v2/suite_data/*.json`, and `quality_cli._run` resolves `--suite` through it. Two suites exist; `classification-support-routing` is `suite_version` `"4"`, 20 items, `level` `development`, `max_output_tokens` 32.
- `suite_gate.gate_suite` certifies `publication`: at least `MIN_PUBLICATION_SUITE_ITEMS` (100), a `size_target` in `PUBLICATION_SIZE_TARGETS` (100, 300) with a `size_target_reason`, every item declaring `licence`, `source`, `source_revision`, and `contamination_risk` true exactly when `provenance` is `public`.
- `subset_sampler` (sampler version `"1"`) draws a classification rule with `stratify_by` `['language', <label field>]`, and `_stratify_problems` refuses a rule whose label field is not among its `content_fields`; the split is equal per language then per sorted label (MInDS-14 at 300: 100 per language, 8 per intent for the first two intents and 7 for the rest). An item id is `<source>:<stable key>`; `canonical_order` refuses a key repeated within a source. MInDS-14's key `path` (for example `fr-FR~ADDRESS/response_4.wav`) carries its locale, and the spike assumes it unique, so a repeat fails at the first draw. The rule's keys are closed (`RULE_KEYS`): the locale-to-language and label-name mapping live in the loader that writes the JSONL source table, recorded only as `loader` library and version. `subset_replay` replays a rule over that table. No loader for any public benchmark exists.
- The exact-label scorer knows only the hand-written labels: `scoring.score_item` parses every completion against `classification_suite.LABELS` (`billing`, `technical`, `account`, `other`), and `normalize_label` matches tokens of `_TOKEN_RE` `[a-z]+`, so a label holding an underscore can never be parsed. Ten of MInDS-14's fourteen intents hold one (`app_error`, `pay_bill`, ...), so as the code stands every such item would score `unparseable`. `scoring_rules.exact_label_match` receives no label set, and on a resumed batch `SuiteDefinition.score_items` passes it only the missing items. `judge.py` also calls `normalize_label`, over its rubric's categories.
- A quality row copies `suite_level`, `item_licence`, `item_source` and `item_source_revision` (`quality_rows.suite_item_fields`) and, from schema `"21"`, the `score_interval` block (`score_interval.check_batch_invariants` runs before a batch is appended). A row carries no item `content_hash` and no session id.
- `bundle_export` resolves each row's suite definition, without its items, into `suite_definition_*` columns and refuses a key with no entry in `SUITE_DEFINITION_FIELDS`, which documents only `context_length`, `max_output_tokens`, `prompt_set_hash`, `stop_sequences` and `thinking_policy`. The committed rows cite `classification-support-routing@2`, which predates `level`, so the refusal has not fired; a row citing `@4` or a publication suite would meet it on `level`, `size_target`, `size_target_reason` and `selection_rule.*`.
- `use_case_coverage.json`: the classification entry is `exercised` with `suite_ids` `["classification-support-routing"]`, a list a second id joins; `multilingual-en-fr-de` (`covered-by-dimension`) lists the same id.
- The committed `aidd_docs/results/quality-reference.jsonl` holds 80 rows, all `classification-support-routing`, `schema_version` `"7"`, none with `score_interval`; `tests/test_reference_bundle.py` expects every row at `PUBLISHED_BUNDLE_SCHEMA_VERSION` `"7"`.
- `LICENSE-DATA` section 1.1 covers the data files of `src/wave_local_ai_v2/suite_data/` and `aidd_docs/results/suite-definitions/` and the item fields of `quality-reference.jsonl` under CC-BY 4.0; section 2 states that the bundle holds no drawn item and names no drawn source. `aidd_docs/results/suite-definitions/NOTICE.md` says "No item here is drawn today", and `src/wave_local_ai_v2/suite_data/NOTICE.md` puts every suite definition in its directory under CC-BY 4.0.
- `scripts/audit_dependencies.py` audits `uv.lock` through `uv export --format pylock.toml` with no group flag, which exports the project's dependencies and the default `dev` group only. `pyproject.toml` declares one dependency group, `dev`, and no parquet reader.

## Acceptance

- A new classification suite id exists beside `classification-support-routing`. The hand-written suite keeps its id, its items, its CC-BY 4.0 licence, its published rows and its `development` level.
- The new suite certifies at `publication` (order 4): it holds 300 items where its source supplies them and never fewer than 100, records which target it was built to and why, and each of EN, FR and DE holds at least 25% of its items.
- Its items are drawn by order 5's sampler from MInDS-14 (`PolyAI/minds14` at revision `40ce77cb32a384e4d50a568e1ec39ac804019d33`, owner answer Q105 (a), 2026-10-03): configs `en-US`, `fr-FR` and `de-DE`, stable source key `path`, label `intent_class` mapped to its name, content fields `transcription` and the label field; 300 items, 100 per language, stratified by language and intent, with the selection rule, each item's licence, source, source revision and content hash recorded. Replaying the rule returns the same item ids in the same order.
- The SHA-256 of the source table the loader writes is recorded in the suite definition's `extra`. The CI replay test runs over a constructed fixture table; a documented operator replay re-fetches the table from the pinned hub revision and checks it against that hash (owner answer Q132 (a), 2026-10-03).
- A completion naming a MInDS-14 intent is parsed to it: the exact-label scorer takes its label set from the suite (declared in the definition, or derived from all of the suite's items' expected labels, never from a resumed batch's subset) and matches a label holding an underscore, such as `app_error`. `classification-support-routing` scores identically, item for item, and the judge's parse over its rubric categories does not move.
- Every drawn item is marked contamination-risk under Methodology 5.
- The spike's verdict is applied as the epic wrote it in advance. The spike returned permissive (CC BY 4.0) for MInDS-14, so items and rows ship unchanged, with no segregation and no redaction. `aidd_docs/results/README.md`, beside the statement of what the bundle is, states the rung and the attribution CC BY 4.0 requires: creator, copyright notice, licence link, source link and revision, and that each item was wrapped in a prompt template. The Hugging Face card at the pinned revision is the licence of record (owner answer Q131 (a), 2026-10-03): the loader records whether the pinned revision ships a licence file, `MInDS-14.zip` is not fetched, and the README states that the licence rests on the card. A licence file at the pinned revision naming anything other than CC BY 4.0 reopens the spike.
- `LICENSE-DATA` and the two NOTICE files stop claiming a drawn item under CC-BY 4.0: section 2 names MInDS-14 (`PolyAI/minds14` at its revision), CC BY 4.0, the permissive rung and the attribution it requires, in place of the sentences saying the bundle holds no drawn item; section 1.1's covered entries cover the hand-written items only; and `src/wave_local_ai_v2/suite_data/NOTICE.md` and `aidd_docs/results/suite-definitions/NOTICE.md` say that a drawn item carries its own source's licence, recorded on the item, with "No item here is drawn today" dropped. Whichever of this story and order 8 lands first writes section 2's drawn-source structure; the other extends it.
- The coverage record's `exercised` entry for classification gains this second suite id, on the shape `no-use-case-is-silently-absent` agrees; no new use-case entry is created.
- At least one batch over the new suite is published in the reference bundle as new rows, carrying its level and its interval block, under the supersede-don't-backfill discipline. The rows are appended after `the-laptop-proves-both-modes-and-republishes-the-bundle-once.md` has moved the bundle's schema, and `tests/test_reference_bundle.py`'s published-schema expectation follows that story, not this one (owner answer Q134 (a), 2026-10-03).
- Beside it, one development-level batch of `classification-support-routing` is published in the bundle on the same subject in the same bench session, so both sizes carry `score_interval` for the threshold review (order 9) (owner answer Q120 (a), 2026-10-03). Rows carry no session id, so the pair is defined as two batches with the same `roster_entry_id`, `fiche_hash` and `engine_build`, and a mismatch is checkable from the rows.
- The tabular export and `scripts/recompute_from_export.py` run clean over the bundle including the new rows of both batches.
- No published table averages the two levels: the development-level score leads and the publication-level score sits beside it as the scale check. [Methodology 4]

## Code it changes

- A new suite definition with its items and selection rule as JSON under `src/wave_local_ai_v2/suite_data/` (the seam settled data, Q1 (a)), its `extra` carrying the source table's SHA-256.
- The loader that writes MInDS-14 as the JSONL table `subset_replay` reads: a script under `scripts/` (owner answer Q135 (a), 2026-10-03). Its parquet reader, pyarrow pinned, sits in a locked `[dependency-groups]` group (for example `loaders`) in `pyproject.toml` and `uv.lock`, never a runtime dependency. `scripts/audit_dependencies.py` is extended so its `uv export` includes that group and the audit covers it.
- `scoring.py`, `scoring_rules.py` and `suite_registry.SuiteDefinition.score_batch` / `score_items`: the exact-label scorer takes its label set from the suite and matches multi-word labels. `quality_cli.py` already resolves `--suite` through `suite_registry` and needs no change for the suite to run.
- `bundle_export.py`: `SUITE_DEFINITION_FIELDS` entries for `level`, `size_target`, `size_target_reason`, every `selection_rule.*` leaf and the source-table hash key.
- `LICENSE-DATA` sections 1.1 and 2, `src/wave_local_ai_v2/suite_data/NOTICE.md`, `aidd_docs/results/suite-definitions/NOTICE.md`.
- `use_case_coverage.json`: the second suite id.

## Tests it needs

- The suite certifies at `publication`; its replay over a constructed fixture table returns the recorded ids; every item carries licence, source, revision, content hash and contamination-risk; the hand-written suite's snapshot and `prompt_set_hash` are unchanged.
- `app_error` and every other MInDS-14 intent parse to themselves; `classification-support-routing`'s scoring fixtures score identically; a resumed batch scores against the whole suite's label set; `judge.py`'s rubric parse is unchanged.
- The export and `scripts/recompute_from_export.py` run clean over a bundle holding a `classification-support-routing@4` batch and a publication batch.
- The two published batches share `roster_entry_id`, `fiche_hash` and `engine_build`.
- The dependency audit's export names the loaders group.
- `tests/test_data_licence.py` still passes: both NOTICE files still name CC-BY 4.0, `LICENSE-DATA` and MIT.

## Evidence it publishes

- The selection-rule record with the source-table hash, the published batch with its intervals, the development-level batch of `classification-support-routing` beside it, and the README section stating the licence rung applied and that the licence rests on the card.

## Cancellation

n/a: not cancelled.
