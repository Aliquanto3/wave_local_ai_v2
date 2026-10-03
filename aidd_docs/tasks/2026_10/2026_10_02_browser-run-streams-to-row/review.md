# Review: A run started from the browser streams until its row lands

## Round 1

VERDICT: CHANGES-REQUIRED

Gates: `uv run pytest -q` => `2612 passed, 2 warnings in 188.98s`, coverage 98.40% (demo_console 99%, service 97%). ruff check / ruff format --check / mypy clean; detect-secrets on every changed and untracked file clean. Frontend offline: `vitest run` 139 passed (29 files), `tsc -b --noEmit` exit 0, eslint 0 errors.

Blocking findings
1. The service does not stop a running child when a browser is following its stream. `stop_child` runs only from the lifespan shutdown (`service.py` `create_app.lifespan`), and `uvicorn.run` (`service.py:501`) runs that only after open connections close. The panel always follows the stream, so Ctrl+C waits for the whole run to finish. A second Ctrl+C sets `force_exit`, which skips lifespan shutdown entirely. The child then keeps running headless: on Windows it sits in its own process group, so the console Ctrl+C never reaches it. Reproduced with uvicorn 0.52.4: `should_exit` set at 1.27s, lifespan shutdown at 6.14s, only after the stream had ended. `test_shutting_the_service_down_stops_a_running_child` never opens a stream. Expected fix: stop the console child before uvicorn waits on connections, and on force-exit too (for example a short `timeout_graceful_shutdown` plus a `uvicorn.Server.shutdown` override or a `finally` in `main`). Add a real-uvicorn test that stops the service while a stream is open.

Non-blocking findings
1. `QUALITY_PROVIDERS` defaults to `local,mistral,google` (`settings.py:88`) and is inherited. If the service env holds `MISTRAL_API_KEY` or `GOOGLE_API_KEY` and leaves `QUALITY_PROVIDERS` unset, one browser click makes paid cloud calls, and nothing on screen says so. This is within the story's letter (child env = service env minus the key), and story order 10 expects console runs to spend provider quota. Owner decision: pin `QUALITY_PROVIDERS=local` for console children, or show the enabled cloud providers in the options route and the panel. `CAMPAIGN_ID` inheritance is fine: the CLI's own campaign check refuses, and the refusal is streamed.
2. A keyless POST with malformed JSON gets FastAPI's 422 `json_invalid` before the key gate runs. FastAPI parses the body (`fastapi/routing.py:439-465`) before `solve_dependencies` (`:481`). No process is spawned and demo mode is not exposed, but "key first" does not hold literally. Fix: read the raw body inside the handler, after the gate.
3. Key blanking is proven only against a mocked `Popen` (`test_demo_console.py:311`). I verified it with a real Windows child and python-dotenv 1.2.3: blanked => `''`, popped => `'from-dotenv-file'`. Worth a real-child test.
4. When a browser disconnects, the threadpool thread in `ConsoleRun.follow` stays blocked in `Condition.wait()` (`demo_console.py:427`) until the next line or the exit. Reattaching many times to a long run can use up the anyio pool. Low risk, since every console route needs the key.
5. The panel never clears a holder it learned from a 409 (`ConsolePanel.tsx`), so Start stays disabled until a reload. The no-writer scan checks the two modules directly; the package `__init__` already imports `results` transitively, and that was true before this change.

Acceptance
- Key on every console route, loopback too: proven (`test_the_console_refuses_a_keyless_loopback_client`, `..._wrong_key_from_loopback`, `test_the_run_routes_are_keyed_and_demo_gated_too`). Caveat: non-blocking 2.
- `SERVICE_DEMO_MODE` strict, off by default, 403 naming it, panel text: proven (`test_settings` unset / `true`,`false` / `maybe`,`True`,`1`,`yes`,`""`; `test_the_console_is_a_403_naming_the_variable...`; ConsolePanel "states that demo mode is off").
- One-run lock, holder named with run_id, no queue, released on success, non-zero exit and crash: proven (`test_a_second_run_is_refused_naming_the_first_and_spawns_nothing`, `test_the_announced_run_id_is_recorded_on_the_holder`, `test_a_crashing_child_releases...`, `test_the_console_is_released_exactly_once_per_run`, `test_a_launch_failure_frees_the_console...`). Release on shutdown: in-process, but see blocking 1.
- Declared sets, identifiers only, refusals with no spawn, argv from constants without a shell, env minus the key, profile mapping with another machine => 422: proven (`test_a_request_outside_the_declared_sets_is_refused_before_any_spawn` covers extra field, path, `;`, `$()`, `--help`, non-string and missing fields; `test_a_profile_of_another_declared_machine_is_refused_naming_both`; the `command_for` tests; `test_the_child_is_launched_without_a_shell_and_without_the_service_key`). The profiles story is done, so the declared-absence branch is moot. Unset `MACHINE_ID` is refused and named.
- Live, unbuffered output; key sent in a header, never in a URL: proven (`test_lines_arrive_as_the_child_writes_them_not_at_exit`, `test_the_stream_reaches_a_real_http_client_line_by_line`, `client.test.ts` header assertions).
- run_id as the first line, row read back through the view routes, exit status and `error:` line on failure: proven (`test_cli` / `test_quality_cli` changes, `test_a_landed_rows_final_event_is_the_existing_view_route_payload`, `test_a_failed_runs_final_event...`, the ConsolePanel stream and failure tests).
- No write path: proven structurally (`test_no_console_module_reaches_a_writer_or_opens_a_file_for_writing` plus its self-check).
- Port already held => the CLI's own refusal: proven by absence (`demo_console.py` has no port check).
- Stopping the service stops the child, graceful then kill: not met (blocking 1). `stop_child` itself is proven by its three tests and `test_a_stopped_cli_still_tears_down_its_llama_server`.
- Selects only, no free text: proven (ConsolePanel "offers only selects...").

