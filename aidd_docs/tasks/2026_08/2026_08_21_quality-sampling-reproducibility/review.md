# Review: Reproducible quality sampling and honest test coverage (PR #1, commits since the last review)

- **Verdict**: changes-requested
- **Diff**: `cc03424...b03bd5c`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_21
- **Findings**: 0 critical, 3 warning, 6 minor

## Phases

### Phase 1 — Deterministic sampling for both models

- [x] Every `/completion` request carries `seed`, `temperature: 0`, `top_k: 0`, `top_p: 1.0`, `presence_penalty: 0`, read from the recorded call args — `quality_cli.py:41-52`, `quality_cli.py:120-124`, `tests/test_quality_cli.py:227-244`
- [x] `build_flags` returns the same list, `tests/test_server.py`'s exact-list comparison unmodified — `server.py` untouched in this range; `tests/test_server.py:10-45` not in the diff
- [x] Every Mistral body carries `temperature: 0` and an integer `random_seed`, non-200 and shape-guard behavior unchanged — `mistral_client.py:52-57`, `mistral_client.py:61-73`, `tests/test_mistral_client.py:57-66`
- [x] `MODEL` is a dated id present on the live API, recorded in every cloud row — `mistral_client.py:26`, `tests/test_quality_cli.py:279-292`; independently corroborated: the two real runs returned HTTP 200 and `suite_accuracy 1.00` for `mistral-small-2603`, which a nonexistent id could not
- [x] Two consecutive real runs give identical `predicted_label` per item and identical `suite_accuracy` — re-verified against `aidd_docs/results/quality.jsonl`: 40 rows, 20 `(provider, item_id)` pairs compared, 0 label mismatches
- [x] The two runs' `suite_accuracy` figures written into the phase file with date and model ids — `phase-1.md:104`; re-derived from the artifact: local `0.60`/`0.60`, cloud `1.00`/`1.00`

### Phase 2 — Sampling provenance in every quality row

- [x] All `2 x 10` rows carry a sampling block with temperature, seed and penalties — `quality_cli.py:184-190`, `tests/test_quality_cli.py:256-274`
- [x] Each provider's block matches what that provider was sent; a swap fails — `tests/test_quality_cli.py:266-274` asserts `random_seed` absent from local blocks and `presence_penalty` absent from cloud blocks
- [ ] No quality row carries a runtime-only field **and no runtime row gains a sampling field** — only the first direction is asserted (`tests/test_quality_cli.py:11-19`, `:93`). Nothing in `tests/test_cli.py` asserts `"sampling" not in row`, so the runtime-side half of the disjointness guard does not exist
- [x] A differing sampling block needs no reader or schema change — `results.py:17-22`, `read_rows` is schema-free JSONL and returns whatever each line holds

### Phase 3 — Tests that exercise the real code path

