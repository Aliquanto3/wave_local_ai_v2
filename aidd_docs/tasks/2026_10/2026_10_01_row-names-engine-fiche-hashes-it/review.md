# Review: Every row names the engine that produced it, and the fiche hashes it

- **Verdict**: approve
- **Diff**: `8f8a27a...working-tree` (uncommitted, parked `c0fdfef` re-applied and conflicts resolved)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_02
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — Engine registry and its loader

- [x] One tracked entry `llama.cpp`, `reference: true`, build probe, endpoints (chat, health, prompt rendering, template source), lifecycle `spawned`, default port, defaults each `declared` / `engine_reported` — `aidd_docs/roster/engines.json`, `engines.py:61-76`, `test_engines.py::test_the_shipped_registry_holds_llama_cpp_as_its_one_reference_engine`, `::test_every_shipped_default_is_marked_declared_or_engine_reported`
- [x] Missing field refused by name; default lacking its mark refused — `engines.py:167-180,256-283`, `test_engines.py::test_an_entry_missing_a_top_level_field_is_refused_naming_it`, `::test_an_entry_missing_a_nested_field_is_refused_naming_its_path`, `::test_a_default_missing_its_mark_or_value_is_refused`

### Phase 2 — Fiche generalised, two projection versions, verdict blocking fields

- [x] Fiche carries `engine_id`, `engine_build`, path-free `engine_config_hash` inside projection "2"; raw `flags` outside (Q20 a) — `hardware.py:57-90`, `engines.py:330-374`, `test_hardware.py::test_each_engine_field_changes_the_hash`, `test_engines.py::test_the_config_hash_is_identical_for_two_model_directories`, `::test_the_config_hash_ignores_host_and_port_but_not_a_flag`; key order: `test_hardware.py::test_hash_is_independent_of_dict_key_insertion_order`
- [x] Projection chosen by citing row's `schema_version`, never by an absent field; `verify_fiche` requires it; committed bundle verifies under "1" — `row_contract.py:260-271`, `fiche_registry.py:62-91`, `test_fiche_validator.py::test_a_legacy_fiche_verifies_under_the_projection_its_row_selects`, `test_reference_bundle.py` green
- [x] `engine_id` / `engine_build` replace `llama_cpp_build` among blocking fields; engine mismatch is `not_comparable` naming `engine_id` — `verdict.py:35`, `test_verdict.py::test_an_engine_mismatch_is_not_comparable_naming_engine_id`

### Phase 3 — Launch, build probe and thinking switch read from the entry

- [x] Host, port, health path from the entry; port guard unchanged for `spawned`; attached never spawned — `server.py:150-183`, `test_server.py::test_host_port_and_health_path_are_read_from_the_engine_entry`, `::test_an_attached_engine_is_never_spawned`, occupied-port test kept
- [x] Switch spelling read from the entry; verified render difference recorded; no-op switch refuses the batch (story 5 tests unchanged) — `local_client.py:170-194`, `quality_cli.py:808-819,866-875`, `test_quality_cli.py::test_the_verified_thinking_switch_is_recorded`, `::test_a_control_the_template_ignores_refuses_the_batch_and_writes_no_row`
- [x] Switchless engine declares `none`, checked by the candidate gate; a roster `none` entry still runs `disabled` on it (story 5 not regressed); parked `effective_thinking_policy` downgrade gone (no hit in src/tests/docs) — `local_client.py:156-160`, `candidate_gate.py:580-584`, `test_local_client.py::test_an_engine_with_no_switch_runs_an_entry_that_does_not_reason`, `::test_an_engine_with_no_switch_refuses_an_object_control_under_disabled`, `test_candidate_gate.py::test_a_none_declaration_still_passes_on_an_engine_declaring_no_switch`
- [x] MoE launch byte-identical — `tests/test_launch_byte_identical.py` unedited (`git diff --quiet`) and green

### Phase 4 — Row fields, writer gate, schema 22, writers, resume, comparison, read model, export, docs

- [x] Every runtime row and local quality row carries both fields; gate refuses missing or unregistered (naming the id); cloud row states `not_applicable`, never `llama.cpp` — `row_contract.py:1164-1201`, `test_row_contract.py::test_an_unregistered_engine_is_refused_through_the_gate_naming_it`, `::test_a_local_row_missing_an_engine_field_is_refused_naming_it`, `::test_a_cloud_row_never_carries_an_engine`
- [x] Schema "22" with history comment; rows below "22" not held to it — `row_contract.py:183-195,697-698`, `::test_a_row_below_the_engine_schema_validates_without_the_engine_fields`
- [x] Resume check includes engine fields (both CLIs), before spawn — `quality_cli.py:309-319`, `judge_probe.py:469-473`, `test_judge_probe.py::test_a_probe_resume_over_rows_of_another_configuration_is_refused`, `test_quality_cli.py::test_a_resume_over_rows_of_another_configuration_is_refused_writing_nothing`
- [x] Comparison `model` axis: engine fields on-axis only local vs cloud, confound between two local sides (sound: `fiche_hash` already on-axis, epic makes the engine its own dimension) — `comparison.py:840-857`, `test_comparison.py::test_two_local_models_on_another_engine_or_build_are_confounded`

### Phase 5 — Live evidence on `qwen3-0.6b-q8`

- [x] Runtime row with `engine_id`, live `engine_build` b10537, config hash, new `fiche_hash`; gate refusal of `ollama` — `evidence/evidence.md`, `evidence/gate-refusal.log`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | rot | 4 | `CHANGELOG.md` (engine entry, "The comparison's `model` dimension holds both fields: ...") | Parked-patch leftover: says the model dimension holds both fields, then calls a different engine a confound; contradicts `comparison._axis` (on-axis only local vs cloud) | Reword to the `cli.md` sentence: on-axis only between a local and a cloud side, a confound between two local sides |
| 🟢 minor | rot | 4 | `row_contract.py:187-188` | Comment lists "a judge-probe row" among rows that state `not_applicable`; a local-subject judge-probe row carries `llama.cpp` (`judge_probe.py:932-936`, correct per acceptance intent) | Say "a cloud subject's row (quality or judge-probe)" |
| 🟢 minor | code | 4 | `CHANGELOG.md` same entry | One over-long unwrapped line ("difference still refuses ... carries") | Re-wrap |
| 🟢 minor | functional | 4 | `tests/test_quality_cli.py:2732-2746` | Quality CLI resume test covers the engine only on the cloud half; no quality-CLI test of a local batch resumed under another `engine_build` (judge probe has it) | Add a local-half `engine_build` case if a local resume path exists |
| 🟢 minor | conform | 2 | `tests/test_reference_bundle.py:71-77` | Edited (one call site) because `verify_fiche` now requires `schema_version`; acceptance only demands no bundle file edited and the launch test unedited, assertions unchanged in strength | None required; note for the owner |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (8/8 acceptance bullets) |
| Files checked | engines.py, engines.json, hardware.py, fiche_registry.py, fiche_validator.py, verdict.py, row_contract.py, server.py, local_client.py, candidate_gate.py, quality_cli.py, judge_probe.py, quality_rows.py, __init__.py, comparison.py, read_model.py, bundle_export.py, docs, tests |
| Unchecked     | none |
| Unplanned     | none (read model / bundle export field docs trace to plan phase 4) |
| Gates         | `uv run pytest -q`: 2096 passed, 2 warnings in 148.40s, coverage 98.10%; ruff check/format clean; mypy: no issues in 61 source files |
