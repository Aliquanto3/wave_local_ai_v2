# Review: Each model, machine and mode runs under its own named profile

- **Verdict**: approve (VERDICT: PASS)
- **Diff**: `c68b23e...working tree` (uncommitted, row schema "26", untracked `profiles.py`, `profiles.json`, `tests/test_profiles.py`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 1 warning, 5 minor

## Phases

### Phase 1 — Profile registry, loader and resolver with its refusal

- [x] Registry keyed by (entry, machine, mode), per-(machine, mode) defaults, per-entry overrides only where needed — `aidd_docs/roster/profiles.json:3-38`, `src/wave_local_ai_v2/profiles.py:102`, `:261`; tests `test_an_entry_with_no_override_uses_the_machine_mode_default`, `test_the_shipped_registry_declares_the_three_machines_profile_set` (only the flagship overrides: epic's "per-entry everywhere" did not occur, recorded in plan Decisions)
- [x] Declared set: laptop and tower `gpu` + `cpu_only`, pro PC `cpu_only` only — `profiles.json:4,13,22`; `test_the_shipped_registry_declares_the_three_machines_profile_set`. Tower / pro-PC values `not_yet_declared` (D1): legitimately pending machine-readiness, runs there refuse unless overridden (`test_the_shipped_laptop_profiles_resolve_and_the_others_await_a_read`)
- [x] Missing triple refuses before any server starts, naming triple and existing profiles — `profiles.py:281`; `test_a_missing_triple_is_refused_naming_it_and_the_declared_profiles`; resolver called before build probe / spawn in all three writers (`__init__.py:245`, `quality_cli.py:278`, `judge_probe.py:473`), `ProfileError` is a `RosterError` caught by each writer's handler
- [x] Resolution order entry default -> profile -> operator, tested in order — `profiles.py:261-330`; `test_entry_default_then_profile_then_operator`

### Phase 2 — validated_host moved into profiles; build_flags and host-fit on the resolved profile

- [x] `validated_host` gone from roster entries and `REQUIRED_FIELDS`; `roster_version` 5 — `models.json`, `roster.py:39-64`; `tests/test_roster.py:112,354,443`
- [x] `server.build_flags` sole flag builder, profile required, no laptop fallback (`DEFAULT_HOST_*` removed, overrides unset = `None`) — `server.py:53-87`, `settings.py:164-174,407-435`; every production caller passes a resolved profile (grep: `__init__.py:281`, `quality_cli.py:332`, `judge_probe.py:488`, `candidate_gate.py:582`)
- [x] `-ngl` from profile, roster keeps model-intrinsic default; `cpu_only` never emits `--n-cpu-moe` — `test_cpu_only_puts_every_layer_on_the_cpu_and_emits_no_moe_offload`, `test_cpu_only_profile_overrides_the_roster_ngl`
- [x] Laptop vs tower `gpu` flagship profiles give different `-t` / `--n-cpu-moe` — `test_the_laptop_and_tower_gpu_profiles_launch_different_host_values` (constructed tower values, per D1)
- [x] Byte-identical launch held; D4 edit confined: `git diff tests/test_launch_byte_identical.py` touches no line of `BASELINE_FLAGS` nor any expected flag string, only the value source (resolved flagship/laptop/gpu profile) — both tests green

### Phase 3 — Profile id and override record on fiche and rows across the three writers

- [x] `profile_id` on fiche, outside every projection — `hardware.py:38-41`, `FICHE_PROJECTIONS` unchanged; `test_renaming_a_profile_does_not_move_the_fiche_hash` asserts equal `fiche_hash`
- [x] `profile_id` + `profile_overrides` on every row, schema "26", cloud rows `not_applicable`, rows < "26" not back-filled — `row_contract.py:221-231,319-322`, `_validate_profile`; `test_every_row_and_fiche_names_its_run_profile` (runtime), quality and judge-probe row tests, `test_a_row_below_the_profile_schema_validates_without_them`, `test_a_cloud_row_states_no_profile_applies`
- [x] Overrides applied last and recorded on the row — `test_an_overridden_run_names_the_values_it_overrode`, `test_an_overridden_quality_run_names_its_override`, `test_an_undeclared_value_refuses_unless_the_operator_overrides_it`

### Phase 4 — Docs, CHANGELOG, one laptop run per mode

- [x] Resolution order and declared-profile table in `docs/setup.md` §4 (`docs/setup.md:392-442`), `.env.example`, `CHANGELOG.md`, memory `cli.md` / `architecture.md`
- [x] One laptop run per mode plus an override run, rows schema "26" naming their profile — `evidence/evidence.md`, `profile-fields.txt`, `validate.log` (`checked 3 row(s)`, exit 0); `cpu_only` fiche `d8524577...` and `gpu` fiche `73ec536e...` equal story 1's stored identities

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | rot | 2 | `aidd_docs/backlog/tech-debt.md:112,115` | Two open rows describe `validated_host` / `DEFAULT` wiring this diff removes; left `open`, now stale | Mark both resolved by this story in the same commit |
| 🟢 minor | rot | 2 | `src/wave_local_ai_v2/candidate_gate.py:321` | `gate_profile` hand-builds a `ResolvedProfile` and re-implements the operator-override step outside `profiles.resolve` (scope-justified: gate runs on no declared machine) | Either resolve via `profiles.resolve` over an in-memory one-machine registry, or keep and name it the sole sanctioned exception in `profiles.py` docstring |
| 🟢 minor | rot | 4 | `docs/setup.md:403` | "One resolution order, applied by `server.build_flags`": the order is applied by `profiles.resolve`; `build_flags` consumes the result | Reword to "applied by `profiles.resolve`, consumed by `server.build_flags`, the only flag builder" |
| 🟢 minor | fit | 3 | `src/wave_local_ai_v2/comparison.py:323,352` | `profile_id` added to the model axis and `profile_overrides` to `ENGINE_FIELDS` with no `test_comparison` case | Add a local-vs-cloud schema-"26" pair test showing neither field is reported as a confound |
| 🟢 minor | fit | 1 | `src/wave_local_ai_v2/settings.py:599` | The only undeclared shipped triple (pro PC `gpu`) is refused earlier by `require_run_profile`, which names machine and mode but not the entry's profiles; the profile refusal is reached only via constructed registries | Acceptable (stronger earlier refusal); no change required |
| 🟢 minor | conform | 2 | `.secrets.baseline:140-180` | Line-number drift from the `models.json` edit is unstaged; detect-secrets hook rewrites the baseline and fails a commit that stages `models.json` without it | Commit `.secrets.baseline` together with `models.json` (hashes unchanged, only line numbers + `generated_at`) |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (17/17) |
| Files checked | profiles.py, profiles.json, models.json, roster.py, server.py, settings.py, hardware.py, row_contract.py, __init__.py, quality_cli.py, judge_probe.py, quality_rows.py, comparison.py, read_model.py, bundle_export.py, candidate_gate.py, docs/setup.md, .env.example, CHANGELOG.md, results/README.md, .secrets.baseline, memory cli.md/architecture.md, tests (profiles, server, launch_byte_identical, hardware, cli, quality_cli, judge_probe, row_contract, roster, settings, candidate_gate) |
| Unchecked     | none (tower / pro-PC fitted values: pending machine-readiness per D1, not-applicable here) |
| Unplanned     | candidate gate `RECORD_VERSION` 1 -> 2 and `load_profile` (justified: the passed entry block can no longer carry `validated_host`, and the gate's one load needs an explicit profile; `candidate-records.jsonl` untouched); `aidd_docs/results/README.md` composition block `roster_version 5` (required by the composition-check test); committed `*.jsonl` stores untouched |

Gates: `uv run pytest -q` => `2371 passed, 2 warnings in 153.40s` (coverage 98.27%); `ruff check` all passed; `ruff format --check` 679 files formatted; `mypy src/ scripts/` no issues.
