---
objective: "With a dedicated playground setting naming a provider and its pinned model, the playground offers that cloud subject in the same selector as the roster entries, sends a typed prompt to it only through the existing provider client under its pacing and retry rules, states on the send control before every send that the text leaves the machine for that provider, and refuses it while unconfigured or while a console run holds the occupancy lock; nothing is recorded and the provider key never leaves the service."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: The playground reaches a cloud subject only when configured, and says so first

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | `PLAYGROUND_CLOUD_SUBJECT` (`<provider>:<model>`, unset by default) enables one cloud subject in the playground; selecting it takes the shared occupancy lock as a cloud playground holder; each send goes through `mistral_client`/`google_client` under `retry.Pacer` + `retry.call_with_retry`; a provider failure ends the exchange with an error naming the provider; the send control names the provider on every send |
| **Source** | `aidd_docs/backlog/stories/the-playground-reaches-a-cloud-subject-only-when-configured-and-says-so-first.md`; parent epic `the-pitch-runs-from-a-browser-and-only-with-the-key.md`; dependency `a-client-types-to-a-local-roster-model-and-nothing-is-recorded.md` (committed at `a12092c`) |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | The setting and the cloud path behind the chat interface | [`phase-1.md`](./phase-1.md) |
| 2   | The selector and the per-send statement | [`phase-2.md`](./phase-2.md) |
| 3   | Refusal tests and the evidence | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The setting is `PLAYGROUND_CLOUD_SUBJECT=<provider>:<model>`, provider `mistral` or `google`, and the model must equal the provider client's pinned `MODEL`; anything else is a `SettingsError` at service start. | The story asks the setting to name provider and model, and to go through the existing client. Both clients pin one dated model id and take no model argument; accepting another id would either be ignored silently or need new HTTP code. Pinning also keeps the playground's cloud subject the one the benchmark rows describe. |
| The provider key is read (`MISTRAL_API_KEY`/`GOOGLE_API_KEY`) only when the setting names that provider, and an empty key with the setting present refuses service start. A key alone enables nothing. | "A key held to send the repo's own suite items is not consent to send text a client typed." Failing at start rather than per send keeps a misconfiguration off the pitch screen. |
| Selecting the cloud subject is a session (`POST /api/playground/session` with `{"cloud_subject": "<provider>"}`) that takes the one occupancy lock as a `CloudPlaygroundHolder`; each send also checks the session still holds it. | "Same interface": the same Start/Switch/Stop flow and 409 refusals. Holding the lock also stops a quality run from starting while the playground can spend the same provider's quota, the other half of the story's "not during a run" rationale. |
| One `Pacer` per session at the provider's benchmark pacing interval; a fresh `RetryBudget` per send sized `derived_retry_budget(1, ...)` from the same `CLOUD_RETRY_*` settings; base delay 1 s as the quality CLI. Sends are serialised by a session lock. | "Its retry and pacing rules apply" without importing `quality_cli`, which imports the row writer the playground must not. |
| The cloud sampler restates the quality CLI's `CLOUD_SAMPLING`/`GOOGLE_SAMPLING` values; a test asserts they are equal. | Same reason: no import of the CLI module, but no silent drift either. |
| The cloud answer is not streamed: the client returns the whole completion, sent as one `delta`, then the `final` event. A failure ends with `final.error` naming the provider and the status or failure class only, never the client's exception text (which embeds the response body). Empty text from the provider is an error, not an answer. | The existing clients are non-streaming; the browser already handles a one-chunk answer. The client's own messages quote `response.text`, which must not reach the browser. |
| The thinking policy is not sent to the provider (neither client sends a thinking control); the `final` event reports `thinking_policy: "not_sent"` for a cloud exchange. | Reporting the browser's choice back would claim a control that was never applied. |
| The per-send statement is the send button's own label: `Send to <Provider>: the text leaves this machine`; a local subject's button reads `Send`. It is rendered on every send, never a dialog. | "On the send control itself ... for every send ... not a browser dialog." |
| Review follow-ups: each playground retry wait is capped at `PLAYGROUND_MAX_RETRY_WAIT_S` (10 s), and a provider asking for longer is refused naming it with no wait; any exception outside the named set still ends the stream with a `final` error naming provider and class only; the thinking selector is disabled while the cloud subject is selected; the evidence script patches `settings.load_dotenv` to a no-op. | A batch can wait a minute, a client watching the screen cannot; a stream with no `final` would leave the exchange spinning; the selector would offer a control that is never sent; the script must never pick up a real key from a `.env`. |
| Browser QA video is not produced in this unattended run. | No paid call (owner decision D2) and no browser session; reported pending. |
