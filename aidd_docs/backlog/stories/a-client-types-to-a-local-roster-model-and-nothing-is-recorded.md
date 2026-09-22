---
type: story
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
depends_on: aidd_docs/backlog/stories/a-run-started-from-the-browser-streams-until-its-row-lands.md
order: 9
---

# Story: A client types to a local roster model, and nothing is recorded

**As** a consultant letting a client try a local model during the pitch
**I want** the client to type a prompt to a roster model through the browser and watch it answer
**So that** they judge its speed and answers first-hand, without that exchange ever being mistaken for a benchmark result

## Acceptance

- PRD AC "every screen of it carries the label 'playground — nothing here is a benchmark row'": the exact string, rendered by one label component on every playground screen, including its empty, loading and refusal states.
- PRD AC "a request without a valid API key is refused": every playground route requires the key, loopback included, as the console does.
- **Behind demo mode too.** Starting a playground model launches a llama-server process and loads a model into memory; that is the same class of action the console gates, so the playground is refused while `SERVICE_DEMO_MODE` is off. This goes beyond the PRD's playground criterion and is this story's decision.
- PRD AC "a local exchange is proxied through the service to the local llama-server under the selected roster entry and its chat template":
  - the roster entry is chosen from the enumerated roster ids, never typed;
  - the service starts llama-server for that entry through `server.build_flags` and `server.start_server`, the same flags a benchmark run launches it with, on the loopback address and port `server.py` already fixes, so llama-server is never reachable from the second machine;
  - the exchange goes to `/v1/chat/completions`, rendered through the model's own template, with the thinking policy chosen from the two declared values and sent through `local_client`'s one spelling of it; the policy in force is shown beside every answer;
  - the answer streams as it is generated, which is how a client judges speed first-hand. No tokens-per-second or latency figure is shown: any number on this screen would read as a measurement.
- **One llama-server, one owner.** The playground takes the occupancy lock order 8 introduced. While the playground holds a model, a run request is refused naming the playground session; while a run holds the lock, the playground is refused naming the run. Two reasons, both checked: `server.start_server` refuses when port 8080 is already taken, and a runtime figure measured beside a loaded playground model would describe a different machine state from the one its fiche records. The playground releases the model on an explicit stop, on a model switch and on service shutdown.
- **The typed text is only ever message content.** It goes as JSON content to the loopback llama-server and nowhere else: never into an argument, an environment variable, a path or a log line. Its length and the answer's `max_tokens` are capped by settings, so a pasted document cannot hold the demo machine.
- PRD AC "no playground exchange is written to any store, result file or log line, nor appears in any benchmark view": the conversation lives in the browser's memory only and is gone on reload; it is not put in session or local storage. The playground module imports no row writer and opens no file for writing.

## Security posture

Key required on every playground route, loopback included. Demo mode off by default and required here. The only browser-supplied values that reach a process are a roster id and a thinking policy, each checked against its enumerated set; the typed text reaches llama-server as message content only. llama-server stays bound to loopback. One llama-server owner at a time, shared with the console. No prompt or answer in any log, file or store. Covered by the epic's pre-merge security review.

## Code it changes

- `src/wave_local_ai_v2/playground.py` (new) — the model lifecycle under the shared lock, and the proxy to the chat endpoint.
- `src/wave_local_ai_v2/demo_console.py` — the occupancy lock generalised to name either holder.
- `src/wave_local_ai_v2/service.py` — start, stop and chat routes on the key-always, demo-mode router.
- `src/wave_local_ai_v2/settings.py` — the prompt length and `max_tokens` caps.
- `frontend/src/views/playground/` (new) and `frontend/src/labels/PlaygroundLabel.tsx` (new).
- `frontend/src/App.tsx` — the playground entry, shown only with demo mode on.

## Tests it needs

- `tests/test_playground.py` — refused without the key from loopback, refused with demo mode off, refused on an unknown roster id or policy with no process started; the lock refuses a run while the playground holds it and the playground while a run does, each naming the holder; the model is released on stop, switch and shutdown; the request sent to a stub llama-server carries the entry's policy spelling and the typed text as content only; an over-cap prompt is refused.
- A no-persistence test: an exchange through the stub leaves every store, the fiche registry and the captured log output byte-identical, and the prompt string appears in none of them.
- `frontend/src/views/playground/*.test.tsx` (vitest) — the label on every state, the policy shown beside each answer, no speed figure rendered, the conversation gone after remount.

## Plan shape

At most four phases: (1) the generalised lock and the playground model lifecycle; (2) the streamed chat proxy; (3) the screen and its label; (4) the no-persistence tests and the second-machine evidence.

## Evidence it publishes

- `aidd-dev:11-browser-qa` videos from the second laptop: a model started, a prompt answered with the label on screen, a run request refused while the playground holds the model, keyless refused.
- A search of the service's output and every store for the prompt used in the video, returning nothing.

## Cancellation

n/a — not cancelled.
