# Review: runtime rows become a declared repetition protocol

- **Verdict**: approve
- **Diff**: `main...feat/runtime-repetition-protocol` (staged working tree plus this review's fixes)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 0 critical, 5 warning (all fixed in this pass), 8 minor (all filed to `aidd_docs/backlog/tech-debt.md`)

## Phases

### Phase 1 — Repetition protocol, pinned sampling, isolation

- [x] The three settings default to 5, 10.0 and 1, are overridable by environment variable, and a repetition count of 1 or 0 is refused by name — `src/wave_local_ai_v2/settings.py:32-34,54-74`; `tests/test_settings.py:63-110` parametrizes `1`, `0`, `-1` and `not-a-number` against `SettingsError` matching the variable name
- [x] The launched flag list is byte-for-byte the baseline; `sampling` carries the seed plus the five flag-sourced values; `seed_pinned` is true — `src/wave_local_ai_v2/server.py:59-93` (`str()` at the call site, constants numeric), `tests/test_server.py:16-53`; `src/wave_local_ai_v2/__init__.py:49`; live row's `sampling` holds all six keys
- [x] Generation facts report stop type, predicted-token count and truncation flag, `None` rather than raising on an absent key — `src/wave_local_ai_v2/timings.py:41-48`; the absent-key path is exercised through `tests/test_cli.py`'s unparseable-repetition case (a body with neither `stop_type` nor `tokens_predicted`)
- [x] One warm-up and N counted requests in order, indices 1..N contiguous, every body carries `cache_prompt: false` and the pinned seed, cooldown N-1 times and never after the last — `src/wave_local_ai_v2/repetitions.py:run_repetition_set`; `tests/test_repetitions.py:29-123`; body assertions in `tests/test_cli.py:test_run_sends_one_warmup_and_five_counted_requests_by_default`
- [x] The written row carries the ordered counted list, the ordered warm-up list and the five protocol fields, and passes the writer gate — `src/wave_local_ai_v2/__init__.py:_run`; `tests/test_cli.py:test_run_appends_one_row_with_fiche_and_metrics`; live row carries all of them

### Phase 2 — Aggregation and the extended row contract

- [x] Known sets give known median/mean/sample-sd, even N takes the two middle values, peak is the maximum, N<2 raises — `src/wave_local_ai_v2/aggregation.py:median,mean,sample_sd,peak`; `tests/test_aggregation.py:17-54`
- [x] Every field in the aggregation label map exists on a written row, and a measurement cannot be added to the metric tuples without a label — `src/wave_local_ai_v2/aggregation.py:AGGREGATION_LABELS`; live row carries all eight declared fields; the reverse direction (a label with no required field) is now guarded by `tests/test_row_contract.py:test_every_declared_measurement_is_a_required_runtime_field`, added for finding 4
- [x] Five differing repetitions give hand-computed medians, each with mean and sd, and the memory figures are the maxima — `tests/test_cli.py:test_run_aggregates_five_differing_repetitions_into_medians_and_peaks` (peaks are 3005.0 / 500_000_005, the counted maxima, not the warm-up and not the last sample)
- [x] A row with `repetitions_n` below 2, a mismatched repetition list, or a drifted aggregation map is refused and nothing is written — `src/wave_local_ai_v2/row_contract.py:_validate_runtime_repetition_structure`; `tests/test_row_contract.py:135-190`

### Phase 3 — A failed repetition fails the row

- [x] Blank, unparseable and `exceed_context_size_error` each produce their own reason from the quality taxonomy; the token cap produces no failure — `src/wave_local_ai_v2/repetitions.py:_run_one` (reasons imported from `scoring.py`, not redefined); `tests/test_repetitions.py:151-233`
- [x] A failure at repetition 3 of 5 stops the run there and a failing warm-up fails with index 0 and no retry — `tests/test_repetitions.py:236-280` asserts `send.call_count == 3` and `== 1`
- [x] The run exits non-zero, prints exactly one stderr line naming index and reason with no traceback, and the results file is byte-identical — exit code and byte-identity held from the start; the single-line half was false in a real run and is now fixed (finding 3): `server.running_server` takes `quiet_exceptions`, `_run` passes `(RepetitionFailure,)`, and `tests/test_server.py:test_running_server_stays_silent_for_a_quiet_exception` asserts it against the real context manager rather than a mock

### Phase 4 — Live validation, docs, changelog, memory

- [x] One real row with `repetitions_n` 5 and five raw repetitions; the Evidence table filled from it; the median and its delta recorded; repetition 1's position stated — verified figure by figure against `aidd_docs/results/runtime.jsonl` run `e85c505d1bac46019da2f6704acd101b`, see Verification below
- [x] Changelog, `cli.md` and `docs/setup.md` each describe the repetition-set shape and none still describes a single request — `CHANGELOG.md:35-62`; `aidd_docs/memory/cli.md:7-15`; `docs/setup.md:210-218`
- [x] No file under `src/`, `docs/`, `aidd_docs/memory/` or `README.md` still asserts the harness sends one request, and the reverted-warm-up note records both the old failure and the replacement — the reverted-warm-up note was already correct and cites the live check (`src/wave_local_ai_v2/__init__.py`, the block inside `_run`); the `FIXED_PROMPT` rationale was the outstanding grep hit and is now rewritten (finding 1). Re-running the mandated grep over `src/`, `docs/`, `aidd_docs/memory/` and `README.md` returns no surviving claim

## Findings

<!-- Fix column states what was applied, since the severity gate has these fixed in-branch with no second review. -->

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | functional | 4 | `src/wave_local_ai_v2/__init__.py:56-62` | The `FIXED_PROMPT` rationale still called 255.9/259.3 tok/s "the harness's honest ceiling for 'one fixed prompt, one fresh server, one real request'" and still said the harness "accepts the cold-start cost rather than adding slot-management complexity to hide it". Both were false: a warm-up runs on every invocation and the live median `prompt_tok_per_s` is 272.08. Phase-4 task 3.2's grep names this exact string. | Fixed. The block's tail now marks 255.9/259.3 as the pre-protocol single-request ceiling, names the warm-up plus `cache_prompt: False` mechanism that replaced the cold-start acceptance, cites the 272.08 median with its phase-4 source, and keeps the prompt-length rationale (overhead amortization) that is still true. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/__init__.py:252-253`, `src/wave_local_ai_v2/repetitions.py:125-127` | `raise_for_status()` was skipped for *every* HTTP 400, but only `error.type == "exceed_context_size_error"` is classified. Any other 400 body has no `content`, so it fell through to the blank-content check and was reported as `repetition N failed: empty` — a wrong reason on the one code path whose purpose is naming failures correctly, with the server's own message discarded. | Fixed. `_is_exceed_context_refusal` in `__init__.py` tolerates the 400 only when the body actually carries that `error.type`; a non-JSON body returns False too. Every other status raises as before. `repetitions.EXCEED_CONTEXT_ERROR_TYPE` is now public so both sides read one string. Two tests added: a non-context 400 and a 400 whose body is not JSON both surface the `HTTPError` and never the word `empty`. |
| 🟡 | functional | 3 | `src/wave_local_ai_v2/server.py:197-203` | "Exactly one stderr line" held only under the test's stub. `running_server`'s `except Exception` fires on a `RepetitionFailure` raised inside its body and printed `llama-server stderr tail:` plus up to 2000 bytes before re-raising. `tests/test_cli.py` asserted `err.strip().count("\n") == 0` against a MagicMock context manager, so the assertion could not fail whatever the real code did. | Fixed. The dump is diagnostics for a failed *server*, not a failed generation: `running_server` gained a `quiet_exceptions` parameter, `_run` passes `(RepetitionFailure,)`, and `tests/test_server.py` now asserts both directions (dump for a server failure, silence for a quiet one) against the real context manager. |
| 🟡 | code | 2 | `src/wave_local_ai_v2/row_contract.py:179-182` | The comment asserted "Every field named in `MEASUREMENT_FIELDS` is also in `REQUIRED_FIELDS` (checked above)". Nothing checked it — the missing-field pass only checks `REQUIRED_FIELDS`. Adding a labelled measurement without the matching required field would publish a declaration the row need not back, which is what phase-2 task 4.2 asked to prevent. The existing `test_aggregation_map_naming_a_field_the_row_does_not_carry_is_refused` passes on set inequality, not row membership. | Fixed. `test_every_declared_measurement_is_a_required_runtime_field` asserts `aggregation.MEASUREMENT_FIELDS - REQUIRED_FIELDS["runtime"]` is empty, and the comment now points at that guard instead of claiming an unperformed check. |
| 🟡 | fit | 2 | `src/wave_local_ai_v2/aggregation.py:30,37`, `src/wave_local_ai_v2/repetitions.py:138` | `gpu_draw_w` was published under `peak_over_counted_repetitions`, but each repetition contributes exactly one NVML sample, read after the completion returns — decode has already stopped. A maximum over five post-generation instants (live row: 41.5 W) is not the run's peak power draw, and a client-facing reader would take it as one. `vram_used_mib` and `process_rss_bytes` are allocation-level and stable across a repetition, so the same label is honest for them. | Fixed. `gpu_draw_w` is labelled `max_post_completion_sample_over_counted_repetitions`; the two allocation-level channels keep `peak_over_counted_repetitions`. The sampling instant is stated in `aggregation.py`'s label comment and in `repetitions._run_one`, and `tests/test_aggregation.py` pins the distinction. No measured value changes, so the phase-4 live run does not need repeating. |
| 🟢 | rot | 1 | `src/wave_local_ai_v2/__init__.py:263-282` | `run_repetition_set` returns `(warmups, counted)` but is called twice with one half zeroed (`count=0`, then `warmup_count=0`), so half of each return is discarded. The signature is never used as designed. | Filed to tech-debt: split into `run_warmups` / `run_counted`, or say in the docstring that the energy window forces two calls. |
| 🟢 | rot | 2 | `src/wave_local_ai_v2/aggregation.py:16` | `RepetitionResult` is imported at runtime for a type annotation only, so `row_contract` now transitively pulls `repetitions` → `scoring`, `gpu` and `timings` (psutil) into every importer, `quality_cli` included. | Filed to tech-debt: move the import under `if TYPE_CHECKING:`. |
| 🟢 | code-health | 3 | `src/wave_local_ai_v2/__init__.py:212` | `MissingTimingsError` is unreachable in `main()`'s caught tuple: `parse_timings` is now called only inside `repetitions._run_one`, which converts it to `RepetitionFailure`. | Filed to tech-debt: drop it, or keep it with a comment saying it guards a future direct caller. |
| 🟢 | code-health | 1 | `src/wave_local_ai_v2/timings.py:37` | `GenerationFacts.truncated` is parsed and never read or published, so a `truncated: true` completion is invisible on the row and in the raw list. | Filed to tech-debt: record it on `RepetitionResult`, or drop it and say why the flag is not consulted. |
| 🟢 | conform | 4 | `docs/setup.md:210-218` | "roughly 5x a single request's time plus 50s of cooldown" undercounts: a default run issues six requests (one warm-up plus five counted), and the live session ran ~113 s against a ~10.5 s request. | Filed to tech-debt: say six requests, or "~6x a single request plus 50 s of cooldown". |
| 🟢 | fit | 4 | `src/wave_local_ai_v2/repetitions.py:67-80` | `seed_pinned: true` cannot be falsified from `runtime.jsonl`: no repetition persists `content` or a content hash, which phase-4's Evidence row concedes, leaving the reproduction claim resting on an out-of-band probe with no artifact in the repo. | Filed to tech-debt: record a `content_sha256` per repetition so two runs can be diffed from the store alone. |
| 🟢 | conform | 4 | `aidd_docs/results/README.md:12-25` | The section does not note that the two curated rows predate `SCHEMA_VERSION` "2" and the repetition protocol, though the file already applies that discipline to `run_id` / `captured_at` at `:54-59`. A reader comparing them field-by-field to a fresh row meets an unexplained shape mismatch. | Filed to tech-debt: add the schema bump to the "deliberately absent" section; regeneration stays with order 19. |
| 🟢 | standards | 4 | `CHANGELOG.md:46` | "a `exceed_context_size_error`" — should be "an". | Filed to tech-debt: fix the article. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (15/15) — 13/15 before this pass's fixes     |
| Files checked | `src/wave_local_ai_v2/{__init__,repetitions,aggregation,row_contract,server,settings,timings}.py`, `tests/{test_repetitions,test_aggregation,test_row_contract,test_cli,test_server,test_settings}.py`, `.env.example`, `CHANGELOG.md`, `docs/setup.md`, `aidd_docs/memory/cli.md`, `aidd_docs/results/runtime.jsonl`, `aidd_docs/results/runtime-reference.jsonl` |
| Unchecked     | none — Phase 3 criterion 3 and Phase 4 criterion 3 were unchecked and are tagged `fixed` (findings 3 and 1) |
| Unplanned     | Phase-1's architecture projection puts the `cache_prompt`/seed body assertions in `tests/test_repetitions.py`, but the module never builds the body, so they live in `tests/test_cli.py` — a sound deviation, the projection is what is stale; phase-4's Evidence is sourced from the first of the two live rows (`e85c505d`, named in the note) rather than the last (`af4246c7`) |
| Gate          | `pytest` 212 passed, coverage 98.33%; `ruff check`, `ruff format --check`, `mypy src/ scripts/` all clean, after the fixes |

**Live-run cross-check** — phase-4's Evidence table against `aidd_docs/results/runtime.jsonl`:

| Figure | Phase-4 claims | Store holds | Agrees |
| ------ | -------------- | ----------- | ------ |
| `gen_tok_per_s` raw 1..5 | 25.4259, 25.4859, 24.8657, 25.7128, 25.4396 | 25.4259395, 25.4859232, 24.8656861, 25.7127910, 25.4395585 | yes |
| `gen_tok_per_s` median / mean / sd | 25.4396 / 25.3860 / 0.3130 | 25.43955851 / 25.38597968 / 0.31303641 | yes |
| Delta vs curated 26.046 | -0.606, inside ±1.5 | reference row 1 is 26.046254456; 25.4396 - 26.0463 = -0.6067 | yes |
| Repetition 1 vs 2..5 | rep 1 mid-pack, rep 3 lowest | rep 1 = 25.4259 is 2nd lowest of 5 and above the mean; rep 3 = 24.8657 is the lowest | yes, and the second run corroborates: its rep 1 (25.510) is the highest of five |
| `ttft_ms` median / mean / sd | 5476.425 / 5487.0722 / 49.5585 | 5476.425 / 5487.0722 / 49.55852545 | yes |
| `prompt_tok_per_s` median / mean / sd | 272.0753 / 271.5650 / 2.4448 | 272.07530460 / 271.56503035 / 2.44484629 | yes |
| `vram_used_mib` peak | 4548.68, constant across the 5 counted and the warm-up | 4548.67578125 on all six repetitions | yes |
| `process_rss_bytes` peak | 15,225,712,640 (rep 1) | 15225712640, and it is the maximum of the five | yes |
| `energy_kwh` | 0.00259323, `measured_nvml` | 0.0025932300018300567, `measured_nvml` | yes |
| Wall clock | 52.531 s over the 5 counted; session ~113 s | `wall_clock_s` 52.53100000000268; reps sum to 52.531; warm-up 10.547 + 50 s cooldown + 52.531 = 113.08 | yes |
| Reference rows | curated 26.046 and 25.484 | `runtime-reference.jsonl`: 26.046254456, 25.483652638 | yes |

Not recorded in the Evidence table: `gpu_draw_w` 41.548 (phase-4 task 1.3 asks for two peaks, and the row publishes three). Finding 5 covers what that third figure actually measures; its label changed after the live run, no measured value did.
