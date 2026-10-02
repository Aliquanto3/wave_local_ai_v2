# Review: Every PRD use case carries a coverage state, or the record refuses to publish

- **Verdict**: approve
- **Diff**: `HEAD...working tree` (uncommitted, branch `feat/ready-stories-unattended`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_02
- **Findings**: 0 critical, 0 warning, 3 minor

## Phases

### Phase 1 — The coverage record as data and the gate over it

- [x] Record is data, ten entries, each exactly one of three states; `exercised` takes a list — `src/wave_local_ai_v2/use_case_coverage.json`, `use_case_coverage.py:47-64,95-114`; tests `test_a_complete_record_passes_in_prd_order`, `test_an_entry_mixing_both_states_fields_refuses`
- [x] Multilingual is `covered-by-dimension` naming classification, translation, rewriting suites; nothing built — `use_case_coverage.json:44-50`; `test_the_multilingual_entry_is_a_dimension_of_three_suites`
- [x] Refusal on missing / no state / unresolvable suite id / out-of-scope without reason, naming every failing entry — `use_case_coverage.py:79-144`; `test_removing_any_entry_refuses_naming_that_use_case`, `test_a_blank_state_refuses_naming_the_entry`, `test_an_unregistered_suite_refuses_naming_the_entry_and_the_suite`, `test_a_suite_the_gate_refuses_does_not_resolve`, `test_an_out_of_scope_entry_without_a_reason_refuses`, `test_three_failing_entries_are_all_named`
- [x] State declared, never inferred — required list in code (`use_case_coverage.py:47`), not in the record; `test_registering_a_suite_never_makes_a_use_case_exercised`
- [x] Removing any one entry from a complete fixture refuses naming it (all ten, parametrized) — `tests/test_use_case_coverage.py:126-130`

### Phase 2 — The publish command, its refusal evidence, and the docs

- [x] Command writes nothing on refusal, publishes to `aidd_docs/results/use-case-coverage.json` (`settings.py` `DEFAULT_USE_CASE_COVERAGE_PATH`) only when all resolve — `use_case_coverage.py:189-207`; `test_the_command_refuses_and_writes_nothing`, `test_the_command_publishes_a_complete_record`
- [x] Run today, refuses naming the six unbuilt, rewriting and multilingual — `test_run_today_the_command_refuses_naming_what_is_not_yet_covered`; reproduced by reviewer (exit 1, 8 entries, no file written); `evidence/coverage-refusal.txt` matches
- [x] `aidd_docs/results/README.md` explains the record and its absence — README section "The use-case coverage record, and why it is not here yet"

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 | fit | 1 | `use_case_coverage.json:20,48` | `rewriting-business-email` is invented; no backlog, epic, PRD, product or frontend artifact names the rewriting suite id (searched), so no conflict. The rewriting story (quality epic, order 5) does not mention the coverage record. | When that story is next refined, add one line: register under this id or edit the record. The gate keeps refusing until it matches, so drift cannot pass silently. |
| 🟢 | code | 2 | `use_case_coverage.py:153` | `gate_record` copies each entry whole, so any stray key in the record (e.g. a `note`) is published unchecked. | Optionally publish only `use_case`, `state`, `suite_ids`/`reason`, or refuse unknown keys. |
| 🟢 | fit | 2 | `tests/test_use_case_coverage.py:126-130` | The all-ten removal check runs through `gate_record`; the command path (`main`) is exercised with one removal only (`:310`). Equivalent since `main` only wraps the gate. | None required. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (8/8)                                        |
| Files checked | use_case_coverage.py, use_case_coverage.json, settings.py, tests/test_use_case_coverage.py, results/README.md, memory/cli.md, memory/codebase-map.md, evidence/coverage-refusal.txt |
| Unchecked     | none                                              |
| Unplanned     | none (memory doc updates trace to the new module and command) |

Gates run by reviewer: `uv run pytest -q` => `1240 passed, 2 warnings in 37.61s`, coverage 96.76% (floor 95%); `ruff check` => all checks passed; `ruff format --check` => 515 files already formatted; `mypy src/ scripts/` => no issues in 50 source files.

Specific points: (1) record at `src/wave_local_ai_v2/use_case_coverage.json` sits beside `suite_registry.py` (story "beside the suite registry"), publishes into `aidd_docs/results/` (acceptance, epic Boundaries) => conforms. (2) No existing rewriting suite id anywhere => invented id not blocking. (3) Six `"state": null` entries: acceptance requires one entry per use case and refusal on "an entry has no state"; the "Run today" bullet names them "entries still without a resolvable state"; Q30 (a) is strict refusal with no fourth state, and null is refused, not a state => shape allowed.
