# Review: A campaign is declared as data, and an empty cell fails it

## Round 1

- **Verdict**: approve (VERDICT: PASS)
- **Diff**: `085190b...working tree` (uncommitted, schema "24"; base HEAD `ce03c23`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — Campaign declaration loader and completeness command

- [x] Three engines refused naming them — `campaigns.py:246`, `test_campaigns.py::test_three_engines_are_refused_naming_them` (the cap is checked before the registry, so unregistered ids still hit the cap)
- [x] Five variants refused naming them — `campaigns.py:258`, `test_five_variants_are_refused_naming_them`
- [x] Each unregistered id (engine, variant id, variant version, roster entry, suite, machine, mode, gpu on a GPU-less machine) refused naming it — `campaigns.py:255-280,364-386`, `test_an_id_absent_from_its_registry_is_refused_naming_it`
- [x] Incomplete engine entry refuses the load (order 1's rule via `engines.load_registry`) — `campaigns.py:251-254`, `test_an_incomplete_engine_entry_refuses_the_declaration`
- [x] Full matrix exits 0 listing run ids — `campaigns.py:553-590,615-654`, `test_the_command_passes_a_full_matrix`
- [x] One empty cell exits 1 naming it — `test_the_command_fails_naming_each_empty_cell`; reproduced by hand on scratch data (rc=1, `error: campaign 'c1': empty cell engine=llama.cpp ...`)
- [x] Dropped/refused cell listed with its reason, not a failure — `test_dropped_and_refused_cells_are_listed_with_their_reason`, `test_a_dropped_cell_with_its_reason_passes_the_command`; reproduced by hand (refused cell, rc=0)
- [x] Re-run returns the same listing (row order reversed too) — `test_re_running_the_command_returns_the_same_listing`

### Phase 2 — `campaign_id` on every row and the pre-launch run check

- [x] Run outside the declaration refuses naming the dimension before any server starts — runtime `__init__.py:251` before `build_flags` (:270) and the build probe (:288), `test_cli.py::test_a_runtime_run_outside_its_campaign_refuses_before_any_server_starts` asserts `running_server` and `probe_build` not called; quality `quality_cli.py:297` before `build_flags` (:322) and the probe (:333), `test_quality_cli.py::test_a_run_outside_its_campaign_refuses_before_any_server_starts`
- [x] Schema-24 row without `campaign_id` refused; cloud row naming a campaign refused; older rows validate — `row_contract.py:759,782,1270-1292`, `test_row_contract.py::test_a_row_missing_its_campaign_is_refused_naming_it`, `test_a_cloud_row_belongs_to_no_campaign`, `test_a_row_below_the_campaign_schema_validates_without_it`
- [x] No campaign writes `"none"`; a campaign run writes its id on every row — `test_cli.py::test_a_runtime_row_with_no_campaign_belongs_to_none`, `test_a_runtime_row_under_a_campaign_carries_its_id`, `test_quality_cli.py::test_a_run_with_no_campaign_records_that_it_belongs_to_none`, `test_a_run_under_a_campaign_records_its_id_on_every_row`; judge probe stamps `none` and refuses `CAMPAIGN_ID` (`judge_probe.py:445`, `test_judge_probe.py` parametrized refusal)

### Phase 3 — Docs, memory and CHANGELOG

- [x] Declaration format, `CAMPAIGN_ID` and the completeness command documented — `aidd_docs/memory/cli.md`, `docs/setup.md`, `.env.example`, `CHANGELOG.md`, `codebase-map.md`
- [x] Every gate command exits 0 — `ruff check` "All checks passed!", `ruff format --check` "663 files already formatted", `mypy` "Success: no issues found in 63 source files", `pytest -q` "2268 passed, 2 warnings in 155.29s", coverage 98.21% (gate 95%)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | code | 2 | `tests/test_quality_cli.py:686` | The quality refusal test asserts `running_server` not called but not `probe_build`; "before the build probe" is proven only by code order (`quality_cli.py:297` < `:333`) | Add `started["probe_build"].assert_not_called()` as the runtime test does |
| 🟢 minor | code | 2 | `src/wave_local_ai_v2/campaigns.py:502` | The runtime run (`suite_id=None`) skips the exclusion check entirely, so a roster entry the campaign declares `refused` on every suite can still be run by the runtime CLI under that campaign | Refuse a suite-less run when exclusions cover every declared suite for its (engine, variant, roster entry) |
| 🟢 minor | fit | 2 | `src/wave_local_ai_v2/quality_cli.py:297-307` | Refusing a cloud provider under a campaign is consistent with the row-contract rule (a cloud row is always `none`; without the pre-check the run would fail at `append_row` after the local batch), but it splits a campaign's local batch and its cloud reference into two invocations with different `run_id`s, losing the same-`run_id` pairing | Not scope creep; owner may later prefer stamping `none` on cloud rows of a campaign invocation instead of refusing |
| 🟢 minor | fit | 1 | `src/wave_local_ai_v2/campaigns.py:416` | An exclusion with no coordinate covers the whole matrix, so a campaign whose every cell is "dropped" passes completeness with zero rows | Refuse an exclusion naming no coordinate |
| 🟢 minor | fit | 1 | `src/wave_local_ai_v2/campaigns.py:553-590` | Completeness reads quality rows only; correct under the acceptance's cell = engine x variant x roster entry x suite (runtime rows name no suite), and quality rows carry per-item TTFT/tokens/energy, but runtime rows under a campaign are never accounted for | None for this story; note for order 12 if runtime per engine must be complete too |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (13/13)                                      |
| Files checked | campaigns.py, __init__.py, quality_cli.py, judge_probe.py, row_contract.py, settings.py, comparison.py, read_model.py, bundle_export.py, pyproject.toml, test_campaigns.py, test_cli.py, test_quality_cli.py, test_judge_probe.py, test_row_contract.py, cli.md, setup.md, CHANGELOG.md, .env.example |
| Unchecked     | none                                              |
| Unplanned     | Judge probe refusing `CAMPAIGN_ID` and quality refusing cloud providers under a campaign: both in plan Decisions, both forced by the row-contract cloud rule, judged in scope. `aidd_docs/campaigns/` is a sibling of `aidd_docs/results/`, not ignored by `.gitignore`: meets "tracked directory beside the results" |
