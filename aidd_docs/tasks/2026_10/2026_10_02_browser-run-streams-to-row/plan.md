---
objective: "A key-holding browser, with demo mode on, starts one runtime or quality run under a declared run profile of the service's own machine, watches its merged output stream live, and sees the row the CLI alone wrote, or its exit status and error line."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A run started from the browser streams until its row lands

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | A demo console (`demo_console.py`, `/api/console/*`) gated by an unconditional key and `SERVICE_DEMO_MODE`, launching the unchanged CLIs from constants plus validated identifiers (kind, suite, roster entry, run profile), one run at a time, streamed as NDJSON, ending with the row read back through the existing view routes |
| **Source** | `aidd_docs/backlog/stories/a-run-started-from-the-browser-streams-until-its-row-lands.md`; parent epic `the-pitch-runs-from-a-browser-and-only-with-the-key.md`; re-applied from the unmerged branch `feat/browser-console-run-streams-to-row` (plan `aidd_docs/tasks/2026_09/2026_09_24_browser-console-run-streams-to-row/` on that branch) |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Demo-mode setting, declared-set options route (profiles included), occupancy lock | [`phase-1.md`](./phase-1.md) |
| 2   | Launcher, `run_id` announcement, graceful stop, stream route | [`phase-2.md`](./phase-2.md) |
| 3   | Row read-back and failure reporting | [`phase-3.md`](./phase-3.md) |
| 4   | Console panel; second-machine evidence (pending, operator) | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `uv.lock` | `h11` present; neither `websockets` nor `wsproto`. A `StreamingResponse` needs no new dependency. |
| Old branch plan (2026-09-24), live experiment on this laptop | `CTRL_BREAK_EVENT` to a Windows child without a `SIGBREAK` handler kills it with no `finally`; with a handler raising, cleanup runs once the current blocking call returns. |
| `settings.load_settings` / `python-dotenv` | Every CLI calls `load_dotenv()`, which sets a variable only when it is absent from the environment: a popped `SERVICE_API_KEY` would be restored from a `.env` holding it. |
| `profiles.declared_profiles`, `profiles.profile_id_for`, `settings.require_run_profile` | A profile is `<entry>@<machine>/<mode>`; every declared (machine, mode) is a profile of every entry; the CLI refuses an undeclared machine, an unknown mode and `gpu` on a GPU-less machine itself. |

## Decisions

| Decision | Why |
| -------- | --- |
| Transport: chunked `StreamingResponse` of NDJSON (`{"line": ...}` per output line, then one `{"final": ...}`), read with `fetch()` + `ReadableStream`. | No new dependency; `fetch` sends `X-API-Key` in a header, which neither `EventSource` nor `WebSocket` can; the key never enters a URL. Re-applied from the old branch. |
| The service names its own machine through `MACHINE_ID` (new optional `ServiceSettings.machine_id`, read raw, never required by the read routes). The console offers, per roster entry, only the declared profiles whose machine is that one; a run request naming another machine is refused (422) before any spawn. With `MACHINE_ID` unset or undeclared, the options route reports the absence by name and every run request is refused. | A run executes on the machine in front of the client; a row written under another machine's profile would claim hardware it never ran on. The read service stays startable without `MACHINE_ID`. |
| The request carries `kind`, `suite` (quality only), `roster_entry_id`, `machine_id`, `compute_mode`: identifiers only. The profile is `profiles.profile_id_for(entry, machine, mode)` and must be a member of `declared_profiles` for that entry; the child's `ROSTER_ENTRY_ID`, `MACHINE_ID` and `COMPUTE_MODE` are set from these validated values only. | A profile id carries `@` and `/`, a path character, so it cannot itself pass the identifier allow-list; its three parts can, and rebuild it exactly. |
| Profile set offered = declared profiles, not filtered by declared-value completeness or GPU presence. A profile with a `not_yet_declared` value, or `gpu` on a GPU-less machine, is refused by the CLI and that refusal is streamed as-is. | Story: "the console adds no second check that could disagree with the CLI's." |
| Child env = the service's own env with `SERVICE_API_KEY` set to the empty string (not merely popped), plus `PYTHONUNBUFFERED=1`, `PYTHONIOENCODING=utf-8` and the three validated ids. `CAMPAIGN_ID`, `QUALITY_PROVIDERS` and the operator overrides are inherited unchanged. | Blanking keeps the CLI's own `load_dotenv()` from restoring the key from a `.env` (it never overrides a present variable). Everything else is the operator's configuration of this machine, which the story leaves as the service's own; the CLI's own campaign check applies. |
| Suites come from `suite_registry.registered_ids()` (the old branch read `quality_cli._SUITES`, since removed). The quality child runs its default `--prompt-variant` (baseline); the variant is not a console choice. | "Imported, not copied": the registry is now what `--suite` resolves against. The story enumerates kind, suite, entry and profile only. |
| CLIs install a graceful-stop handler (`SIGBREAK` on Windows, `SIGTERM` elsewhere) raising `server.StopRequested` (a `BaseException`), and `_spawn_and_wait_ready` stops its llama-server on any exception during the readiness wait. The console child gets its own process group; `stop_child` sends the signal, waits `GRACE_S` = 25 s, then kills. | Re-applied from the old branch: without the handler the child dies with no `finally` and orphans llama-server; the grace covers the 10 s cooldown plus `SHUTDOWN_GRACE_S`. |
| Each CLI prints its `run_id` (flushed) as its first stdout line, right after `require_run_profile`, before any other output. An early refusal (settings, profile) prints only its `error:` line. | One-line change per CLI; writes nothing into any row. |
| Occupancy lock: module-level holder under a `threading.Lock`; released by the pump thread's `finally` on every exit, and on launch failure. Holder carries kind, suite, roster entry, profile id, start time, `run_id` once announced. | Re-applied, plus the profile. |
| Console key gate ignores loopback; it runs before the demo-mode check so a keyless request cannot probe demo mode. Demo mode off answers 403 naming `SERVICE_DEMO_MODE`; the dashboard shows "demo mode is off on this machine". | PRD AC taken literally; re-applied. |
| Review round 1: the serving entry runs uvicorn's single-process path on a `uvicorn.Server` subclass whose `shutdown` stops the console child (in a worker thread) before uvicorn's own drain, plus a `finally` that stops it on any other exit, a forced one included. The panel re-reads the options route every 3 s while a holder is shown, so Start re-enables when that run ends. | uvicorn 0.52.4's `shutdown` waits on open connections before the lifespan event, and `force_exit` skips that event: a lifespan-only stop let an open stream hold the service and orphan the child. |
| `SERVICE_DEMO_MODE`: unset = off; exactly `true` / `false` parse; anything else refuses service start. | Re-applied. |
| Second-machine browser-QA videos and the side-by-side row are pending (operator, second laptop). A loopback live check ran on this laptop (`evidence/live-check.txt`): demo off 403, keyless loopback 401, another machine 422, a real `qwen3-0.6b-q8` quality run streamed line by line over 9 s (`evidence/stream.txt`) until its row read back, a second request 409 naming the holder, the key found in no log, stream or row. | Night run: no second machine, owner asleep. |
