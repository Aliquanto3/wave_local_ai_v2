# Review: a publication-level translation suite stands beside the hand-written one

## Round 1 (2026-10-04, Stage A `0f69b60` + uncommitted Stage B)

VERDICT: CHANGES-REQUIRED

Gates run by the reviewer: `timeout 900 uv run pytest -q` => `3147 passed, 20 skipped, 2 warnings in 262.39s`, coverage 98.51%, exit 0. ruff check, ruff format --check, `mypy src/ scripts/` are clean. The detect-secrets hook, run over every modified and untracked file against a copy of the baseline, exits 0 and leaves the copy unchanged. `merge-bundle --check` => "committed bundle equals the merge (6 runtime, 926 quality, 0 refusals)". `wave-local-ai-v2-validate` (`FICHE_REGISTRY_DIR` unset) checks 926, 6 and 926 rows, each exit 0. Export + `scripts/recompute_from_export.py` => `360 values recomputed (interval), 0 differ`, exit 0.

Offline checks, with no download, over the implementer's cached raw pair files:
- Each file's git blob SHA-1 equals the oid in `fetch-record.json`. The files hold 998 rows, 38 of them `is_bad_source`, the canary included.
- The rebuilt table hashes to `db57a8a4...f4ed` and is byte-equal to the cached table and to `source_table.sha256`.
- `build_definition`, re-run over that table, the record and `evidence/token-counts.json`, gives a file byte-equal to the committed `translation-mixed-domain-wmt24pp.json`.
- `subset_replay --suite translation-mixed-domain-wmt24pp` => `reproduced: 300 items, same ids, same order`.
- None of the 300 items fails the raw-file check of `source_text`, `reference` and `domain` against the direction's sides.
- Every item's `reference_tokens` equals the evidence count. The longest is 304, over the drawn items and over the 960-row pool alike, so the cap is 608.

Acceptance:
1. New suite id beside `translation-business-short-form`, which is untouched: proven. Its file and snapshots were last changed in `90115fc`. Its `_SHIPPED` hash is unchanged. `test_the_hand_written_suite_keeps_its_id_items_licence_and_level` passes.
2. Publication, 300 items, target and reason, each language at least 25%: proven (`test_the_committed_suite_certifies_at_publication_with_its_recorded_draw`, 100/100/100).
3. Sampler draw from `google/wmt24pp@fd7405c0`, join, `is_bad_source` dropped, `segment_id % 3` directions, bare key, target-side references, stratified by language under sampler "1", pools and per-domain counts in the README, `domain` on each item, replay: proven by the `test_wmt24pp_suite.py` fixture tests, `test_the_readme_per_domain_counts_are_the_definitions` and the reviewer's rebuild above.
4. Table SHA-256 in `extra`, CI fixture replay, documented operator replay: proven by `source_table`, the `verify` subcommand, the README and `memory/cli.md`. The live `verify` was not run, since it needs a download; the offline equivalent passes.
5. Cap derived, with its basis and a reason naming the subject's tokenizer, and the truncated count stated (0): proven. The basis names `granite-4.0-h-350m-q8` with its GGUF and llama-server b10537. CI cannot run that tokenizer, so `test_the_committed_cap_is_twice_the_longest_reference_under_the_subjects_tokenizer` checks only the arithmetic, a UTF-8 byte bound and the named entry and file. The plan says this openly, so the check is honest but weak. The real count rests on `evidence/token-counts.json`, which the reviewer's byte-equal rebuild ties to the definition. In the rows, `truncated_max_tokens` is 0 and the longest output is 320 tokens.
6. Contamination-risk: proven. 300/300 items and 300/300 rows carry it.
7. Graded rows with the metric triple: proven (`chrf`, "1", same params on all 321 rows; `test_a_bundle_holding_both_translation_levels_exports_and_recomputes`).
8. Permissive rung, Apache text, LICENSE-DATA 2.2 and declaration 3, README statements: proven, except in `machines/` (see blocking 1). The three copies are LF, 11358 bytes, SHA-256 `cfc7749b...3d30`, which is the canonical file's hash. The relevant tests are `test_every_directory_holding_drawn_wmt24pp_items_carries_the_apache_text` and `test_section_two_names_wmt24pp_and_section_three_its_research_use_origin`.
9. LICENSE-DATA and the two named NOTICEs stop claiming drawn items under CC-BY: proven for the files the story names. `machines/NOTICE.md` still makes the claim (see blocking 1).
10. Coverage record gains the id, and no new entry is added: proven (one-line diff).
11. Publication batch in the bundle with its level and interval, after the schema move: proven. All rows are schema "30" with `score_interval`. Each store's diff is one hunk, `@@ -605,0 +606,321 @@`, with 0 lines removed.
12. Development pair on the same subject and session, checkable: proven.
    - All 321 rows carry `tree_dirty: false` and `commit_sha` `0f69b60d...`, with the same `roster_entry_id`, `fiche_hash` and `engine_build`.
    - Each batch's precondition log lists untracked paths only: 09:08:13 for the publication batch and 09:10:22 for the development batch. Provenance is resolved once at run start (`provenance.py:62`). So the pairing-test edit during the publication batch, made after its capture, does not falsify either batch.
    - The pairing test is parametrized per use case, with the commit in its key.
