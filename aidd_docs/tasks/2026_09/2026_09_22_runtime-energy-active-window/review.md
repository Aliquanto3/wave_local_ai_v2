# Review: runtime-energy-active-window

- **Verdict**: changes-requested
- **Diff**: `main...feat/runtime-energy-active-window` (`468d4ad` plus the uncommitted fixes of the first review pass)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_22
- **Findings**: 0 critical, 1 warning, 2 minor

## Phases

### Phase 1 — Probe: verify per-repetition CodeCarbon tasks on this machine, decide the method

- [x] Probe ran against a real `llama-server` and printed overhead plus both energy figures — `phase-1.md:54-57` (median 1.650 ms; 0.0017348 kWh whole-window vs 0.0011335 kWh summed tasks, ratio 0.6534)
- [x] Pass/fail verdict stated for both questions with the actual numbers — `phase-1.md:56-57`
- [x] Phase 2 entered knowing the method (`per_repetition_tasks`, not the `whole_window_minus_idle_baseline` fallback) — `phase-1.md:58`; `src/wave_local_ai_v2/energy.py:33-42`

### Phase 2 — Runtime harness measures energy per repetition; schema, aggregation and read-model updates

- [x] `finish()` sums every task's channel deltas on success, all-`None` when any one fails or the tracker never started — `src/wave_local_ai_v2/energy.py:166-196`; `tests/test_energy.py` (construction failure, one `None` `stop_task`). CodeCarbon 3.3.0 `stop_task` returns `None` (no raise) on a missing task and `start_task` returns silently on failure (`.venv/.../codecarbon/emissions_tracker.py:736-806`); `_stop_task` covers both
- [x] Runtime row carries `energy_window_method`, `active_window_s` = summed `wall_clock_s`, `idle_window_s` = `(N-1) * cooldown_s` — `src/wave_local_ai_v2/__init__.py:370-375,427-429`; `tests/test_cli.py:251`, `:346`
- [x] `cost_total` and `cost_per_million_tokens` derive from the summed active-window `energy_kwh` — `src/wave_local_ai_v2/__init__.py:378,388`
- [x] `SCHEMA_VERSION == "12"`; three fields required on runtime only, quality rows still validate — `src/wave_local_ai_v2/row_contract.py:69-80,150-155`; `tests/test_row_contract.py:825`
- [x] `build_runtime` resolves the three fields; `energy_view` untouched — `src/wave_local_ai_v2/read_model.py:236-238` (in `RUNTIME_VIEW_FIELDS`, not `ENERGY_VIEW_FIELDS`)
- [x] `uv run pytest -q` passes in full — re-run: `985 passed`, coverage 95.66%; `ruff check`, `ruff format --check`, `mypy src` clean

### Phase 3 — PRD Methodology 15 gains the window rule; results README records the supersession

- [x] Methodology 15 states the window rule naming all three fields, no other Methodology sentence altered — `2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md:57` (single-line diff, item 15 only)
- [x] Results README carries a dated supersession note, pre-change rows and tables not edited — `aidd_docs/results/README.md:39-59`; `git diff main -- aidd_docs/results/README.md` is additions only (0 lines removed)

### Phase 4 — Live evidence: re-run a fast dense model and the MoE flagship, publish the before/after comparison

- [x] Two new runtime rows with `energy_window_method` `per_repetition_tasks`; validator exits 0 — live `runtime.jsonl` rows `45d2bf7d` / `cc1efa34`, schema `"12"`, commit `5d9a0044`; `uv run wave-local-ai-v2-validate` => `checked 598 row(s)`, `exit=0`
- [x] Before/after cost-per-token ratio computed from rows on disk — recomputed in review from `runtime.jsonl` + `runtime-reference.jsonl`: cost ratio 0.2963 => 0.0871, energy ratio 0.2954 => 0.0868; every figure in `aidd_docs/results/README.md:74-80` matches the stored rows to the printed precision
- [x] New dated section, existing `### Runtime` table untouched — `aidd_docs/results/README.md:61-96`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | rot | 2 | `src/wave_local_ai_v2/energy.py:38-39` | Residual of the first pass's window-method fix: the constant's comment still defines `unavailable` as a row whose energy "could not be measured at all", contradicting PRD Methodology 15 (`...-prd.md:57`, "could not measure every counted repetition"), plan Decisions row 3 and `finish()` itself (`energy.py:177-178` returns it on one lost delta). | Fixed in this commit: comment reworded to "could not be measured over every counted repetition (tracker never started, or one repetition's delta was lost)". |
| 🟢 minor | conform | 4 | `aidd_docs/results/README.md:61-96` | Section cites three rows (`68a5e1df`, `45d2bf7d`, `cc1efa34`) that exist only in the gitignored live `runtime.jsonl` (`.gitignore:32`), without the "not part of the committed bundle" note sibling sections carry (`README.md:219`, `:616`); a repo-only reader cannot recompute the ratios. | Logged to `tech-debt.md`: add the note, or promote the two after rows to a committed bundle file. |
| 🟢 minor | rot | 4 | `aidd_docs/tasks/2026_09/2026_09_22_runtime-energy-active-window/phase-4.md:47` | Test scope still predicts the gap "narrows or inverts"; the published outcome widened it (0.2963 => 0.0871). Task 2 already required reporting the actual outcome, which the README does. | Logged to `tech-debt.md`: restate the line as the observed outcome. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (14/14) |
| Files checked | `src/wave_local_ai_v2/__init__.py`, `energy.py`, `aggregation.py`, `row_contract.py`, `read_model.py`, `.venv/.../codecarbon/emissions_tracker.py` (3.3.0 `start_task`/`stop_task`), `tests/test_energy.py`, `test_cli.py`, `test_row_contract.py`, `test_read_model.py`, `test_aggregation.py`, `store_fixtures.py`, `aidd_docs/results/README.md`, `aidd_docs/results/runtime.jsonl`, `runtime-reference.jsonl`, PRD `2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`, `aidd_docs/tasks/2026_09/2026_09_22_audit/report.md` (C3) |
| Unchecked     | none |
| Unplanned     | First review pass's fixes, landed in this commit: PRD M15 / plan Decisions row 3 / phase-2 test scope aligned on `unavailable` for a partial loss; `wall_clock_s` computed once and reused as `active_window_s`; dead `runtime_repetitions > 0` guard dropped; `start_task`/`stop_task` cost inside `wall_clock_s` documented (`__init__.py:366-368`); `_run`-level test for the unavailable-tracker row (`tests/test_cli.py:346`). `tests/test_aggregation.py` label assertions follow from phase 2 task 3. |
