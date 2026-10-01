## Round 1

# Review: Every row names its prompt variant, and a baseline row carries the authored prompt

- **Verdict**: approve (VERDICT: PASS)
- **Diff**: `HEAD...working tree` (uncommitted, plus untracked `prompt_variants.py`, `test_prompt_variants.py`, task folder; `run-log.md` excluded)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_01
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — The variant registry, its load-time hash check, and the one application function

- [x] Registry with one entry `baseline` v1, identity, carrying id/version/definition/definition hash; only baseline required by this story (other three are orders 4, 5, 9) — `src/wave_local_ai_v2/prompt_variants.py:69-84`; `tests/test_prompt_variants.py::test_the_tracked_registry_holds_baseline_version_1_as_the_identity`
- [x] Edited definition at unchanged version refused at load, naming variant and version — `prompt_variants.py:109-116`; `test_an_edited_definition_at_an_unchanged_version_is_refused_naming_it`
- [x] `apply_variant(baseline, text)` returns text; unknown id/version raise naming it — `prompt_variants.py:127-155`; `test_baseline_returns_the_authored_prompt_unchanged`, `test_an_unregistered_variant_is_refused_naming_it`, `test_an_unregistered_version_is_refused_naming_it`

### Phase 2 — Row fields, gate rules and schema "14", applied on every writer path

- [x] Three fields required on both row kinds — `row_contract.py:147-152,249-254`; `test_a_row_missing_a_prompt_variant_field_is_refused_by_name` (3 fields x 2 kinds)
- [x] Gate refuses unregistered variant / version, naming the field — `row_contract.py:843-854`; `test_an_unregistered_prompt_variant_is_refused_naming_the_field`, `..._version_is_refused_naming_the_field`
- [x] Gate refuses `baseline` with transformed pre-template prompt; genuine baseline passes; authored text resolved from code, not the row — `row_contract.py:856-905`; `test_a_hand_built_baseline_row_with_a_transformed_prompt_is_refused`, `test_a_baseline_runtime_row_with_a_transformed_fixed_prompt_is_refused`, `test_a_genuine_baseline_row_of_each_kind_passes`; evidence `evidence/baseline-gate-refusal.txt`
- [x] Variant applied before templating, local + both clouds + runtime fixed prompt + probe; judges keep authored text — `quality_cli.py:413-420`, `judge_probe.py:792-797,933-934`, `__init__.py:258-262`; `test_the_variant_runs_before_templating_on_the_local_and_cloud_paths`, `test_the_fixed_prompt_passes_through_the_declared_variant`, `test_the_probe_subject_is_sent_the_variant_and_the_judges_the_authored_text`
- [x] `prompt` stays the string the engine received, so a non-baseline variant is visible in it — `quality_cli.py:1082`; asserted in `test_the_variant_runs_before_templating_on_the_local_and_cloud_paths` (local = rendered marked, cloud = marked)
- [x] Cloud quality rows carry the fields as `baseline` — `test_every_row_names_the_baseline_variant_and_its_authored_prompt` (local, mistral, google), probe equivalent in `test_judge_probe.py`
- [x] `SCHEMA_VERSION` "14" with history comment; older rows not back-filled — `row_contract.py:93-101`; gate runs only in `results.append_row` (`results.py:90`), read path untouched; `wave-local-ai-v2-validate` on all four `aidd_docs/results/*.jsonl` exits clean (80/40/2/3 rows checked)
- [x] Fields placed in read_model NOT_RENDERED — `read_model.py:267-273,342-348`
- [x] `uv run pytest -q`: `1105 passed, 2 warnings in 34.55s`, coverage 96.01%; ruff check, ruff format --check, mypy all clean

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 | code | 2 | `src/wave_local_ai_v2/row_contract.py:850` | Unhashable `prompt_variant_version` (e.g. a list) on a registered id raises `TypeError`, not `RowContractError` naming the field | Check `isinstance(version, str)` before the membership test |
| 🟢 | conform | 2 | `src/wave_local_ai_v2/row_contract.py:883` | Shared contract module now reaches into a CLI writer (`judge_probe`) for item text (function-local, so no import cycle) | Later: move `JUDGE_PROBE_ITEMS`/`SUITE_*` into a pure suite module like the other two |
| 🟢 | fit | 2 | `src/wave_local_ai_v2/row_contract.py:856` | Non-baseline rows are not checked that `prompt_before_template == apply_variant(variant, authored)`; not required here, but the variant stories (orders 4, 5, 9) will want it | Consider generalising the authored-text check to all variants in the first non-identity story |
| 🟢 | rot | 2 | `CHANGELOG.md` | Entry added for schema "14"; schema "13" (previous story) still has none | Add the missing "13" entry |
| 🟢 | fit | 2 | `tests/` | "Never back-filled" for rows below "14" is proved structurally (no default anywhere, `read_model.resolve_field` returns `Absent`) but no test pins a pre-14 row reading without `prompt_variant_id` | Optional: one read-model test over a schema-13 row |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (12/12)                                      |
| Files checked | prompt_variants.py, row_contract.py, __init__.py, quality_cli.py, judge_probe.py, read_model.py, CHANGELOG.md, codebase-map.md, tests/conftest.py, store_fixtures.py, test_prompt_variants.py, test_row_contract.py, test_results.py, test_judge.py, test_cli.py, test_quality_cli.py, test_judge_probe.py |
| Unchecked     | none                                              |
| Unplanned     | none (`verdict.py` untouched: story acceptance does not make the variant a comparability field) |