13. Export and recompute clean: proven (reviewer run above).
14. No averaging, development leads: proven (README table and text). The README's figures equal the rows. The 21-item interval equals that of `be0dda5e`, as claimed.

Other checks:
- `scripts/hub_source.py`: the refactor moves the code verbatim. minds14's public names stay importable, and `test_minds14_suite.py` is untouched and passes.
- Secrets: the baseline gains 305 entries and loses none, all of type `Hex High Entropy String`: 300 `content_hash` values, the table SHA-256 and the revision in the definition, plus the table hash and the two blob oids in `fetch-record.json`. The hook's exclude has been unchanged since `cc0692d`.
- The covering slice in the constrained-run test is sound. `labels` is a property derived from the items, and the slice is asserted to keep every language, target, label and shape.

Blocking findings:
1. `aidd_docs/results/machines/NOTICE.md:3-6` still licenses the per-machine rows under CC-BY 4.0, excepting only the model-output fields. `machines/laptop-mobile-gpu/quality.jsonl` now holds 300 WMT24++ rows (Apache-2.0), and no Apache text sits in `machines/`. LICENSE-DATA 1.1 already makes the exception. The fix:
   - State the drawn-item exception in that NOTICE, naming WMT24++/Apache-2.0 and the Apache text, or ship `LICENSE-APACHE-2.0.txt` there.
   - Add `aidd_docs/results/machines` to `WMT24PP_DIRECTORIES` in `tests/test_data_licence.py`, or assert the exception there.

Non-blocking findings:
1. `tests/test_reference_bundle.py` `test_a_published_wmt24pp_batch_ran_the_model_its_cap_was_counted_for` will fail on any later roster batch over this suite, such as the roster-ranking story (Q130). It enforces the story, but that story then needs a suite@2 or a multi-tokenizer basis.
2. `_DEVELOPMENT_SUITE` (`tests/test_reference_bundle.py:401`) ignores a publication suite under a third `task_suite`, with no error. Assert that every publication `task_suite` is a key.
3. `scripts/assemble_release_archive.py:515`: "the data is CC-BY 4.0" now also covers Apache-2.0 items in `quality_items.csv`. This is round-1 item 5 of the classification twin, still open.
4. `evidence/run-summary.md` says that the pairing-test edit was parked during the development batch, but not that it was made during the publication batch, after that batch captured its provenance. Add one line.

## Round 2 (2026-10-04, fixes for round-1 findings, uncommitted)

VERDICT: PASS

Gates run by the reviewer:
- `timeout 900 uv run pytest -q` => `3149 passed, 20 skipped, 2 warnings in 256.25s`, coverage 98.51%, exit 0. This run includes `test_the_legal_code_is_the_official_text_verbatim`, the CC-BY legal-code hash test.
- `uv run --isolated --locked --group release pytest tests/test_assemble_release_archive.py tests/test_release_parquet.py --no-cov` => `58 passed`, so the archive and parquet stay deterministic.
- ruff check and ruff format --check are clean.
- `merge-bundle --check` => "committed bundle equals the merge (6 runtime, 926 quality, 0 refusals)". The new file at the root of `machines/` does not disturb the merge.
- The bundle rows are unchanged since round 1.

Blocking 1 is resolved:
- `machines/NOTICE.md` now excepts drawn item fields from CC-BY 4.0. It names MInDS-14 (CC BY 4.0, attribution in section 2.1) and WMT24++ (Apache-2.0, with its text in that directory, the change stated, section 2.2).
- `machines/LICENSE-APACHE-2.0.txt` is byte-equal to the other three copies (SHA-256 `cfc7749b...3d30`).
- `LICENSE-DATA` section 2.2 and the results README list `machines/` among the directories holding drawn items. Section 1.1 already treats that file as licence text, not data.
- `test_data_licence.py` adds `machines` to `WMT24PP_DIRECTORIES` and adds `test_every_notice_over_drawn_rows_names_each_drawn_source`.

Wording is consistent across `LICENSE-DATA` 1.1, 2.1, 2.2 and 3, the four NOTICE files, the results README and the archive README. Each one sends drawn items to their source's licence under section 2, and only the change it names is made. The archive README's licence text (`assemble_release_archive.py:532-538`) is accurate: the archive ships `LICENSE-APACHE-2.0.txt` beside `aidd_docs/results/` and `suite-definitions/` through `bundle_files`.

The round-1 non-blocking findings are handled:
- 1: recorded as a plan follow-up.
- 2: `test_every_use_case_with_a_publication_suite_names_its_development_suite` closes it.
- 3: the archive README is fixed.
- 4: the run summary now states when the edit was made (by 09:08:50) and when the batches captured their provenance (09:08:16 and 09:10:22).

Blocking findings: none.

Non-blocking findings:
1. The archive README's licence paragraph does not repeat the model-output exception (`LICENSE-DATA` 1.3). This was the case before this story, and `LICENSE-DATA` itself states the exception.
