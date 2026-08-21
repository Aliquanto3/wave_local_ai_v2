# Review: Full branch (feat/runtime-measurement-harness vs main)

- **Verdict**: changes-requested
- **Diff**: `main...feat/runtime-measurement-harness` (working tree, includes uncommitted changes)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_21
- **Findings**: 0 critical, 2 warning, 4 minor

## Phases

<!-- Two plans on this branch: Runtime measurement harness (Increment 1) and Deterministic classification scoring. -->

### Plan: Runtime measurement harness (Increment 1) — Phase 1 — Fiche and results store

- [x] `Settings` populated from env, missing `LLAMA_SERVER_PATH`/`SLM_MODELS_DIR` raises before spawn — `settings.py:39-40`, `test_settings.py`
- [x] `capture_fiche()` returns all documented keys, NVML failure degrades to `None` without raising — `hardware.py:24-58`, `test_hardware.py`
- [x] `append_row`/`read_rows` round-trip on tmp path, parent dirs created — `results.py:10-22`, `test_results.py`

### Plan: Runtime measurement harness (Increment 1) — Phase 2 — llama-server process lifecycle

- [x] `build_flags` matches the baseline flag list exactly — `server.py:45-79`, `test_server.py`
- [x] `start_server` waits for ready, raises immediately (no full timeout wait) on early process exit — `server.py:82-115`, `test_server.py`
- [x] `running_server` context manager terminates (kill after grace period) on normal exit and on exception — `server.py:118-142`, `test_server.py`

### Plan: Runtime measurement harness (Increment 1) — Phase 3 — Metrics collection

