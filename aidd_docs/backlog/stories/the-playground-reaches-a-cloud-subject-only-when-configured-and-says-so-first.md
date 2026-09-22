---
type: story
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
depends_on: aidd_docs/backlog/stories/a-client-types-to-a-local-roster-model-and-nothing-is-recorded.md
order: 10
---

# Story: The playground reaches a cloud subject only when configured, and says so first

**As** a consultant letting a client compare a local model with a cloud one first-hand
**I want** the playground to offer a configured cloud subject through the same screen, and to say before each send that the text will leave the machine
**So that** the client can try the comparison the pitch argues about, and never sends text off the machine without being told

## Acceptance

- PRD AC "a cloud subject is selectable only when one is configured": a dedicated playground setting names the provider and model, and is unset by default. Holding a `MISTRAL_API_KEY` or `GOOGLE_API_KEY` for the benchmark does not enable it: a key held to send the repo's own suite items is not consent to send text a client typed. Unset, the subject is absent from the selector and the route refuses it.
- PRD AC "the playground states before each send to it that the text will leave the machine for that provider": the statement is on the send control itself and names the provider, for every send, not once per session. It is not a browser dialog.
- PRD Non-Goals, "the one opt-in this release carries is the playground's cloud subject": this is the only path in the release where typed text leaves the machine, and no local exchange ever reaches a cloud client — asserted, not assumed.
- **The same interface.** The cloud subject sits in the same selector as the local roster entries, under the same label "playground — nothing here is a benchmark row", with the same key and demo-mode refusals and the same no-persistence rule as order 9.
- The call goes through the existing provider client, so its retry and pacing rules apply. A rate limit or provider failure is shown as a refusal naming the provider, never as an empty answer.
- **Not during a run.** The cloud subject is refused while a console run holds the occupancy lock: a quality run spending the same provider's quota could be pushed into a partial run by a playground call.
- The provider key stays on the service: it never reaches the browser, a response body or a log line.

## Security posture

Key and demo mode required, as order 9. Egress only when the operator has configured it and only after the screen has said so, per send. The provider key never leaves the service. No typed text or answer is stored or logged. The egress path is added to the epic's pre-merge security review scope.

## Code it changes

- `src/wave_local_ai_v2/settings.py` — the playground cloud-subject setting, unset by default.
- `src/wave_local_ai_v2/playground.py` — the cloud subject behind the same chat interface, through the existing provider client.
- `frontend/src/views/playground/` — the subject in the selector, and the per-send statement on the send control.

## Tests it needs

- `tests/test_playground.py` — with the setting unset, the cloud subject is absent from the options and refused by the route, and the provider client is never called, even with the provider's benchmark key present; a local exchange never calls a cloud client; the cloud subject is refused while a run holds the lock; a provider rate limit surfaces as a named refusal; no response body carries the provider key.
- `frontend/src/views/playground/*.test.tsx` (vitest) — the send control names the provider on every send, and the statement is absent for a local subject.

## Plan shape

At most three phases: (1) the setting and the cloud path behind the chat interface; (2) the selector and the per-send statement; (3) the refusal tests and the evidence.

## Evidence it publishes

- An `aidd-dev:11-browser-qa` video: the cloud subject absent while unconfigured, then present with the statement on its send control once configured.
- A search of the service's output for the provider key's value, returning nothing.

## Cancellation

n/a — not cancelled.
