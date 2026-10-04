# Review: a publication-level classification suite stands beside the hand-written one

## Round 1 (2026-10-04, Stage A `95040a7` + uncommitted Stage B)

VERDICT: PASS

Gates run by the reviewer: `timeout 900 uv run pytest -q` => `3120 passed, 20 skipped, 2 warnings in 475.03s`, coverage 98.51%, exit 0; ruff check, ruff format --check, mypy src/ scripts/ clean; detect-secrets hook over the changed and untracked files exit 0, baseline unmodified; `merge-bundle --check` => "committed bundle equals the merge (6 runtime, 605 quality, 0 refusals)"; `wave-local-ai-v2-validate` (FICHE_REGISTRY_DIR unset) over both bundle files and the laptop store => `checked 1216 row(s)`, exit 0; export + `scripts/recompute_from_export.py` => `320 values recomputed (interval), 0 differ`, exit 0. Offline replay (no download) over the implementer's cached table: SHA-256 `9172eba3...1dc06` equals `source_table.sha256`, `subset_replay --suite classification-banking-intents-minds14` => `reproduced: 300 items, same ids, same order`.

Acceptance:
1. New suite id beside the hand-written one, which is untouched: proven (`95040a7 --stat` does not touch `classification-support-routing.json` or its snapshots; `test_suite_registry._SHIPPED` hash unchanged).
2. Certifies `publication`, 300 items, target + reason, each language >= 25%: proven (`test_the_minds14_suite_certifies_at_publication_with_its_recorded_draw`; counts 100/100/100, 8/8/7x12 per intent).
3. Drawn by the sampler from `PolyAI/minds14@40ce77cb...`, `path` key, intent names, `transcription` content, replay: proven (`test_minds14_suite.py` fixture replay, `evidence/replay.log`, reviewer replay above).
4. Source-table SHA-256 in `extra`, CI fixture replay, documented operator replay: proven (`source_table` block; `scripts/minds14_suite.py verify`; results README, `memory/cli.md`).
5. Scorer label set from the whole suite, underscore labels, hand-written suite and judge parse unchanged: proven (`SuiteDefinition.labels`; `test_every_minds14_intent_parses_to_itself`, `test_a_one_word_label_set_parses_as_the_one_token_rule_did`, `test_a_resumed_subset_is_parsed_against_the_whole_suites_labels`, `test_the_categorical_parse_is_the_first_category_word`, no judge call).
6. Every drawn item contamination-risk: proven (same registry test; 300/300 rows `contamination_risk: true`).
7. Permissive rung, README attribution, card as licence of record, licence-file check: proven (README section; `licence_file_at_revision: false`; `build_definition` refuses a revision shipping a licence file, `test_a_revision_shipping_a_licence_file_is_not_drawn`).
8. `LICENSE-DATA` sections 1.1 and 2, both NOTICE files: proven (`test_section_two_names_the_drawn_source_its_terms_and_its_attribution`, `test_neither_suite_notice_claims_a_drawn_item_under_cc_by`).
9. Coverage record gains the id, no new entry: proven (one-line diff of `use_case_coverage.json`).
10. Publication batch in the bundle with level and interval, after the schema move: proven (300 rows, schema "30", `suite_level: publication`, `score_interval` present; additions only, one `@@ -285,0 +286,320 @@` hunk per file).
11. Development batch, same subject and session, checkable triple: proven (20 rows `classification-support-routing@5`; all 320 rows `tree_dirty: false`, commit `95040a7`, same `roster_entry_id`/`fiche_hash`/`engine_build`; batches 07:37 and 07:38; pairing test added).
12. Export and recompute clean: proven (reviewer run above).
13. No averaging, development leads: proven (README table and text).

Secrets: 299 new baseline entries, all `Hex High Entropy String`: 297 item `content_hash` values, the `source_table.sha256` and the `source_revision`; the hook's exclude pattern is unchanged since `c68b23e`. Dependency group: `loaders = ["pyarrow==25.0.1"]`, same pin as `release`; `test_pyarrow_is_pinned_in_the_release_and_loaders_groups_and_nowhere_else` also asserts that pyarrow is absent from the runtime dependencies, the default groups and the Dockerfile.

Blocking findings: none.

Non-blocking findings:
1. `tests/test_reference_bundle.py:398-424`: the pairing test is already satisfied by the subject's earlier `classification-support-routing@5` batch (same triple, with an interval), so it would not catch a missing same-session batch. Add `commit_sha` to the key. It also asserts that every publication batch is MInDS-14, which breaks when order 8's publication suite lands.
2. `tests/test_quality_cli.py:3318`: `test_a_variant_changes_the_prompt_and_nothing_else_on_every_suite[classification-banking-intents-minds14]` takes 170 s, so a full run now takes 475 s against 213 s at the previous story. Parametrize it over a sliced suite.
3. `verdict.select_quality_references` (`verdict.py:310-337`) keys on `task_suite`, not `suite_id`. Two suites now share `classification`, so their versions can collide (for example `support-routing@2` in the schema-7 file and a future `minds14@2`). Add `suite_id` to the key.
4. `read_model.overview_quality_view` groups by `task_suite`, so the classification use case's per-run comparator list now mixes both levels. It is not averaged.
5. `scripts/assemble_release_archive.py:515`: "the data is CC-BY 4.0" now also covers PolyAI-licensed items in `quality_items.csv`. The attribution reaches the archive only through `LICENSE-DATA` section 2.

## Round 2 (2026-10-04, fixes for round-1 non-blocking findings 1-3)

VERDICT: PASS

Gates: `timeout 900 uv run pytest -q` => `3122 passed, 20 skipped, 2 warnings in 294.35s`, coverage 98.51%, exit 0 (round 1: 475 s). ruff check, ruff format --check, mypy src/ scripts/ clean. No file under `aidd_docs/results/comparisons/` or `leader-sets/` changed; bundle rows unchanged since round 1.

- `verdict.select_quality_references` (`verdict.py:334-348`): the `suite_id` clause holds whenever either side lacks one, so a row without `suite_id` selects exactly what it did before (`test_a_row_without_a_suite_id_is_matched_on_task_suite_as_before`). A mismatch is `not_comparable` (`test_a_publication_batch_never_selects_the_hand_written_suites_reference`). Verdicts are written once at run time and never recomputed. Before this story only one suite had `task_suite` `classification`, so no committed verdict would have selected differently. The only caller is `quality_cli.py:1526`.
- The not-comparable reason text changed (`verdict.py:478-479`). 545 committed rows keep the old wording, untouched under supersede-don't-backfill. No code matches on that string (grep over `src`, `scripts` and `tests`).
- Slice (`tests/test_quality_cli.py:3318-3365`): the argument is sound. A variant transforms each prompt on its own by task family, and baseline and variant both run over the same slice, so the invariance check is unweakened. The slice keeps every language, label and item shape, asserted against the full suite. The derived label set equals the full suite's, so the parse is unchanged. `monkeypatch.setitem(_LOADED, ...)` is restored at teardown.
- Pairing key (`tests/test_reference_bundle.py:398-432`): it now includes `commit_sha`, so only this session's development batch (commit `95040a7`) satisfies it, and the earlier `@5` batch no longer stands in. The publication filter is scoped to `task_suite == "classification"`, so order 8's publication suite will not trip it.

Blocking findings: none.
Non-blocking: round-1 items 4 and 5 (read-model grouping, release-archive licence line) remain open as notes.
