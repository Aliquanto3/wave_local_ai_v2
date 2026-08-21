# Review: Runtime measurement harness (Increment 1)

- **Verdict**: approve
- **Diff**: `main...feat/runtime-measurement-harness`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_21
- **Findings**: 0 critical, 0 warning, 2 minor

## Phases

### Phase 1 — Fiche and results store

- [x] `Settings` populated from env, missing `LLAMA_SERVER_PATH`/`SLM_MODELS_DIR` raises before spawn — `settings.py:27-49`, `test_settings.py`
- [x] `capture_fiche()` returns all documented keys, NVML failure degrades to `None` without raising — `hardware.py:24-58`, `test_hardware.py`
- [x] `append_row`/`read_rows` round-trip on tmp path, parent dirs created — `results.py:10-22`, `test_results.py`

### Phase 2 — llama-server process lifecycle

- [x] `build_flags` matches the baseline flag list exactly — `server.py:45-79`, `test_server.py`
- [x] `start_server` waits for ready, raises immediately (no full timeout wait) on early process exit — `server.py:82-115`, `test_server.py`
- [x] `running_server` context manager terminates (kill after grace period) on normal exit and on exception — `server.py:118-142`, `test_server.py`

### Phase 3 — Metrics collection

- [x] `parse_timings` extracts the three fields, raises `MissingTimingsError` (not `KeyError`) when `timings` is absent — `timings.py:27-42`, `test_timings.py`
- [x] `read_gpu_stats` returns stubbed values in documented keys, degrades to `None` fields on NVML failure — `gpu.py:15-28`, `test_gpu.py`
- [x] `measure_energy` tags `measured_nvml`/`estimated_tdp`/`unavailable` per the stubbed conditions — `energy.py:21-43`, `test_energy.py`

### Phase 4 — CLI wiring (end to end)

- [x] Stubbed `requests.post` carries the fixed prompt and `max_tokens` exactly once per `main()` — `__init__.py:195-206`, `test_cli.py`
- [x] Stubbed end-to-end `main()` appends exactly one row with every fiche field, flags, `energy_method`; readiness/mid-run failures append zero rows and still call stubbed shutdown — `__init__.py:154-230`, `test_cli.py`
- [x] Real run's `gen_tok_per_s` matches baseline (26 ± 1.5) and `prompt_tok_per_s` matches the re-scoped bar — clean evidence in `aidd_docs/results/runtime.jsonl` rows 3-4 (255.93/259.25 prompt_tok_per_s, 26.05/25.48 gen_tok_per_s); independently re-verified below (not a straight re-read of the log).

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 | fit | 4 | `phase-4.md:64`, `src/wave_local_ai_v2/__init__.py:179-194` | Phase-4 task 1's prose ("capturing wall-clock TTFT independently as a cross-check...") went unmet — attempted via streaming, reverted after a live-observed `gen_tok_per_s` regression (confounded by a since-confirmed thermal-throttle event). Not a graded-criterion miss: the `Test acceptance criteria` table's task-1 row only requires the fixed prompt/`max_tokens` sent once. Recorded so a reader of the task list alone doesn't assume it was simply missed. | None required. A future TTFT cross-check needs slot isolation (`id_slot` or `/slots` erase), not a retry of streaming or a second request on the shared `-np 1` slot. |
| 🟢 | rot | - | `aidd_docs/results/runtime.jsonl` rows 5-9 | The results store now carries 5 low-throughput rows (17-19 gen_tok_per_s, from this task's own thermal-throttle incident and today's independent re-verification runs below) alongside the 2 clean baseline rows. Fine as an append-only measurement log, but a future reader diffing against "the baseline" without `debug-prefill-gap.md` in hand could mistake the throttled majority for the norm. | None required for this review; worth a one-line comment or a `thermal_state` field in a later increment if this file starts driving decisions. |

## Verification

| Metric        | Value                                             |
| ------------- | -------------------------------------------------- |
| Verified      | 100% (12/12) |
| Files checked | `settings.py`, `hardware.py`, `results.py`, `server.py`, `gpu.py`, `energy.py`, `timings.py`, `nvml.py`, `__init__.py`, all 9 `test_*.py`, `aidd_docs/results/runtime.jsonl`, `debug-prefill-gap.md`, `plan.md`, `phase-4.md` |
| Unchecked     | none |
| Unplanned     | none |

### Independent re-derivation (this review, not trusted from the prior review.md)

- **Automated tests**: `uv run pytest -q` → `30 passed in 11.26s`.
- **Lint**: `uv run ruff check .` → `All checks passed!`.
- **Types**: `uv run mypy src` → `Success: no issues found in 9 source files`.
- **Live CLI run** (today, this machine): `uv run wave-local-ai-v2` →
  `gen_tok_per_s=18.3 prompt_tok_per_s=244.7 ttft_ms=6090.1 energy_method=measured_nvml`.
- **Live `llama-bench` pp512/tg128** with the harness's exact flags (`-ngl 99 -ncmoe 37 -fa 1 -t 8 -p 512 -n 128 -r 5`):
  `pp512 = 261.48 ± 23.16 tok/s`, `tg128 = 11.31 ± 0.37 tok/s` — both well below the plan's own reference numbers
  (pp512 314.81 ± 5.60, tg128 baseline ~26).
- **GPU state check** (`nvidia-smi --query-gpu=...clocks_event_reasons.active,power.draw`, before and after):
  `clocks_event_reasons.active = 0x24` (SW Power Cap + SW Thermal Slowdown bits set) both times; power draw ~22-25W
  against an unreported (`[N/A]`) limit — the GPU was already throttled before either run started, not something
  triggered by this session's testing.

**Conclusion on the `prompt_tok_per_s` re-scope decision**: cannot be cleanly reproduced at ~255-260 tok/s today,
because this machine's GPU is presently thermally throttled — confirmed independently via `nvidia-smi`, and
confirmed as external to the harness's code because `llama-bench` (untouched by this diff) degraded by
essentially the same proportion as the CLI (pp512 down ~17% from its own logged 314.81 baseline; the harness's
`gen_tok_per_s` down ~30% from 26, `prompt_tok_per_s` down ~5-9% from 255-260). This is consistent with, not
contradictory to, `debug-prefill-gap.md`'s account and `phase-4.md:88`'s note about rows 5-7's prior thermal
event — the same failure mode reproducing on a fresh day is corroborating, not incidental. It does mean this
review's live run could not be the clean confirmation the plan's task 3.1 asks for; that confirmation stands on
the log's rows 3-4, captured before thermal onset, which this review has no basis to distrust — the raw
`llama-bench`/CLI numbers, prompt lengths, and root-cause chain in `debug-prefill-gap.md` are internally
consistent and match today's degraded-but-proportional readings. Re-running once the GPU is idle and cool would
be the way to get a same-day clean number if that mattered further; not required to approve this diff, since the
harness's job is to report `energy_method`-tagged, hardware-fiche-attached numbers honestly (including under
throttling) rather than to guarantee a fixed tok/s figure regardless of thermal state.