Evidence vs done: the second-laptop browser-QA videos, the side-by-side row comparison and the key search are listed under "Evidence it publishes", not under Acceptance. They are pending on the operator. A loopback live check exists (`evidence/live-check.txt`; key found: False; the run used `QUALITY_PROVIDERS=local`, so no paid call). The story is not done while blocking 1 stands. Once it is fixed, the acceptance can be fully proven by tests. Keep the story out of `done` until the operator's second-laptop evidence is recorded, since the story names it as its published evidence.

## Round 2

VERDICT: PASS

Gates: `uv run pytest -q` => `2616 passed, 2 warnings in 203.93s`, coverage 98.40%. ruff check, ruff format --check and mypy are clean. Frontend offline: vitest 140 passed in each of three consecutive runs, `tsc -b --noEmit` exit 0, eslint 0 errors.

Round 1 blocking 1: fixed.
- `_ConsoleStoppingServer.shutdown` (`service.py`) stops the console child in a worker thread before uvicorn drains connections, so the open stream ends and the drain completes.
- The `finally` in `_serve` stops it again on a force exit or on any exception (`test_the_serve_entry_stops_a_child_on_a_forced_exit_too`).
- When the server never started, `_serve` exits with `STARTUP_FAILURE` (3), as `uvicorn.run` does (`test_the_serve_entry_exits_with_uvicorns_startup_failure_code`).
- `test_stopping_the_service_with_a_stream_open_stops_the_child_first` runs a real uvicorn with a stream open. I re-ran it with `shutdown` reverted to `uvicorn.Server.shutdown` through a pytest plugin, without editing any file: it FAILS (`1 failed ... in 50.71s`). So it bites.
- `_serve` reproduces `uvicorn.run`'s single-process path in 0.52.4: same `Config(**kwargs)`; `config.load()` happens inside `Server._serve`; `KeyboardInterrupt` is swallowed; startup failure exits with 3. Dropped: the reload and workers branches and the UDS cleanup, none of which this service uses. host, port, `proxy_headers=False` and the TLS cert and key are still passed, and asserted (`test_the_serve_entry_prints_the_address_and_floor...`).
- The five serve-entry tests only swap `uvicorn.run` for `_serve` in their patch; every assertion is unchanged.

Round 1 non-blocking 3: fixed. `test_a_dotenv_holding_the_key_cannot_restore_it_in_a_real_child` goes through the real `launch` and `child_env` with a `.env` that sets the key; the child prints `''`.

Holder poll (`ConsolePanel.tsx`): runs every 3 s only while a holder is shown. The effect depends on the boolean `held`, so changing from one holder to another does not restart the timer, and the interval is cleared as soon as the holder is null or the panel unmounts. At most one request every 3 s, so no storm. The test holds back the poll's answer with a deferred promise, so its result does not depend on timing; three runs were green.

Non-blocking
1. A failed poll is swallowed (`ConsolePanel.tsx`, the poll's `.catch`). After a 401, `apiFetch` has already cleared the stored key but the key gate is never told, so polling continues at 401 every 3 s. Route `UnauthorizedError` to `reportUnauthorized()`, as the initial load does.
2. Polls can overlap when a request takes longer than 3 s (`setInterval` does not wait for the previous one). Harmless at this rate.
3. No test asserts that polling stops once the holder is cleared. The effect's cleanup makes it true by construction.
4. Round 1 non-blocking items 1 (paid cloud call through the inherited `QUALITY_PROVIDERS`, owner decision), 2 (malformed-JSON 422 before the key gate) and 4 (a reader thread stays blocked after a browser disconnect) still stand.

Acceptance: every line is now proven by code and tests, including "stopping the service terminates a running child". The browser-QA videos from the second laptop, the side-by-side rows and the key search are "Evidence it publishes", not acceptance lines. They are pending on the operator, so the status stays `ready` until they land.
