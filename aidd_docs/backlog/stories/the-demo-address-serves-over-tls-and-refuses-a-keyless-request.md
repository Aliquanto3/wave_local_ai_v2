---
type: story
status: ready
source: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
depends_on: aidd_docs/backlog/stories/the-browser-opens-on-the-list-of-runs-behind-its-own-gate.md
order: 5
---

# Story: The demo address serves over TLS and refuses a keyless request

**As** a consultant running the demo from one machine and presenting from another
**I want** the service to bind where I configure it, serve over TLS, take the key once in the browser, and refuse a request without it in a way I can show a client
**So that** the second laptop reaches the pitch and nothing else on the network does

## Acceptance

- PRD AC "the service binds only to a configured address over TLS": the bind address is configuration and defaults to loopback; TLS terminates at the service with a self-signed certificate it can generate or a certificate the operator provides.
- PRD AC "a request carrying a valid API key from a second machine is answered, a request without a valid key is rejected, and no request from outside loopback is served without a key": enforced on every `/api/*` route. Order 1 shipped the startup refusal and the non-loopback gate; this story is where the rule is exercised against a real second machine rather than against a test client.
- PRD AC "the key is read from the environment, never written to the repo or logs, and the service refuses to start without one": the key value appears in no log line, no error message, no response body and no tracked file, `.env.example` included, which carries the variable name and never a value. Verified by searching a real run's output for the value, not by asserting that the code never logs it.
- The browser asks for the key once, holds it in `sessionStorage` for the session only, and never writes it to disk. Closing the tab ends its custody; a refusal clears it and returns to the prompt.
- **What a refusal looks like to a person.** A keyless or wrong-key browser gets a named screen the consultant can show a client — not a stack trace, not a blank page, not a silent hang. The refusal states that a key is required and nothing else: no path, no store location, no key fragment, no hint whether the key was absent or wrong.
- CORS stays configured and restricted to the single dashboard origin, as defence in depth. The epic's single-origin decision means it is never the access mechanism, and this story does not let it become one.
- The configurable store path refuses to resolve outside its configured root, so a path parameter can never read a file the operator did not point the service at.
- The `security-review` skill is run over the branch before merge, scoped to this demo's threat model as the epic fixes it — key handling and leakage, TLS configuration, bind address, CORS, traversal on the configurable store path, and what a refusal discloses — and not against the public-internet model the PRD's Non-Goals exclude. Every finding is fixed or recorded with the reason it was accepted.
- The service stays read-only under all of the above: adding a credential adds no writer.

## Code it changes

- `src/wave_local_ai_v2/settings.py` — bind host and port, certificate and key paths, the certificate-generation switch, and the API key, read from the environment with no default value.
- `src/wave_local_ai_v2/service.py` — TLS on the ASGI server, the per-request key dependency across `/api/*`, the refusal response shape, the restricted CORS origin, and the store-path root check.
- `frontend/src/api-client.ts` — the `X-API-Key` header on every request, and the single place a 401 is turned into the refusal state.
- `frontend/src/views/key/` (new) — the one-time key prompt and the refusal screen.
- `docs/demo.md` (new) — the operator path: generate a key, choose the bind address, obtain or generate the certificate, start the service.
- `.env.example` — the variable name, with no value.

## Tests it needs

- `tests/test_service.py` — a non-loopback request without a key is refused; with a wrong key is refused with the identical body, so the response cannot distinguish absent from wrong; with the right key is answered; the refusal body carries no path, no store location and no key fragment; a store path resolving outside the configured root is refused; TLS is configured from the provided certificate and the service refuses to start with a certificate path that does not exist.
- A log-capture test asserting the key value appears in no emitted record across startup, a served request and a refused one.
- `frontend/src/views/key/*.test.tsx` — the prompt appears when no key is held; a submitted key is used for the next request; a 401 clears `sessionStorage` and returns to the prompt with the named message; the key never reaches `localStorage`.
- `tests/test_settings.py` — the API key has no default and the certificate paths are configuration, so no value ships in the repo.

## Evidence it publishes

- The `security-review` report for this branch, filed with the delivery task, with each finding's resolution.
- A captured run's full output alongside a search for the key value returning nothing — the epic's second success check, done as the check states it, by searching the output rather than by reading the middleware.

## Cancellation

n/a — not cancelled.
