---
type: story
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
order: 8
---

# Story: A run started from the browser streams until its row lands

**As** a consultant running a demo in front of a client
**I want** to start a runtime or quality run from the browser and let the client watch its output until the row appears
**So that** the client sees a number produced on the machine in front of them rather than taking a pre-computed table on trust

## Acceptance

- PRD AC "a run request without a valid API key is refused": every console route requires the key, **from loopback too**. This is stricter than the four read views, which serve loopback without a key; the PRD criterion for the console is unconditional and is taken literally.
- PRD AC "a run request is refused whenever the demo-mode setting is off, which is its default": a new `SERVICE_DEMO_MODE` setting, off when unset. Only an explicit enabling value turns it on; any other value refuses service start rather than being read as off or on. With demo mode off, every console route answers a refusal naming the setting, and the panel shows "demo mode is off on this machine" rather than a broken control.
- PRD AC "given a run in progress, a second request is refused naming the run in progress rather than queued": one in-process occupancy lock. A second request is answered with the kind, suite, roster entry, start time and, once known, the `run_id` of the run holding it. Nothing is queued. The lock is released on every child exit — success, failure, crash — and on service shutdown.
- PRD AC "launches only the runtime or the quality CLI, with a suite, roster entry and run profile chosen from the declared sets, never a free-form command or argument":
  - a `GET` options route lists the declared sets: the two kinds, the suites from `quality_cli`'s own suite table (imported, not copied), the roster entry ids from the roster file, and the named run profiles once `each-model-machine-and-mode-runs-under-its-own-named-profile` ships them — until then the profile set is reported as a declared absence naming that story, and no profile is accepted;
  - the run request carries identifiers only; each is checked for membership in its declared set before anything is spawned, and any other field, any unknown value, or any value carrying a path or shell character is refused with no process started;
  - the command is built from constants plus validated identifiers, run without a shell: the quality CLI receives `--suite`; the runtime CLI, which takes no arguments, receives the roster entry through `ROSTER_ENTRY_ID` in the child's environment, set from the validated id only;
  - the child's environment is the service's own minus `SERVICE_API_KEY`: the key never reaches a process that did not need it.
- PRD AC "the browser receives the CLI's output lines as they are emitted": stdout and stderr merged, the child run unbuffered (a piped Python stdout is block-buffered, so without this every line would arrive at exit and nothing would be watchable). The transport is picked in the plan against two facts already checked: `uv.lock` carries `h11` but neither `websockets` nor `wsproto`, so a WebSocket needs a new pinned dependency through the CI epic's gate while a streamed HTTP response needs none; and neither the browser's `EventSource` nor its `WebSocket` constructor can send the `X-API-Key` header, while putting the key in a query string would write it into the access log. Whatever the plan picks, the key travels in the header and never in a URL.
- PRD AC "then the row once the CLI has written it, or the CLI's exit status and failure reason when it does not": each CLI announces its `run_id` as its first output line (a one-line change to each CLI, which writes nothing new into any row). On exit 0 the panel reads that `run_id` back through the existing quality or runtime view route and renders the row with every label those views carry. On a non-zero exit the panel shows the exit status and the CLI's own `error:` line, and no row is shown or invented.
- PRD AC "every row is written by the CLI alone — the service has no write path to either store, verified by there being none rather than by convention": the console module and the service import no row writer and open no store for writing; a row produced this way is an ordinary CLI row, with no field recording that it was launched from a browser.
- A runtime run launched while a llama-server already holds its port fails with the CLI's own refusal, streamed as-is: the console adds no second check that could disagree with the CLI's.
- Stopping the service terminates a running child through the same graceful-then-kill path `server.stop_server` uses, so the CLI's own teardown stops its llama-server. Cancelling a run from the browser is not in this story; the PRD's non-goal is a job runner, and one more control in front of a client is one more thing to misclick.
- The panel offers only selection controls over the declared sets. There is no free-text input anywhere in it.

## Security posture

Key required on every console route, loopback included. Demo mode off by default, strictly parsed. Subprocess arguments are never user-supplied strings: the browser picks from enumerated kinds, suites, roster entries and profiles, and the service rebuilds the command from constants. No shell. The API key is stripped from the child's environment and never placed in a URL. One run at a time. No write path from the service to either store. Reviewed with the epic's pre-merge security review, with subprocess spawning added to its scope.

## Code it changes

- `src/wave_local_ai_v2/settings.py` — `SERVICE_DEMO_MODE`, strictly parsed, default off.
- `src/wave_local_ai_v2/demo_console.py` (new) — the declared sets, request validation, the occupancy lock, the command table and the launcher.
- `src/wave_local_ai_v2/service.py` — the options, run and stream routes on a router that requires the key unconditionally and refuses when demo mode is off.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — announce `run_id` as the first output line.
- `frontend/src/views/console/` (new) — the run panel: selections, the live output, then the row through the existing quality or runtime view.
- `frontend/src/api/client.ts` — a streaming read that sends the key header.
- `frontend/src/App.tsx` — the console entry, shown only when the options route reports demo mode on.

## Tests it needs

- `tests/test_settings.py` — demo mode off when unset, on only for the enabling value, start refused on any other value.
- `tests/test_demo_console.py` — every refusal is reached with no process spawned: unknown kind, suite, roster entry or profile; an extra field; a path or shell character in a value; demo mode off; a keyless request from loopback. A second request while the lock is held is refused naming the holder. The lock is released after a success, a non-zero exit and a crash. The child environment carries no `SERVICE_API_KEY`. Streaming order and timing are asserted against a stub child (`sys.executable -c ...`) that prints, sleeps and prints, so a buffered stream fails the test.
- `tests/test_service.py` — the console routes are refused without the key from loopback and off it; a structural test that no service-side module references `results.append_row` or opens a store path for writing.
- `frontend/src/views/console/*.test.tsx` (vitest) — demo-off state, the refusal naming a run in progress, lines appended as they arrive, the row rendered on success with its labels, the exit status and error line on failure, and no text input in the panel.

## Plan shape

At most four phases: (1) the demo-mode setting, the declared-set options route and the occupancy lock; (2) the launcher, the `run_id` announcement and the stream route; (3) the row read-back and failure reporting; (4) the panel and the second-machine evidence.

## Evidence it publishes

- `aidd-dev:11-browser-qa` videos from the second laptop: demo mode off refused, keyless refused, a real run streamed until its row appears, a second request refused while it runs.
- The row that run wrote, set beside a terminal-launched row of the same kind: the same key set, no extra field.
- A search of the service's and the child's output for the key's value, returning nothing.

## Cancellation

n/a — not cancelled.
