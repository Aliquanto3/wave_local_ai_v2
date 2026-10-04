# Review: Generated code is scored by its tests in a sandbox, or not run at all

- **Verdict**: changes-requested
- **Diff**: `main...working-tree (uncommitted, schema "30")`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 1 critical, 3 warning, 2 minor

## Phases

### Phase 1 — Sandbox runner, scoring rule, preflight and refusal

- [x] Without docker, the daemon or an image, the preflight refuses in one line and no container is run — `tests/test_code_sandbox.py::test_no_container_runtime_refuses_in_one_line_and_runs_nothing`, `test_an_unreachable_daemon_refuses`, `test_a_missing_image_refuses_and_is_never_pulled`; `tests/test_quality_cli.py::test_a_code_suite_with_no_container_runtime_exits_1_before_any_process`; real host: `evidence/local-run-refusal.txt` (Node image absent => exit 1)
- [x] The docker command has no mount, `--network none`, `--pull never`, memory and pid caps — `src/wave_local_ai_v2/code_sandbox.py:198-240` (argv list, no shell; also `--read-only`, tmpfs-only workdir, `--user 65534:65534`, `--cap-drop ALL`, `no-new-privileges`, `--cpus 1`, no docker socket); `test_the_container_has_no_network_no_mount_and_its_caps`
- [ ] A planted passing generation scores 1; a failing one scores 0 with its reason — gap: a failing generation that exits 0 at import scores 1 (`code_sandbox.py:79-86`, `:98-101`). Reproduced in the real sandbox (local image sha256:11b8a687f7d5): `def f(): return 2` + `sys.exit(0)` / bare `exit()` / `os._exit(0)` => `passed`; Node v22.17.1: `process.exit(0)` in solution.mjs => `node --test` exit 0, `# pass 1`

### Phase 2 — Suite data, snapshot, coverage entry, row contract "30", export docs, per-language read