- [x] `parse_timings` extracts the three fields, raises `MissingTimingsError` (not `KeyError`) when `timings` is absent — `timings.py:27-42`, `test_timings.py`
- [x] `read_gpu_stats` returns stubbed values in documented keys, degrades to `None` fields on NVML failure — `gpu.py:15-28`, `test_gpu.py`; NVML init/handle/shutdown boilerplate now shared via `nvml.py` (prior review's `rot` finding resolved)
- [x] `measure_energy` tags `measured_nvml`/`estimated_tdp`/`unavailable` per the stubbed conditions — `energy.py:21-43`, `test_energy.py`

### Plan: Runtime measurement harness (Increment 1) — Phase 4 — CLI wiring (end to end)

- [x] Stubbed `requests.post` carries the fixed prompt and `max_tokens` exactly once per `main()` — `__init__.py:194-205`, `test_cli.py`
- [x] Stubbed end-to-end `main()` appends exactly one row with every fiche field, flags, `energy_method`; readiness/mid-run failures append zero rows and still call stubbed shutdown — `__init__.py:154-229`, `test_cli.py`
- [x] Real run's `gen_tok_per_s` matches baseline (26 ± 1.5) and `prompt_tok_per_s` matches the re-scoped bar — carried from the prior review of this plan alone: `aidd_docs/results/runtime.jsonl` rows 3-4 read 255.93/259.25 `prompt_tok_per_s`, 26.05/25.48 `gen_tok_per_s`, matching `phase-4.md:88`/`debug-prefill-gap.md`. TTFT independent-cross-check (task 1.2) remains unmet — see `fit` finding below, not a graded criterion.

### Plan: Deterministic classification scoring — Phase 1 — Classification task suite and deterministic scorer

- [x] `CLASSIFICATION_TASK_SUITE` has 10 items (≥8), every `expected_label` a member of `LABELS`, no I/O on import — `classification_suite.py:19-96`, `test_classification_suite.py`
- [x] `normalize_label` matches clean/noisy-whitespace/mixed-case/embedded completions, returns `None` (never raises) for no match — `scoring.py:20-30`, `test_scoring.py`
- [x] `score_item` correct only on exact match, `False` (not a raise) when unparseable; `score_suite([])` returns `0.0`, mixed list returns the exact fraction — `scoring.py:42-61`, `test_scoring.py`

### Plan: Deterministic classification scoring — Phase 2 — Cloud model client (Mistral)

- [x] `complete_prompt` returns the `content` string, sends the correct URL/headers/body — `mistral_client.py:27-52`, `test_mistral_client.py`
- [x] Non-200 response raises `MistralRequestError` naming the status code — `mistral_client.py:39-43`, `test_mistral_client.py`
- [x] A 200 response missing `choices` raises `MistralRequestError`, not a raw `KeyError`/`IndexError` — `mistral_client.py:45-51`, `test_mistral_client.py`
- [x] No test in `test_mistral_client.py` makes a live network call — `test_mistral_client.py:16-19,33-35,44-47` (all stub `requests.post`)

### Plan: Deterministic classification scoring — Phase 3 — Quality results store and settings

- [x] `load_settings()` returns `quality_results_path`/`mistral_api_key` from env, or their defaults when unset, without raising — `settings.py:41-53`, `test_settings.py`
- [x] Existing `Settings(...)` 3-field call sites in `tests/test_cli.py` still pass unmodified (new fields default) — `settings.py:26-27`, `test_cli.py`
- [x] `.env.example` lists `QUALITY_RESULTS_PATH` with the same default value used in code — `.env.example:6`, `settings.py:12`

### Plan: Deterministic classification scoring — Phase 4 — CLI wiring (end to end, both models)

- [x] Local server started exactly once for the whole suite, no local-model row carries a fiche/timings/energy field — `quality_cli.py:67-86`, `test_quality_cli.py`
- [x] One Mistral call per suite item with that item's prompt; empty `mistral_api_key` raises `SettingsError` before any HTTP call — `quality_cli.py:89-96`, `test_quality_cli.py`
- [x] `2 * len(CLASSIFICATION_TASK_SUITE)` rows written, one per item per model, `prompt` matches verbatim, `suite_accuracy` equal within a model — `quality_cli.py:99-122`, `test_quality_cli.py`
- [x] No quality row carries any runtime-only field (`cpu`, `ram_gb`, `gpu_name`, `ttft_ms`, `prompt_tok_per_s`, `gen_tok_per_s`, `energy_method`) — `quality_cli.py:109-119`, `test_quality_cli.py:11-19,87-93`
- [x] `wave-local-ai-v2-quality` entry point registered; `SettingsError`/`MistralRequestError` during `_run()` print to stderr and exit 1 — `pyproject.toml:20`, `quality_cli.py:34-44`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | code | Quality:4 | `src/wave_local_ai_v2/quality_cli.py:84` | `response_json["content"]` is indexed directly with no shape guard, unlike every other HTTP boundary in the branch (`mistral_client.complete_prompt` wraps its parse in `MistralRequestError`; `timings.py` wraps its parse in `MissingTimingsError`). A malformed/unexpected llama-server `/completion` body raises a raw `KeyError`, which `main()`'s `except (SettingsError, server.ServerStartupError, requests.RequestException, MistralRequestError)` does not catch — the CLI crashes with an unhandled traceback instead of the clean stderr+exit(1) path every other failure mode gets. No test exercises this shape. | Wrap the parse (e.g. `try: content = response_json["content"] except (KeyError, TypeError): raise ...`) using a project error type, or reuse `SettingsError`/a new small error, and catch it in `main()`. |
| 🟡 | code | Quality:4 | `src/wave_local_ai_v2/quality_cli.py:47-51` | `_run()` runs the full local-model suite (start `llama-server`, N completions) before `_run_cloud_suite` checks `settings.mistral_api_key` is non-empty. A run with no Mistral key configured burns the entire local pass — GPU time, a full server lifecycle — before failing on the missing key, even though the check itself is free. `test_run_raises_before_any_cloud_call_when_mistral_key_missing` confirms the current (wasteful) order rather than catching it. | Check `settings.mistral_api_key` before `_run_local_suite`, not only before the cloud loop, so a missing key fails immediately. |
| 🟢 | fit | Runtime:4 | `phase-4.md:64`, `src/wave_local_ai_v2/__init__.py:177-194` | Carried from the prior review of the runtime-harness plan alone: phase-4 task 1's independent wall-clock TTFT cross-check went unmet — attempted via streaming, reverted after a live `gen_tok_per_s` regression confounded by a since-confirmed thermal-throttle event. Not a graded criterion (the acceptance-criteria table's task-1 row only requires the fixed prompt/`max_tokens` sent once). | None required. A future TTFT cross-check needs slot isolation (`id_slot`/`/slots` erase), not a retry of streaming or a second request on the shared `-np 1` slot. |
| 🟢 | conform | - | `CLAUDE.md:33-39` | Two new assistant-behavior rules (recommend-next-AIDD-skill, model/effort recommendation) are bundled into this feature branch's diff. Neither traces to either plan (runtime-measurement-harness or classification-quality-scoring) — an unrelated process-instructions change riding along with feature code. | None required for this diff to merge; carry it as its own commit/PR so the feature branch's history stays traceable to its plan. |
| 🟢 | rot | - | `.secrets.baseline` | Staged change is a binary diff (CRLF/regeneration artifact) against a file whose parsed content (`generated_at`, tracked file list) is identical to `main`'s version — a regenerated-but-equivalent file bundled into the diff. | None required; re-run `detect-secrets scan` only when the actual secret inventory changes, to avoid no-op diffs on this file. |
| 🟢 | conform | - | `aidd_docs/tasks/2026_08/2026_08_21_runtime-measurement-harness/review.md` (uncommitted) | The working-tree edit to this file's `## Findings`/`## Verification` adds a fourth section, `### Independent re-derivation`, not in the review skill's closed section list (`Phases`, `Findings`, `Verification` only). It also self-contradicts its own header (`0 warning, 2 minor`) against the two 🟡 `functional`/`rot` rows it otherwise carries forward. This review (in a separate folder) supersedes it for the branch-level verdict. | Either finish that file into a valid report (drop the extra section, fold its content into `Verification`'s `Unplanned` row) or discard the uncommitted edit and keep the last-committed, valid version. |

## Verification

| Metric        | Value                                             |
| ------------- | -------------------------------------------------- |
| Verified      | 100% (28/28) |
| Files checked | `settings.py`, `hardware.py`, `results.py`, `server.py`, `gpu.py`, `energy.py`, `timings.py`, `nvml.py`, `__init__.py`, `classification_suite.py`, `scoring.py`, `mistral_client.py`, `quality_cli.py`, `.env.example`, `.gitignore`, `pyproject.toml`, `CLAUDE.md`, `.secrets.baseline`, all 15 `test_*.py`, both plans' `plan.md`/`phase-*.md`, `debug-prefill-gap.md`, `aidd_docs/results/runtime.jsonl` |
| Unchecked     | none |
| Unplanned     | `CLAUDE.md`'s new rules and the `.secrets.baseline` regeneration trace to no acceptance criterion in either plan — flagged above as `conform`/`rot`, not blocking. `aidd_docs/backlog/*` (untracked) is the classification plan's own cited `Source`, not unplanned. `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` (untracked) is a planning document, out of code-review scope. Full suite green: `uv run pytest -q` → 54 passed; `uv run ruff check .` → all checks passed; `uv run mypy src` → no issues (13 source files). |
