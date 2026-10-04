# Review: A client types to a local roster model, and nothing is recorded

## Round 1

Scope: uncommitted working tree on top of `36e8307` (14 modified files, `playground.py`, `tests/test_playground.py`, `frontend/src/views/playground/`, `PlaygroundLabel.tsx`, `holder.ts`, this task folder).

VERDICT: PASS

### Gates run by the reviewer

- `uv run --offline pytest -q`: `2661 passed, 2 warnings in 194.89s`, coverage 98.42% (floor 95%).
- `uv run ruff check .`: all checks passed. `ruff format --check .`: 730 files already formatted. `mypy src/ scripts/`: no issues in 70 files.
- `frontend/`: `npm test` 31 files, 149 tests passed; `npm run typecheck` clean; `npm run lint` 0 errors (1 pre-existing warning in `KeyGate.tsx`).
- Empirical check (inline script, nothing written to the repo): real `_ConsoleStoppingServer`, a fake SSE child standing in for llama-server, a playground chat stream open, then `should_exit`. Server thread exited in 0.14 s, the stream ended with a `final` carrying `error: "the local model stopped answering (ChunkedEncodingError)"`, the child had exited, and the lock holder was `None`.

### Acceptance, line by line

| Acceptance | Status | Evidence |
| --- | --- | --- |
| Exact label on every playground screen, incl. empty, loading, refusal | proven | `PlaygroundLabel.tsx:2`; rendered once above every state in `PlaygroundPanel.tsx` (section root); vitest "carries the label while loading / on a refusal / when empty", and in the streaming test |
| Key required on every route, loopback included | proven | router-level `_demo_gates` (`service.py`, `_playground_router`); `test_every_playground_route_refuses_a_keyless_loopback_client` over all four routes; live check 401 |
| Behind demo mode | proven | same router dependency; `test_the_playground_is_refused_with_demo_mode_off` (403, no process) |
| Roster entry from enumerated ids only | proven | `playground.validate_entry`; `test_a_start_outside_the_roster_ids_is_refused_with_no_process` (unknown id, `--model`, int, extra `flags` field, non-object) |
| Launch via `build_flags` + `start_server`, loopback and fixed port | proven | `playground.py:216-231`; `test_a_start_launches_the_benchmark_flags_and_holds_the_lock` asserts the flag list equals `build_flags` and `--host 127.0.0.1` |
| `/v1/chat/completions`, own template, policy from the two values via `local_client`'s spelling | proven | `prepare_chat` uses `local_client.thinking_kwargs`; `test_the_typed_text_is_only_message_content_under_the_entrys_spelling`; caveat (b) below |
| Policy shown beside every answer | proven | `ExchangeView` "(thinking: …)"; vitest "streams an answer with the policy in force beside it" |
| Answer streams; no speed or latency figure | proven | NDJSON proxy, `timings`/`usage` dropped (`stream_chat`); vitest `SPEED_FIGURE` regex; live check `grep -c timings` = 0 |
| One lock, both directions, each naming the holder | proven | `test_a_run_is_refused_naming_the_playground_while_it_holds_the_model`, `test_the_playground_is_refused_naming_the_run_while_a_run_holds_the_lock`; live check 409 |
| Released on stop, switch, shutdown | proven | `test_a_stop_releases_the_model_and_the_lock`, `test_a_switch_stops_the_first_model_before_starting_the_second`, `test_service_shutdown_releases_the_model`, `test_the_shutdown_backstop_stops_the_playground_model`; stream-open shutdown checked empirically above (no dedicated test) |
| Typed text only message content; prompt and `max_tokens` capped by settings | proven | content-only assertion in the spelling test; `test_a_chat_outside_its_caps_or_sets_is_refused_before_anything_is_sent`; settings cap tests (default, read, below-one refusal) |
| Nothing recorded; browser memory only | proven (this machine) | structural `test_no_demo_module_reaches_a_writer_or_opens_a_file_for_writing` now includes `playground.py`; `test_an_exchange_leaves_every_store_registry_and_log_untouched`; vitest remount test; live marker search `quokka-amber-7731` returned 0 |
| Second-laptop `aidd-dev:11-browser-qa` videos | pending (operator) | not producible here |
| Marker search for the prompt used in the videos | pending (operator) | not producible here |

Story status: code-done; it stays `ready` until the second-laptop videos and their marker search are published.

### Implementer decisions

- (a) No `preflight.enforce`: correct, it appends a refusal record. Not required by any acceptance line, but the methodology intent ("a machine that cannot hold a model refuses it without loading it") is reachable without writing: `preflight.observe` + `preflight.first_failure` are pure (`preflight.py:89`, `:140`). Today the only machine with resolvable profiles (`laptop-mobile-gpu`) meets every entry's declared RAM minimum and VRAM minimums are `not_yet_declared`, so no live harm. Recommended, non-blocking.
- (b) No `verify_thinking_control`: the label states the policy sent, not one verified. Mitigated: `reasoning_content` is forwarded and rendered as "reasoning:", so a template ignoring the switch would show visible reasoning under "(thinking: disabled)" rather than hide it; all four roster entries are Qwen3 with `enable_thinking`, and the live check shows 0 reasoning lines under `disabled`. A one-time render-only probe at session start would make the label a checked claim. Non-blocking.
- (c) Compute mode server-side (gpu profile else cpu_only, no operator override): consistent with "only a roster id and a policy reach a process"; the profile id is shown. No substitution on a profile error (503).
- (d) Single-turn: within the acceptance (judge speed and answers). The screen lists past exchanges without saying the model does not see them.

### Blocking findings

None.

### Non-blocking findings

1. `playground.py:232`: only `ServerStartupError`/`OSError` release the lock; any other exception out of `start_server` leaves the `PlaygroundHolder` installed with no session handle to stop it, blocking the console until restart. Release on `BaseException` and re-raise.
2. `playground.py:216`: add the non-recording minimum check (`observe` + `first_failure`) before `build_flags`, refused as a 503 naming the requirement (decision a).
3. `server.py:206`: the playground's llama-server keeps writing its stderr to an unlinked temp file for the session's life; the live marker search covered service output and stores, not that stream. Confirm the pinned build's default verbosity logs no prompt text (or note it in the evidence).
4. `PlaygroundPanel.tsx`: state on screen that each prompt is answered on its own (decision d), so a client's follow-up question is not read as the model forgetting.
5. `playground.py:260`: a chat refused while a run holds the lock answers "no playground model is loaded" with `holder: null` instead of naming the run; the start route does name it.
