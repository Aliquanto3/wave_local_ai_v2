# Review: A suite is certified to its declared level, and every item names its licence and source

## Round 1

VERDICT: PASS

### Gates

- `uv run pytest -q`: `1288 passed, 2 warnings in 41.01s`, coverage 96.85% (floor 95%).
- `ruff check .` (All checks passed), `ruff format --check .` (519 files already formatted), `mypy src/ scripts/` (no issues in 50 files).
- detect-secrets over every changed and untracked file, with the hook's own `--exclude-files fiches.[0-9a-f]{64}[.]json$|suite-definitions.[a-z0-9@-]+[.]json$`: exit 0. That exclusion is in `.pre-commit-config.yaml:52`, and `[a-z0-9@-]+` matches the new `@4`/`@3` filenames.
- `uv run wave-local-ai-v2-validate` over the four committed stores (`quality-reference.jsonl`, `runtime-reference.jsonl` and both `.schema-1.jsonl` files): `checked 125 row(s)`, `legacy (pre-fiche-hash, not fatal): 43`, exit 0. Old rows still pass because `row_contract.validate_row` runs only on the write path (`results.append_row`, `results.py:90`), so a schema-"7" row is never checked against the "15" required set. `tests/test_reference_bundle.py` passes too.

### Acceptance, condition by condition

1. Level declared, development unchanged: `level` is a required core key (`suite_registry.py` `_CORE_KEYS`). The development constants are untouched (`suite_gate.py:30-33`). Proved by `test_a_definition_without_a_level_is_refused` and by the existing development tests, which still pass.
2. Publication rules (100 floor, 25% share, licence/source/revision on every item, declared 100/300 target with a reason, count checked against the target): `suite_gate._publication_shortfalls`. Proved by `test_ninety_nine_items_at_publication_fails_naming_the_count`, `test_a_language_below_its_share_at_publication_fails_naming_the_language` (38/38/24), `test_an_item_without_a_licence_or_a_source_fails_naming_the_item`, `test_a_declared_300_target_holding_250_fails_naming_the_target`, `test_a_publication_suite_without_a_valid_target_fails` and `test_a_publication_suite_without_a_target_reason_fails`.
3. `gate_suite` returns the certified level and never passes quietly at development: `SuiteGateResult.level`; a shortfall raises `SuiteGateError` with the prefix "suite declares level 'publication' and falls short of it". The acceptance asks the suite to "fail to that level naming the count" and to never "pass quietly at development instead". A raise at load meets both, and the story's "fails loudly" so-that clause supports it. An `indicative` flag would be the quiet pass the story forbids. Proved by `test_a_short_publication_suite_never_passes_at_development_instead` and `test_a_publication_definition_that_falls_short_is_never_registered`.
4. Every quality row names its level, and both shipped suites keep today's verdict: `quality_rows.suite_item_fields` is used by both writers (`quality_cli.py:1000`, `judge_probe.py:770`). Proved by `test_real_classification_suite_is_not_indicative_at_the_suite_level`, `test_real_translation_suite_certifies_at_development_unchanged`, `test_a_shipped_suite_run_names_development_and_each_items_licence` and `test_a_publication_suite_runs_and_every_row_names_its_level_and_source`.
5. The licence sits on the item, and neither the text nor the hash moves: the suite_data diff is limited to `suite_version`, `level` and the per-item `licence` (checked by inspecting the diff). Comparing `@3`/`@4` and `@2`/`@3` shows the same `prompt_set_hash`, with `licence` the only differing item key. Proved by `test_every_hand_written_item_names_its_licence_at_the_development_level`.
6. `contamination_risk` is unchanged and nothing verifies licence or source truth. `aidd_docs/results/README.md` says so in its new "Suite levels" section.
7. The four fields are declared unrendered in `read_model.QUALITY_FIELDS_NOT_RENDERED`, and the export dictionary gains entries for them.
- Evidence: `evidence/snapshot-export.txt` shows the new files written, the hashes equal and an overwrite refused (exit 1). `suite_snapshot.main` now enforces write-once.

### Version bump vs comparability (asked point)

The bump is forced. The story's evidence requires a snapshot "carrying its level and item licences" and adds that "an already-published snapshot file is never overwritten". Snapshots are addressed by `<suite_id>@<suite_version>`, and the existing test `test_every_committed_definition_equals_its_export_byte_for_byte` makes adding `level` under an unchanged version an overwrite. Neither the story nor the epic asks to keep rows comparable across a version bump. Epic lines 86 and 110 make a different `suite_version`, and a different level, a refusal by design. Commit f34e5b8 set the same precedent. The bump also breaks nothing published: committed rows cite only `classification-support-routing@1` (task evidence) and `@2` (80 reference rows, schema "7"). No committed row cites `classification@3` or `translation@2`, so the reference rows were already `not_comparable` to the current suite before this change.

### Blocking findings

None.

### Non-blocking findings

1. `aidd_docs/results/README.md` (new "Suite levels" section): "not_comparable to the published @3 / @2 rows" and "stay beside them for the rows that cite them" describe rows that do not exist. No committed row cites `classification@3` or `translation@2`. Fix the wording.
2. `evidence/snapshot-export.txt`: "git diff --stat -- aidd_docs/results/ (empty = unchanged)" is stale, because `aidd_docs/results/README.md` is modified. Narrow the claim to `suite-definitions/`.
3. `suite_snapshot._published_text` docstring says "with its newlines folded", but no code folds them; only text-mode universal newlines does. Say that, or drop the phrase.
4. `bundle_export` FieldDoc for `suite_level` and `item_licence`: there is no null/absence note for rows below schema "15", which do not carry these fields, unlike `item_source`.
5. `plan.md` decision: the level and licence live in `suite_data/*.json`, not in the `*_suite.py` modules the story's "Code it changes" lists. This is file-location drift only and is justified by the dependency story.
