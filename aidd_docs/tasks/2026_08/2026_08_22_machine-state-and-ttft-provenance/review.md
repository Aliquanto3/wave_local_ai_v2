# Review: Each repetition records machine state, and the row states its TTFT provenance

- **Verdict**: changes-requested
- **Diff**: `ab9280d...working-tree` (tracked changes plus untracked `src/wave_local_ai_v2/machine_state.py`, `tests/test_machine_state.py`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 0 critical, 4 warning, 3 minor

## Phases

### Phase 1 — NVML temperature/throttle reads and per-repetition sampling

- [x] Task 1 — stubbed handle decodes temperature and throttle bitmask; either query's exception yields `None` / `[]` without raising — `src/wave_local_ai_v2/nvml.py:31-89`, `tests/test_nvml.py:82-122`. All nine `nvmlClocksEventReason*` constants, `nvmlDeviceGetTemperature`, `NVML_TEMPERATURE_GPU` and `nvmlDeviceGetCurrentClocksEventReasons` confirmed present on the installed `nvidia-ml-py==13.610.43`, with the bit values (1,2,4,8,16,32,64,128,256) matching the test literals.
- [x] Task 2 — `read_machine_state()` returns all four fields on a stubbed session; `cpu_temp_c` `None` and `cpu_temp_source` `"unavailable"` on this platform — `src/wave_local_ai_v2/machine_state.py:38-93`, `tests/test_machine_state.py:37-78`.
- [x] Task 3 — every warm-up and counted `RepetitionResult` carries the stub's `machine_state`, called once per repetition (`call_count == 3` for 1+2) — `src/wave_local_ai_v2/repetitions.py:115-180`, `tests/test_repetitions.py:167-186`.
- [x] Task 4 — `_run` passes `read_machine_state` to both `run_repetition_set` calls; the written row's repetitions and warm-up repetitions each carry the key — `src/wave_local_ai_v2/__init__.py:298,310`, `tests/test_cli.py:183-184`.

### Phase 2 — Spread, the unreliable flag, thermal posture, settings

- [x] Task 1 — `RUNTIME_SPREAD_THRESHOLD` defaults to `0.10`, overridable, negative refused by name — `src/wave_local_ai_v2/settings.py:35,76-82`, `tests/test_settings.py:42,77,84,97-98`.
- [x] Task 2 — 5.4% spread → `unreliable: False`, 12% → `True`, both carry all three `*_spread` fields; a wildly varying `ttft_ms` never flags — `src/wave_local_ai_v2/aggregation.py:117-140`, `tests/test_aggregation.py:110-160`.
- [x] Task 3 — each of the five new fields, removed one at a time, is refused by name — `src/wave_local_ai_v2/row_contract.py:79-87`, `tests/test_row_contract.py:141-156`.
- [x] Task 4 — written row carries all five, `thermal_posture` reads `"fixed_cooldown"`, and `append_row`'s `validate_row` gate accepts it — `src/wave_local_ai_v2/__init__.py:358,377`, `tests/test_cli.py:185-190`.

### Phase 3 — TTFT provenance

- [x] Task 1 — `parse_timings` returns `ttft_source == "server_reported"` beside the three metrics — `src/wave_local_ai_v2/timings.py:29-30,75`, `tests/test_timings.py:32-33`.
- [x] Task 2 — `validate_row` accepts both declared values, refuses a missing field, refuses any other string naming it — `src/wave_local_ai_v2/row_contract.py:160-168`, `tests/test_row_contract.py:158-168`.
- [x] Task 3 — row carries `ttft_source`; the streaming-TTFT comment now states only what the row does not, and the thermal-slowdown / SSE-flush investigation history is intact — `src/wave_local_ai_v2/__init__.py:236-252,362-365`.

### Phase 4 — Live validation, changelog, docs

- [x] Task 1 — live row's five repetitions and its warm-up each carry `gpu_temp_c` 65.0-68.0 and a non-empty `gpu_throttle_reasons`; Evidence table filled with observed spread and the CPU-temperature outcome — `phase-4.md:97-121`, `aidd_docs/results/runtime-reference.jsonl:3`.
- [x] Task 2 — the reference bundle carries the new fields and the README states the observed 5.2% against the 10% threshold and that the flag did not fire — `aidd_docs/results/README.md:35-54`. Partial on presentation, see finding W4.
- [x] Task 3 — `[Unreleased]` names machine state, spread + `unreliable`, `thermal_posture` and `ttft_source` — `CHANGELOG.md:48-63`.
- [x] Task 4 — every new row field and `RUNTIME_SPREAD_THRESHOLD`'s default documented — `docs/setup.md:221-232`.
- [x] Task 5 — `uv run pytest`: `239 passed`, coverage 97.32%. `ruff check` / `ruff format --check` / `mypy src/ scripts/` all clean.

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | code | 1 | `src/wave_local_ai_v2/machine_state.py:81-89` | When a chip key matches but no entry's label contains `package`, the `next(..., entries[0])` default falls back to the first sensor and labels it `cpu_temp_source: "psutil"` — publishing a per-core temperature as the CPU **package** temperature. `phase-1.md:84` specifies `None` / `"unavailable"` when the package label is not found. Unreachable on this platform, so no test covers the branch; the whole increment's premise is that a published number names what it is. | Drop the `entries[0]` default: return `None, CPU_TEMP_SOURCE_UNAVAILABLE` when no entry is package-labelled. **Fixed in-branch** (`machine_state.py:76-92`). |
| 🟡 | rot | 2 | `src/wave_local_ai_v2/aggregation.py:33-48` | `UNRELIABLE_SPREAD_METRIC` and its comment were inserted between `AGGREGATION_LABELS`'s explanatory block ("One entry per measurement a runtime row publishes… its label names what was actually sampled.") and the dict it documents, so that pre-existing paragraph now reads as documentation of the new constant. | Move the new constant and its comment above the `AGGREGATION_LABELS` comment block, restoring comment-to-declaration adjacency. **Fixed in-branch** (`aggregation.py:33-50`). |
| 🟡 | code | 2 | `src/wave_local_ai_v2/aggregation.py:91-97` | `spread` lets a zero median escape as a bare `ZeroDivisionError`, while `sample_sd` in the same module raises a named `AggregationError` for its own undefined case. `plan.md:75` justified "let it raise" by that very `AggregationError` precedent; the code raises the builtin instead, so a full benchmark would die at aggregation time with an unattributable `float division by zero`. | Raise `AggregationError` naming the zero median, keeping the "never fabricate `0.0` or `inf`" decision unchanged. **Fixed in-branch** (`aggregation.py:93-105`, `tests/test_aggregation.py:110-113`). |
| 🟡 | rot | 4 | `aidd_docs/results/README.md:14-19` | The section still opens "Two rows, copied from lines 4 and 5" with a claim table of two `gen_tok_per_s` values, while the file now holds three rows. The added row reads `gen_tok_per_s` 15.26 — below the 17-18 rows the same section excludes two paragraphs later precisely because they were measured under `sw_thermal_slowdown` — and neither its own block nor the claim table states that number or its cause, though the row's `gpu_throttle_reasons` carry `sw_thermal_slowdown`. `phase-4.md:109-121` states it plainly; the published README does not. | Update the row count and the claim table, and state in the Row 3 block its `gen_tok_per_s` and that it is thermally suppressed, so it cannot be read as a throughput claim. **Fixed in-branch** (`aidd_docs/results/README.md:14-20,38-59`). |
| 🟢 | code | 1 | `src/wave_local_ai_v2/nvml.py:44-48` | The `EventReasons`-over-`ThrottleReasons` rationale comment sits above `clocks_event_reason_names()`, but the call it justifies (`nvmlDeviceGetCurrentClocksEventReasons`) is in `read_clocks_event_reasons()` further down. | Move the comment onto the reading function, or make it a module-level note. |
| 🟢 | code | 1 | `tests/test_machine_state.py:70-78` | The CPU-unavailable test stubs nothing, so it opens a real NVML session as a side effect and asserts a platform-specific `psutil` build (it would fail on any Linux box exposing `coretemp`). | Stub `pynvml` for isolation and gate the psutil assertion on `hasattr(psutil, "sensors_temperatures")`. |
| 🟢 | conform | 4 | `docs/setup.md:210-232` | `RUNTIME_WARMUP_COUNT` is in `.env.example` but documented nowhere in `docs/setup.md`, while the other three runtime settings are. Pre-existing, not introduced by this diff. | Add one line beside the `RUNTIME_REPETITIONS` / `RUNTIME_COOLDOWN_S` walkthrough. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (16/16)                                      |
| Files checked | `src/wave_local_ai_v2/{__init__,aggregation,machine_state,nvml,repetitions,row_contract,settings,timings}.py`, `tests/test_{aggregation,cli,machine_state,nvml,repetitions,row_contract,settings,timings}.py`, `.env.example`, `CHANGELOG.md`, `docs/setup.md`, `aidd_docs/results/{README.md,runtime-reference.jsonl}` |
| Unchecked     | none                                              |
| Unplanned     | `nvml.clocks_event_reason_names()` is a function rather than `phase-1.md:72`'s `CLOCKS_EVENT_REASON_NAMES` module constant — a deliberate, documented deviation (lazy `pynvml` import forbids reading constants at import time), not drift; `tests/test_cli.py:251-277` adds a threshold-override run beyond the plan's phase-2 test list |
