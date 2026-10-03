# Review: A GPU run and a CPU-only run never share a fiche

- **Verdict**: approve (VERDICT: PASS)
- **Diff**: `fb8659f...working tree` (uncommitted, 30 modified + 4 untracked paths)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — Machine registry, its loader, and the two required run inputs

- [x] Shipped registry loads with the three PRD machines, every fact `{value, source, read_from}` — `aidd_docs/roster/machines.json`; `tests/test_machines.py::test_the_shipped_registry_declares_the_three_prd_machines`, `::test_every_shipped_fact_is_marked_and_an_unread_one_carries_no_value`
- [x] Entry missing a fact refuses naming entry and fact — `machines.py` `_parse_entry`; `test_machines.py::test_an_entry_missing_a_fact_refuses_naming_it`
- [x] Missing/undeclared machine names declared ids; missing mode names `gpu` and `cpu_only`; `gpu` on GPU-less machine names it — `settings.py` `require_run_profile`; `test_settings.py::test_a_missing_or_undeclared_machine_refuses_naming_the_declared_ids`, `::test_a_missing_or_unknown_mode_refuses_naming_both_modes`, `::test_a_gpu_run_on_a_gpu_less_machine_refuses_naming_it`

### Phase 2 — Fiche fields, projection "3", `cpu_only` launch and host-fit mode check

- [x] `gpu` / `cpu_only` hash differently, both stored with own flags; machine ids separate; committed fiches verify under citing row's version — `hardware.py` projection "3"; `row_contract.py` `fiche_projection_for`; `test_hardware.py::test_a_gpu_and_a_cpu_only_fiche_of_one_machine_hash_differently`, `::test_two_machine_ids_with_identical_captured_fields_hash_differently`; `test_fiche_registry.py::test_a_gpu_and_a_cpu_only_fiche_are_both_stored_each_with_its_own_flags`, `::test_each_projection_verifies_under_its_citing_rows_schema_version` (schema-23 row citing a fiche without `machine_id` => `edited`)
- [x] `cpu_only` emits `-ngl 0 --device none`, no `--n-cpu-moe`; supplied value refused naming mode; flagship `gpu` launch byte-identical — `server.py` `build_flags`, `roster.py` `validate_host_fit`; `test_server.py::test_cpu_only_puts_every_layer_on_the_cpu_and_emits_no_moe_offload`, `::test_cpu_only_refuses_a_supplied_n_cpu_moe_naming_the_mode`; `test_roster.py::test_validate_host_fit_refuses_any_n_cpu_moe_under_cpu_only_naming_the_mode`; `tests/test_launch_byte_identical.py` and `tests/test_reference_bundle.py` absent from `git status` (unedited) and green

### Phase 3 — Row fields and writer gate, verdict blocking, declared-absent GPU

- [x] Schema-23 row missing either field or naming undeclared machine refused; schema-22 row not held — `row_contract.py` `_validate_machine`; `test_row_contract.py::test_a_row_missing_the_machine_or_the_mode_is_refused_naming_it`, `::test_an_undeclared_machine_is_refused_through_the_gate_naming_the_declared`, `::test_a_row_below_the_machine_schema_validates_without_both_fields`; cloud row `not_applicable` — `::test_a_cloud_row_never_carries_a_machine_or_a_mode`
- [x] Each CLI refuses a missing input before any server starts; rows and fiche carry machine and mode — `require_run_profile` called right after `load_settings` in `__init__._run`, `quality_cli._run`, `judge_probe._run` (before roster, preflight, build probe, fiche, spawn); `test_cli.py::test_a_run_without_a_valid_run_profile_refuses_before_any_server_starts`, `test_quality_cli.py::test_a_batch_without_a_machine_refuses_before_any_server_starts`, `test_judge_probe.py::test_a_missing_judge_refuses_the_run_before_anything_is_generated[machine_id/compute_mode]`; service routes launch nothing (read-only)
- [x] Mode mismatch => `not_comparable` naming `compute_mode`; two `cpu_only` runs on declared GPU-less machine reproduce; failed GPU capture never matches — `verdict.py` `_RUNTIME_BLOCKING_FIELDS`, `runtime_blocking_fields`; `test_verdict.py::test_a_mode_mismatch_alone_is_not_comparable_naming_compute_mode`, `::test_two_cpu_only_runs_on_a_declared_gpu_less_machine_can_reproduce`, `::test_a_gpu_that_failed_capture_on_a_gpu_declaring_machine_never_matches`, `::test_an_undeclared_machine_never_declares_its_gpu_absent`; `machine_id` not blocking (M8)