- [x] `pynvml` raising gives three `None` GPU fields and propagates nothing; deleting the `except` fails the test — `tests/test_hardware.py:25-52`; mutation run: narrowing `hardware.py:57` to `except ZeroDivisionError` => `1 failed, 1 passed`
- [x] `main()` issues exactly one request carrying the fixed prompt and `max_tokens`; changing either fails — `tests/test_cli.py:168-176`; mutation run: `n_predict` 128 -> 64 => `test_run_sends_the_fixed_prompt_and_max_tokens_exactly_once` failed
- [x] No CodeCarbon tracker built, `energy_method` asserted as a concrete value, the `main()` tests well under a second — `tests/test_cli.py:65-70`, `:95-96` (`== "estimated_tdp"`); measured `68 passed in 3.03s`, both `main()` tests below the `--durations` 0.005s cutoff, against 5.39s and 2.95s before
- [x] Leaving `running_server` normally terminates the process without mocking `stop_server`; removing the `finally` fails — `tests/test_server.py:140-156`; mutation run: dropping `finally: stop_server(process)` => `2 failed`
- [x] `TimeoutExpired` on the first `wait` escalates to `kill()` and waits again — `tests/test_server.py:126-137`; mutation run: replacing the kill escalation with `pass` => `1 failed`
- [x] The shutdown assertion names one expected call per platform, so swapping the two fails — `tests/test_server.py:91-97`; mutation run: replacing the win32 branch with a bare `terminate()` => `2 failed`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | functional | 2 | `tests/test_cli.py:88-97` | The phase-2 disjointness criterion is bidirectional, but only the quality-row side is asserted. No test anywhere fails if a runtime row gains a `sampling` key, so half the guard protecting `architecture.md`'s "never merged into a single table" is missing. | Mirror `RUNTIME_ONLY_FIELDS`: add a `QUALITY_ONLY_FIELDS = {"sampling", "suite_accuracy", "expected_label", "predicted_label", "task_suite"}` set in `tests/test_cli.py` and assert `QUALITY_ONLY_FIELDS.isdisjoint(row.keys())` in `test_run_appends_one_row_with_fiche_and_metrics`. |
| 🟡 | code | 3 | `tests/test_cli.py:179-187` | `test_run_builds_no_real_energy_tracker` asserts only that the fixture's own `measure_energy` patch was called. The patch guarantees that outcome, so the test exercises no `src/` behavior and cannot fail for any code change: it is the same "test stubs out what it claims to verify" shape this phase exists to remove. | Drop the test (the fixture's patch and the `energy_method == "estimated_tdp"` assertion at `:95` already carry the criterion), or make it real: `import sys` and assert `"codecarbon" not in sys.modules` after `_run()`. |
| 🟡 | fit | 1 | `src/wave_local_ai_v2/mistral_client.py:26`, `src/wave_local_ai_v2/quality_cli.py:82-86` | Pinning `MODEL` to a dated id turns model rotation into a hard failure at the first cloud request, i.e. after the full local suite has already run (server spawn plus 10 completions, ~49s in the recorded 21:55:11-21:56:00 run). `_run` already pre-flights `MISTRAL_API_KEY` before the local suite for exactly this reason, with a comment saying so; the plan accepted the pinning tradeoff without extending that guard to the new foreseeable failure. | In `_run`, beside the API-key check, verify the id is live before `_run_local_suite`: a `GET https://api.mistral.ai/v1/models` membership check on `mistral_client.MODEL`, raising `SettingsError` naming the id when absent. |
| 🟢 | code | 3 | `tests/test_cli.py:127` | The failure-path energy stub returns `energy_method: "x"`, a value `measure_energy` can never produce (`energy.py:29`, `:38`, `:41` yield only `unavailable`, `measured_nvml`, `estimated_tdp`). An impossible fake invites a later assertion to be written against a value the real code cannot emit. | Use `"unavailable"`, the value the real tracker-init failure path returns. |
| 🟢 | code | 1 | `tests/test_mistral_client.py:72` | `assert not MODEL.endswith("-latest")` is weaker than the criterion it backs ("`MODEL` is a dated model id"): `mistral-small`, `mistral-small-newest` or an empty-suffix typo all pass. | Assert the shape instead: `import re` and `assert re.fullmatch(r".+-\d{4}", MODEL)`. |
| 🟢 | rot | 1 | `tests/test_quality_cli.py:290` | The alias assertion is duplicated verbatim from `tests/test_mistral_client.py:72`. Two copies of one rule drift apart when the rule is tightened, and the quality-CLI test's own subject is the row content, not the id's shape. | Keep the id-shape assertion in `test_mistral_client.py` only; leave `test_cloud_rows_record_the_dated_model_id` asserting just `cloud_ids == {mistral_client.MODEL}`. |
| 🟢 | rot | 3 | `tests/test_server.py:93-97`, `tests/test_server.py:152-155` | The `sys.platform == "win32"` branch is copy-pasted into two tests. Tightening the platform expectation, or adding a third platform, means editing both. | Extract one helper, `def assert_stopped_gracefully(fake_process) -> None`, holding the branch, and call it from both tests. |
| 🟢 | code | 3 | `tests/test_hardware.py:26-39`, `tests/test_hardware.py:42-52` | The fixture returns `fake_module` but no test asserts on it, so nothing proves the NVML boundary was reached. If the `try` body failed earlier for an unrelated reason (an `ImportError`, a `nvml_device` change), `except Exception` still returns the three `None`s and the test passes for the wrong reason. | Add `assert pynvml_that_raises.nvmlInit.called` to the test, so the intended exception source is confirmed. |
| 🟢 | rot | 1 | `aidd_docs/tasks/2026_08/2026_08_21_quality-sampling-reproducibility/phase-1.md:103` | The evidence cites two run windows (21:55:11-21:56:00, 21:56:08-21:56:53), but a quality row carries no timestamp or run id (`quality_cli.py:157-190`), so the 40 rows in `quality.jsonl` can only be split back into the two runs by append order. The claim is re-verifiable that way, but not by the times the document names. | Either drop the times from the evidence line, or record a run id per row so the split is reconstructible from the artifact itself. |

## Verification

| Metric        | Value                                                                        |
| ------------- | ---------------------------------------------------------------------------- |
| Verified      | 94% (15/16)                                                                  |
| Files checked | `src/wave_local_ai_v2/mistral_client.py`, `tests/test_cli.py`, `tests/test_hardware.py`, `tests/test_mistral_client.py`, `tests/test_quality_cli.py`, `tests/test_server.py`, `plan.md`, `phase-1.md`, `phase-3.md` |
| Unchecked     | Phase 2 — "no runtime row gains a sampling field" — fix                       |
| Unplanned     | `phase-3.md` created in `de78802` (the plan's own artifact, traces to the plan Phases table, not to a criterion); `plan.md` status flips `in-progress` -> `blocked` (`b8dd3d6`) -> `implemented` (`b03bd5c`), and the `phase-1.md` status flip in `b03bd5c`, trace to no acceptance criterion |
