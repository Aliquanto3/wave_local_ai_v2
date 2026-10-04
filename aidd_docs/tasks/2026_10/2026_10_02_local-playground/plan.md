---
objective: "A key-holding browser, with demo mode on, starts one roster model on the service's own machine, sends it a typed prompt under a declared thinking policy and watches the answer stream, while the shared occupancy lock keeps a console run and the playground apart and nothing of the exchange reaches any store, file or log."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A client types to a local roster model, and nothing is recorded

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | A playground (`playground.py`, `/api/playground/*`) behind the console's key-always and demo-mode gates: a roster entry from the enumerated ids is launched through `server.build_flags` + `server.start_server` under the service machine's declared profile, a typed prompt is proxied to `/v1/chat/completions` as message content only and streamed back as NDJSON, under the one occupancy lock the console run already takes |
| **Source** | `aidd_docs/backlog/stories/a-client-types-to-a-local-roster-model-and-nothing-is-recorded.md`; parent epic `the-pitch-runs-from-a-browser-and-only-with-the-key.md`; dependency `a-run-started-from-the-browser-streams-until-its-row-lands.md` (code-done at `36e8307`) |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Generalised lock, settings, playground model lifecycle and routes | [`phase-1.md`](./phase-1.md) |
| 2   | Streamed chat proxy | [`phase-2.md`](./phase-2.md) |
| 3   | Playground screen and its label | [`phase-3.md`](./phase-3.md) |
| 4   | No-persistence proof; live check; second-machine evidence (pending, operator) | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The playground shares `demo_console`'s one occupancy lock; the holder is either a `RunHolder` or a `PlaygroundHolder`, and every 409 carries `holder` with a `session` field (`run` / `playground`). | The story's "one llama-server, one owner": both need port 8080, and a runtime figure measured beside a loaded playground model would describe another machine state. One lock, not two that could disagree. |
| The playground releases the lock only if it is still its own holder (`release_if(holder)`); the console's pump keeps its unconditional `release()`. | A late stop from the playground can never free a lock a run took meanwhile. |
| The compute mode is not browser-supplied: the playground launches the service machine's declared `gpu` profile when one exists, else `cpu_only`, resolved with `profiles.resolve_for_run` and no operator override. | The story limits browser-supplied values to a roster id and a thinking policy. The resolved profile id is shown so the client knows what runs. |
| `ServiceSettings` gains optional `llama_server_path` and `slm_models_dir` (read raw from the same env vars as the CLIs, never required) and two caps, `PLAYGROUND_MAX_PROMPT_CHARS` (default 4000) and `PLAYGROUND_MAX_TOKENS` (default 512). Unset paths make the playground answer 503 naming the variable. | The read service stays startable on a machine without a model install. |
| The declared minimums are checked with `preflight.observe` + `preflight.first_failure`, never `preflight.enforce` (review follow-up). A machine below one is a 503 naming the requirement, with nothing started. | `enforce` appends a refusal record; the playground records nothing, but a model that does not fit must still be refused before any process starts. |
| Single-turn exchanges: each prompt is sent alone (`messages: [{"role": "user", ...}]`); the browser lists past exchanges but does not resend them. | Bounds every request by the prompt cap, keeps the "typed text is only message content" check to one field, and is enough to judge speed and answers. |
| The request carries `messages`, `stream: true`, `max_tokens` and `local_client.thinking_kwargs(...)` only; no sampler values (the server was launched with them) and no `timings` forwarded to the browser. | The same launch flags as a benchmark run; no number on screen that could read as a measurement. |
| `disabled` is not verified with `verify_thinking_control` before each exchange. | That probe guards a published row's claim; the playground publishes nothing and shows the policy it sent. |
| Single-turn is stated on screen (review follow-up). | The listed exchanges are not context the model sees; the client must not read them as a conversation. |