### Phase 4 — Live proof, docs, CHANGELOG, PRD alignment

- [x] Two hashes, two stored fiches with own flags, second row `not_comparable` naming `compute_mode` — `evidence/evidence.md`; reviewer re-hashed both `evidence/fiches/*.json` under projection "3" (`73ec536e...`, `d8524577...` match names); `evidence/runtime.jsonl` row 2 verdict `differing_fields: ["compute_mode", "flags"]`; validator `checked 2 row(s)` exit 0
- [x] Operator learns both inputs are required and their values — `.env.example`, `docs/setup.md` §4; PRD alignment (M14, M8 divergence) recorded in `aidd_docs/memory/architecture.md` and plan Decisions

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | 2 | `src/wave_local_ai_v2/candidate_gate.py:528` | Candidate gate still spawns llama-server with `compute_mode=None` (gpu flags) and no `MACHINE_ID` check; writes no row, so outside the acceptance, but on the no-GPU machine it would launch `-ngl 99` | Track for the epic story that brings the pro PC online |
| 🟢 minor | conform | 1 | `aidd_docs/roster/machines.json` (laptop `vram_allocatable_gb`) | Marked `declared` but sourced from `context_input/hardware.md` operator note, "not re-measured" | Re-measure on the laptop or mark `not_yet_declared` until order 0 |
| 🟢 minor | code | 3 | `src/wave_local_ai_v2/verdict.py` `runtime_blocking_fields` | `declares_no_gpu` reads the registry at verdict time, not as of the fiche; an in-place edit of `gpu_present` would change old verdicts | Rely on the "configuration change = new id" rule; consider a registry test guarding in-place edits |
| 🟢 minor | fit | 4 | `evidence/evidence.md` §4 | `cpu_only` row publishes `vram_used_mib` 254.7 (CUDA context) | Owned by the epic's success check 3 story, as recorded |
| 🟢 minor | rot | - | story file, "Blocks every other story" paragraph | Premise "`-ngl 99` and `-ngl 0` hash identically" is stale since projection "2": `engine_config_hash` already separates them (reviewer: projection-2 hashes `3b11dad5...` vs `ae604236...`); `compute_mode` remains needed for a declared identity | None for this diff; note when the story is closed |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (10/10) |
| Files checked | settings.py, machines.py, hardware.py, row_contract.py, verdict.py, server.py, roster.py, __init__.py, quality_cli.py, judge_probe.py, quality_rows.py, comparison.py, bundle_export.py, read_model.py, fiche_registry.py, machines.json, evidence/*, tests diffs |
| Unchecked     | none; live tower / pro-PC facts legitimately pending (D1, operator on another machine) |
| Unplanned     | none (comparison `ENGINE_FIELDS` and read-model partition are planned Decisions) |

Gates: `uv run pytest -q` => `2186 passed, 2 warnings in 149.42s`, coverage 98.15%; `tests/test_quality_cli.py` alone under `timeout 400` => `125 passed in 102.30s` (no hang; slowest test 14.85s, pre-existing); also green with `MACHINE_ID=pro-pc-no-gpu COMPUTE_MODE=cpu_only` exported. `ruff check` / `ruff format --check` / `mypy src/ scripts/` clean. `git status --ignored aidd_docs/` shows nothing under `aidd_docs/results/`.
