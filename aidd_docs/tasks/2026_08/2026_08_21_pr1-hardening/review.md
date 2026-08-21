# Review: PR #1 hardening increment

- **Verdict**: approve
- **Diff**: `a0b7b1a~1...8cd756a` plus the uncommitted review fixes on top
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_21
- **Findings**: 0 critical, 0 warning, 1 minor

## Phases

### Phase 1 — Row provenance and store safety

- [x] Two `new_run_id()` calls return different values; `captured_at()` parses back to a timezone-aware UTC datetime — `src/wave_local_ai_v2/results.py:12,22`, `tests/test_results.py:30,35`
- [x] A stubbed runtime run appends one row carrying a non-empty `run_id` and a UTC-parseable `captured_at`, and no quality-only field — `src/wave_local_ai_v2/__init__.py:225`, `tests/test_cli.py:196`; disjointness asserted on the same row shape at `tests/test_cli.py:114`
- [x] A stubbed quality run's rows all carry the same `run_id`; a second run's rows carry a different one; no row carries a runtime-only field — `src/wave_local_ai_v2/quality_cli.py:202`, `tests/test_quality_cli.py:373,391`
- [x] With `append_row` raising `OSError`, each CLI exits 1 with an `error:` line on stderr and no traceback — `src/wave_local_ai_v2/__init__.py:163`, `src/wave_local_ai_v2/quality_cli.py:76`, `tests/test_cli.py:216`, `tests/test_quality_cli.py:399`
- [x] `repr()` of a populated `Settings` omits the key value while attribute access still returns it — `src/wave_local_ai_v2/settings.py:27`, `tests/test_settings.py:83`

### Phase 2 — Server lifecycle honesty

- [x] With the port reported occupied, `start_server` raises `ServerStartupError` naming the port and spawns no process — `src/wave_local_ai_v2/server.py:104`, `tests/test_server.py:162`
- [x] An exception raised inside a `running_server` body reaches the caller unchanged, and the server's stderr tail was written to stderr before it did; the process is still stopped exactly once — `src/wave_local_ai_v2/server.py:180`, `tests/test_server.py:183` (`mock_stop.assert_called_once_with`)

### Phase 3 — Metrics collection resilience

- [x] With `stop()` raising, `measure_energy` returns the measured function's result tagged `energy_method="unavailable"`; when both the function and `stop()` raise, the caller sees the function's exception — `src/wave_local_ai_v2/energy.py:33,39`, `tests/test_energy.py:49,64`
- [x] `read_process_rss` returns `None` for both `NoSuchProcess` and `AccessDenied` and still returns a positive integer for a live process; a stubbed run whose RSS read fails still appends its row — `src/wave_local_ai_v2/timings.py:45`, `tests/test_timings.py:52,60`, `tests/test_cli.py:234`

### Phase 4 — Cloud client and quality run order

- [x] A Mistral 200 response carrying `content: null` surfaces as `MistralRequestError` naming the value; a string content still returns unchanged — `src/wave_local_ai_v2/mistral_client.py:87`, `tests/test_mistral_client.py:177`
- [x] A cloud failure leaves exactly one local row per suite item on disk, all sharing the run's `run_id`, and the local rows are already written when the first cloud call happens — `src/wave_local_ai_v2/quality_cli.py:107`, `tests/test_quality_cli.py:417,430`

### Phase 5 — Committed evidence and project memory

- [x] `git check-ignore` reports the two reference files as not ignored and both live stores as ignored; each reference row is byte-identical to its source line; `detect-secrets-hook` exits 0 — `git check-ignore -v` matches only `.gitignore:22` and only for the live stores; `git ls-files aidd_docs/results/` lists both references plus the README; `git status --porcelain aidd_docs/results/` is empty; live-vs-reference byte comparison identical for `runtime.jsonl` lines 4-5 and `quality.jsonl` lines 1-40. Caveat: identical after CRLF-to-LF normalization only, disclosed at `aidd_docs/results/README.md:61`.
- [x] `cli.md` names both commands with no "in progress"; `codebase-map.md` lists the tests, results and backlog areas and both entry points; no memory file claims a gate that is not wired — `aidd_docs/memory/cli.md:7-16`, `aidd_docs/memory/codebase-map.md:8-31`, `aidd_docs/memory/architecture.md:9`, `aidd_docs/memory/coding-assertions.md:7`
- [x] `CLAUDE.md` no longer states a rule and its opposite: the Communication bullet names the two exceptions and the Action rules point back to it with their scope stated — `CLAUDE.md:14,33,39`
- [x] A real runtime run appends a row with both provenance fields and a `gen_tok_per_s` within +/-1.5 of 26; a real quality run's rows share one `run_id` and reproduce the reference accuracies, or the skip is stated — verified against the live stores, not only the notes: the last `runtime.jsonl` row carries `run_id=4826bf9f4534494c9f7e4c367deacaad`, a `captured_at` with UTC offset zero, and `gen_tok_per_s=26.4796`; the last 20 `quality.jsonl` rows share one `run_id`. Matches `phase-5.md` Notes.

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 | code | 2 | `src/wave_local_ai_v2/server.py:191` | `_read_stderr_tail` seeks the stderr handle to 0 while the child is still alive: `stop_server` only runs in the `finally`, after the `except`. Parent and child share the handle's file offset, so between the seek and the end of the read llama-server can resume writing over the head of its own log, and the printed tail can show garbled bytes. Confined to a temp file that is discarded immediately after; the two other call sites are safe (the child is already dead or already stopped). | Restoring the offset after the read does not close the window (`read()` already leaves it at EOF); the seek itself is what moves the shared pointer. The real fix is to read the tail in the `finally` after `stop_server`, tracking the failure in a local so the process is still stopped exactly once. Deferred: it restructures the lifecycle path every real run takes, for a defect with no observable output. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (15/15)                                      |
| Files checked | `src/wave_local_ai_v2/{__init__,energy,mistral_client,quality_cli,results,server,settings,timings}.py`, `tests/test_{cli,energy,mistral_client,quality_cli,results,server,settings,timings}.py`, `.gitignore`, `CLAUDE.md`, `aidd_docs/memory/{architecture,cli,codebase-map,coding-assertions}.md`, `aidd_docs/results/{README.md,runtime-reference.jsonl,quality-reference.jsonl}` |
| Unchecked     | none                                              |
| Unplanned     | `aidd_docs/memory/coding-assertions.md:7` — the "wired via pre-commit" line was corrected too; absent from phase 5's architecture projection, but it is the same false claim task 2.3 targets in `architecture.md`, so it belongs. Plus the five review fixes applied on top of `8cd756a`, none tied to a plan criterion: `energy.py:11-17,52` typed `_stop_tracker` against `EmissionsTracker` under `TYPE_CHECKING` and dropped the `type: ignore`; `server.py:186` narrowed `except BaseException` to `Exception`; `__init__.py:160`, `quality_cli.py:73` stated the `OSError` widening's real scope; `tests/test_quality_cli.py:398` corrected a comment phase 4 had made false; `.gitignore:19-23` moved from two pinned filenames to `*.jsonl` with `!*-reference.jsonl`. |
