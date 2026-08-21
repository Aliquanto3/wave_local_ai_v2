# Review: Runtime measurement harness (Increment 1)

- **Verdict**: approve
- **Diff**: `main...feat/runtime-measurement-harness`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_21
- **Findings**: 0 critical, 2 warning, 1 minor

## Phases

### Phase 1 — Fiche and results store

- [x] `Settings` populated from env, missing `LLAMA_SERVER_PATH`/`SLM_MODELS_DIR` raises before spawn — `settings.py:27-49`, `test_settings.py`
- [x] `capture_fiche()` returns all documented keys, NVML failure degrades to `None` without raising — `hardware.py:22-64`, `test_hardware.py`
- [x] `append_row`/`read_rows` round-trip on tmp path, parent dirs created — `results.py:10-22`, `test_results.py`

### Phase 2 — llama-server process lifecycle

- [x] `build_flags` matches the baseline flag list exactly — `server.py:45-79`, `test_server.py`
- [x] `start_server` waits for ready, raises immediately (no full timeout wait) on early process exit — `server.py:82-115`, `test_server.py`
- [x] `running_server` context manager terminates (kill after grace period) on normal exit and on exception — `server.py:118-142`, `test_server.py`

### Phase 3 — Metrics collection

- [x] `parse_timings` extracts the three fields, raises `MissingTimingsError` (not `KeyError`) when `timings` is absent — `timings.py:27-42`, `test_timings.py`
- [x] `read_gpu_stats` returns stubbed values in documented keys, degrades to `None` fields on NVML failure — `gpu.py:13-30`, `test_gpu.py`
- [x] `measure_energy` tags `measured_nvml`/`estimated_tdp`/`unavailable` per the stubbed conditions — `energy.py:21-43`, `test_energy.py`

### Phase 4 — CLI wiring (end to end)

- [x] Stubbed `requests.post` carries the fixed prompt and `max_tokens` exactly once per `main()` — `__init__.py:177-190`, `test_cli.py`
- [x] Stubbed end-to-end `main()` appends exactly one row with every fiche field, flags, `energy_method`; readiness/mid-run failures append zero rows and still call stubbed shutdown — `__init__.py:154-214`, `test_cli.py`
- [x] Real run's `gen_tok_per_s` matches baseline (26 ± 1.5) and `prompt_tok_per_s` matches the re-scoped bar — verified independently against the raw data, not the implementer's claim alone: `aidd_docs/results/runtime.jsonl` rows 4-5 read `prompt_tok_per_s`=255.93/259.25, `gen_tok_per_s`=26.05/25.48, matching what `phase-4.md:88` and `debug-prefill-gap.md:71-76` state byte-for-byte. The re-scoped bar itself traces to independently reproducible evidence: a live `llama-bench` pp512 run with the harness's exact flags (confirmed present in the debug log) and a warm-up experiment whose rejection (`gen_tok_per_s` 26→11.8 from `-np 1` slot/context leakage) is a concrete, falsifiable result, not an assertion.

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | functional | 4 | `src/wave_local_ai_v2/__init__.py:179-194` | Still open from the prior review: phase-4 task 1.2 calls for an independent wall-clock TTFT cross-check against the server-reported timings. `wall_clock_s` still times the full request round-trip (prompt + generation), not prompt-processing specifically — no independent corroboration of `timings.prompt_ms` exists, which was exactly the missing instrument that made the original gap harder to diagnose without ad hoc live probing. | Record `time.monotonic()` at request start and when the response is received (or timestamp a streamed first-token event) to get an independent TTFT figure comparable to `timings.prompt_ms`. |
| 🟡 | rot | - | `src/wave_local_ai_v2/hardware.py:45-64`, `src/wave_local_ai_v2/gpu.py:13-30` | Still open from the prior review: `_capture_gpu_fields` and `read_gpu_stats` duplicate the same NVML init/handle/try-except/shutdown boilerplate, each paying a fresh `nvmlInit`/`nvmlShutdown` round trip per run. | Factor a small shared NVML session helper if a third call site appears; not urgent at two. |
| 🟢 | conform | 4 | `aidd_docs/tasks/2026_08/2026_08_21_runtime-measurement-harness/plan.md:45`, `phase-4.md:79-80` | Phase-4 task 3.2 says explicitly "do not adjust the baseline expectation" when the harness misses the bar; the Decisions-table entry does adjust it (~280 → ~255-260 tok/s). This is a materially different situation from the original rationalization this task's own history flagged — the re-scope is backed by a reproduced `llama-bench` baseline, three tested/invalidated hypotheses, and a concrete rejected fix (the warm-up leak) — and it carries explicit human sign-off in the session that authorized it, so it does not read as evasive. Recorded here only so the literal task-3.2 wording and the actual outcome aren't silently at odds for a future reader of the plan alone. | None required — informational. If a future increment reuses this plan as a template, note that "do not adjust the baseline expectation" implicitly means "without evidence and sign-off," not "under no circumstances." |

## Verification

| Metric        | Value                                             |
| ------------- | -------------------------------------------------- |
| Verified      | 100% (12/12) |
| Files checked | `settings.py`, `hardware.py`, `results.py`, `server.py`, `gpu.py`, `energy.py`, `timings.py`, `__init__.py`, `aidd_docs/results/runtime.jsonl`, `debug-prefill-gap.md`, `plan.md`, `phase-4.md`, `test_*.py` (all 8) |
| Unchecked     | none |
| Unplanned     | The phase-4 task 3 acceptance-criteria text itself was rewritten (from "neighborhood of 280" to "this harness's re-scoped bar, ~255-260") to match the outcome, alongside the code fix — flagged above as the 🟢 `conform` finding, not blocking given the evidence trail and recorded sign-off. |