- [x] The suite resolves gated, both programming languages present, each natural language >= 25% — 24 items, 12 py / 12 js, 8 EN / 8 FR / 8 DE; `tests/test_code_generation_suite.py::test_the_suite_tags_both_languages_and_each_instruction_language`; tests read item by item and are correct and non-trivial (e.g. numeric sort trap js-en-03, accent-free vowel count py-fr-01); licence CC-BY-4.0 / hand_written / contamination_risk false consistent with `suite_gate.HAND_WRITTEN_LICENCE`; tolerance reason says "Provisional"; snapshot `aidd_docs/results/suite-definitions/code-generation-python-javascript@1.json` is a new untracked file
- [x] A code row validates at "30"; one missing part of the block is refused; an untagged language reads as nothing — `row_contract.py` `_validate_code_fields`; `read_model.py:851` `programming_language_score`; `test_code_generation_suite.py:251-267` (`rust` => None, one-language suite => None for the other)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 critical | functional | 1 | `src/wave_local_ai_v2/code_sandbox.py:79-86`, `:98-101` | Verdict trusts the test process exit code alone: a solution that exits 0 at import (`sys.exit(0)`, `exit()`, `os._exit(0)`, `process.exit(0)`) never runs a test and scores 1. Violates acceptance "1 when every one of its tests passes"; the harness comment at :64-66 claims the opposite | Require proof the tests ran: Python runner prints a host-generated nonce (sent in the stdin payload) after the loop and the harness requires rc 0 AND the nonce; Node appends a last `test("<nonce>")` or parses `--test-reporter=tap` and requires that test's `ok` line and `# fail 0`. Add planted exit-0 cases to the fake-docker unit tests and the `CODE_SANDBOX_IT` test |
| 🟡 warning | functional | 2 | `src/wave_local_ai_v2/code_sandbox.py:89-103` | JavaScript harness never executed in a container (no Node image locally, never pulled); Node path proven only by argv shape | Pending operator: load a Node image, run `CODE_SANDBOX_IT` with a JS planted set (add one; the IT test is Python-only) |
| 🟡 warning | functional | 2 | `aidd_docs/results/quality-reference.jsonl` | No local or cloud code batch published; no MoE / tiny dense side-by-side | Pending: Node image on the roster machine (local); owner decision D2 (cloud) |
| 🟡 warning | security | 1 | `src/wave_local_ai_v2/code_sandbox.py:256-265` | Wall clock enforced only by the host client: if the client dies (Ctrl-C, crash) or `docker kill` races container creation, the container runs with no time cap (`--rm` removes it only when it ends) | Add an in-container watchdog (harness child `timeout=`) and follow the kill with `docker rm -f <name>` |
| 🟢 minor | code | 1 | `src/wave_local_ai_v2/code_sandbox.py:47`, `:190` | Images are tags, not digests; the row records the tag, so `python:3.12-slim` names no exact interpreter | Record the resolved image id (`docker image inspect --format {{.Id}}`) in the sandbox block |
| 🟢 minor | fit | 2 | `src/wave_local_ai_v2/use_case_coverage.json` | `exercised` passes the record's own definition (`use_case_coverage.py:7`, a resolvable suite id) and matches precedent (translation is `exercised` with 0 published rows), but epic line 17 reads "exercised by a suite whose rows meet the methodology criteria" and no code row exists | Acceptable while the story stays `ready`; mark done only with the batches published |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 80% (4/5) |
| Files checked | code_sandbox.py, code_generation_suite.py, scoring_rules.py, suite_registry.py, quality_cli.py, row_contract.py, read_model.py, bundle_export.py, use_case_coverage.json, suite_data/code-generation-python-javascript.json, snapshot @1, tests/* in diff, evidence/* |
| Unchecked     | Planted failing generation scores 0 — fix |
| Unplanned     | none |

## Round 2

- **Verdict**: approve (code); story stays `ready` (JS in-container run and batches pending)
- **Date**: 2026_10_03
- **Gates**: `uv run pytest -q` => `2820 passed, 8 skipped, 2 warnings in 200.70s`, coverage 98.49%; ruff check, ruff format --check, mypy clean; `CODE_SANDBOX_IT=1` (local image sha256:11b8a687f7d5, never pulled) `-k "real_sandbox or harness"` => `25 passed`; no `wave-sandbox-` container left

### Phases

- [x] Round 1 critical (exit 0 forges a pass) fixed — `code_sandbox.py:93-110` (Python: rc 0 AND nonce as last stdout line), `:123-136` (Node: appended `test(<nonce>)`, `--test-reporter=tap`, its top-level `ok N - <nonce>` required); reviewer probes in the real sandbox: exit before imports, `atexit(os._exit(0))` after a failing test, a guessed nonce printed, `sys.exit(0)` inside the tested function => all `tests_failed`; Node harness (host, reviewer-authored code): `process.exit(0)` at import / in the function / `exitCode` reset on exit, a forged `ok 2 - <guess>` line => all `tests_failed`; correct code with a debug print => `passed`
- [x] Watchdog + host grace + kill and remove — in-container `timeout_s` (`:103`, `:127`, `:132`), host deadline cap + 15 s (`:309`), `docker kill` then `docker rm -f` (`:314-321`); endless loop and an orphaned background process => `timeout` at 20.5 s, container gone; `test_a_run_the_watchdog_did_not_end_is_a_timeout_and_its_container_removed`
- [x] `image_id` resolved and recorded — `code_sandbox.py:183-205`, container started from the id (`:286`), `row_contract.SANDBOX_FIELDS` includes it (`row_contract.py:849`, checked at `:2235`), export doc `bundle_export.py:905`
- [x] No production path executes generated code on the host — every `subprocess.run` in `code_sandbox.py` (`:191`, `:218`, `:302`, `:315`) invokes the docker binary; the harness strings are only docker arguments; no other `src/` module references them. The host-harness tests (`test_the_python_harness_passes_only_when_every_test_ran`, `test_the_node_harness_...`) run test-authored constant snippets in `tmp_path`, never model output

### Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | code | 1 | `src/wave_local_ai_v2/code_sandbox.py:128`, `:133` | Node `spawnSync` default `maxBuffer` (1 MiB): a correct solution printing 3 MB scored 0 with reason `timeout` in 0.2 s (`t.error` is ENOBUFS, not ETIMEDOUT); wrong reason under Methodology 9 | Report `timeout` only when `error.code === "ETIMEDOUT"`; otherwise `tests_failed` with the error code, or raise `maxBuffer` |
| 🟢 minor | code | 1 | `src/wave_local_ai_v2/code_sandbox.py:98`, `:108-109` | Correct Python code that writes stdout without a trailing newline at import (`sys.stdout.write('dbg')`) or prints from `atexit` scores 0 (`tests_failed`): the nonce is no longer the last line. Safe direction, rare | Print `"\n" + nonce` and search the lines for it after the last test, or pass the nonce through a file/fd the solution does not share |
| 🟡 warning | functional | 2 | `src/wave_local_ai_v2/code_sandbox.py:113-137` | Node harness proven only on host Node v22.17.1; never run inside a Node container (no Node image locally, never pulled) | Pending operator: load a Node image and add a JS planted set to the `CODE_SANDBOX_IT` test |
| 🟡 warning | functional | 2 | `aidd_docs/results/quality-reference.jsonl` | No local or cloud code batch published | Pending: Node image on the roster machine (local); owner decision D2 (cloud) |

### Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (5/5 plan criteria) |
| Files checked | code_sandbox.py, row_contract.py, bundle_export.py, tests/conftest.py, tests/test_code_sandbox.py |
| Unchecked     | none (story acceptance "JS runs in the sandbox" and "batches published" pending, not fix) |
| Unplanned     | none |
