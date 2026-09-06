---
type: story
status: ready
source: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
depends_on: aidd_docs/backlog/stories/the-four-views-answer-over-http-and-name-every-absence.md
order: 2
---

# Story: The browser opens on the list of runs, behind the front-end's own gate

**As** a consultant, and as the client-side developer who judges this repo's engineering
**I want** the service to serve a built dashboard on its own origin, opening on the list of runs, with the first non-Python code in the repo held to a check suite that can refuse a merge
**So that** the pitch starts in a browser rather than a terminal, and the front end does not arrive as the one directory nothing checks

## Acceptance

- PRD AC "a dashboard presents those four views without the viewer touching a terminal": opening the service's root in a browser shows the list of runs — `run_id`, `captured_at`, the suites and models the run covers, and its `release_version` and `commit_sha`.
- Methodology 19: a run whose rows carry `tree_dirty: true` says so in the list. A sha taken from a dirty tree names code that never existed, and the first screen of the pitch is where that is either disclosed or hidden.
- **Single origin, as the epic decided.** The service serves the built bundle and `/api/*` on the same host and port, so the second laptop gets one URL and one certificate. In development, Vite proxies `/api` to the service. CORS is configured and restricted to that one origin, as defence in depth rather than as the access mechanism. `/api` is never shadowed by the static mount, and an unknown non-`/api` path falls back to the bundle's entry document.
- A field the read-model reports absent renders as a named absence, never as a blank cell, a dash, a zero or an em-dash with nothing behind it. The declared-absent contract survives the trip through the browser.
- **The front-end toolchain, owned here.** Vite + React + TypeScript with a committed lockfile and pinned versions, `vitest` for unit tests, ESLint and Prettier for lint and format, and `tsc --noEmit` for types — the same four gates the Python side already runs, in the tools that side has no equivalent of.
- PRD AC "an automated check suite ... runs on the head commit and the platform blocks the merge until it reports success": a `frontend` job in `.github/workflows/ci.yml` installs from the lockfile and runs lint, format check, type check and tests with coverage, and is added to the `required` summary job's `needs` so a front-end failure blocks a merge exactly as a Python failure does. Every action is pinned by commit sha, matching the pins already in that file. Extending the workflow is agreed with `clean-machine-runs-it-and-nothing-reaches-main-unchecked`, which owns the suite; this story adds one job to it and changes no other.
- Front-end line coverage is gated at the same 80% the Python suite is gated at (`--cov-fail-under=80`), so the two halves of the repo are held to one number rather than to a strict half and a lenient one.
- PRD AC "the documented setup steps produce a working benchmark run without undocumented manual fixes": `docs/setup.md` and the README name the front-end prerequisite and the one documented command that produces a served bundle on a fresh machine.
- The epic's open decision — whether the built bundle is committed or built during setup — is taken in this story's first phase together with the fresh-machine story that owns the setup path, and recorded with its reason. The acceptance above holds under either choice; what it refuses is a third state where the demo path needs a step nobody wrote down.

## Code it changes

- `frontend/` (new) — `package.json`, the committed lockfile, `vite.config.ts` (dev proxy for `/api`), `tsconfig.json`, the ESLint and Prettier configs, and `src/` with the app shell, one API client module every view fetches through, and the runs list.
- `src/wave_local_ai_v2/service.py` — the static mount of the built bundle, the entry-document fallback, and the restricted CORS origin.
- `src/wave_local_ai_v2/settings.py` — the bundle directory and the allowed dashboard origin as configured values.
- `.github/workflows/ci.yml` — the `frontend` job, and `required.needs`.
- `.pre-commit-config.yaml` — the front-end lint and format entries, or an explicit recorded reason why they stay CI-only rather than joining the fast gate.
- `.gitignore` — `frontend/node_modules`, and the bundle path per the decision taken above.
- `docs/setup.md`, `README.md`.

## Tests it needs

- `frontend/src/**/*.test.tsx` (vitest, new) — the runs list renders rows from a fixture; a declared absence renders as its named absence rather than as an empty cell; a `tree_dirty` run is marked; a refused or unreachable API response surfaces as a stated message, never as an empty table that reads like "no runs".
- `tests/test_service.py` — the root path serves the bundle's entry document; an unknown non-`/api` path falls back to it; an unknown `/api` path is a 404 from the API and never the entry document, so a mistyped endpoint cannot return HTML that a client parses as data.
- `tests/test_ci_workflow.py` (new) — the `frontend` job is present and is named in `required.needs`, and every `uses:` in the workflow is pinned by commit sha. This is the assertion that silently regresses: a job that stops gating a merge looks exactly like a job that gates one.

## Evidence it publishes

- A CI run on the delivery branch showing the `frontend` job green and `required` depending on it, and a second run with a deliberately failing front-end test showing `required` refusing — the same "each check can fail" proof the CI epic's own stories published.
- A screenshot of the runs list over the live stores, filed with the delivery task, showing a real `commit_sha` and its dirty flag.

## Cancellation

n/a — not cancelled.
