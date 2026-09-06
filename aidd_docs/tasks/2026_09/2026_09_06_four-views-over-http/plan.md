---
objective: "The four views the PRD names answer over HTTP from one read-only service, every field a row does not carry is reported as a named absence, and the API key is required at startup and enforced on every non-loopback `/api/*` request."
status: in-progress
---

# Plan: The four views answer over HTTP, and every absence is named

## Overview

| Field      | Value                                                                              |
| ---------- | ---------------------------------------------------------------------------------- |
| **Goal**   | A read-only HTTP service over the two stores: four routes, three named absence reasons, an unreadable count, and a key gate that refuses to start without a key. |
| **Source** | `aidd_docs/backlog/stories/the-four-views-answer-over-http-and-name-every-absence.md` (epic: `aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md`) |

## Phases

| #   | Phase                                              | File                         |
| --- | -------------------------------------------------- | ---------------------------- |
| 1   | The floor-aware read path and the service's settings | [`phase-1.md`](./phase-1.md) |
| 2   | The read model: four views, named absences          | [`phase-2.md`](./phase-2.md) |
| 3   | The service: four routes, the key gate, the entry   | [`phase-3.md`](./phase-3.md) |
| 4   | The bundle proof, the evidence and the docs         | [`phase-4.md`](./phase-4.md) |

## Resources

| Source                                                                 | Verified                                                                                                                                                    |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `https://pypi.org/pypi/fastapi/json`                                    | Latest `0.141.1`, `requires_python >=3.10`. Base deps are `starlette>=0.46.0`, `pydantic>=2.9.0`, `typing-extensions`, `typing-inspection`, `annotated-doc` — no `[standard]` extra needed, and `httpx` is an extra we take in the dev group instead. |
| `https://pypi.org/pypi/uvicorn/json`                                    | Latest `0.52.4`, `requires_python >=3.10`. Base deps `click>=7.0`, `h11>=0.8`. Plain `uvicorn` (not `uvicorn[standard]`) is enough for HTTP/1.1 loopback serving. |
| `https://pypi.org/pypi/httpx/json`                                      | Latest `0.28.1`, base deps `anyio`, `certifi`, `httpcore`, `idna`. Dev-group only — it is what `starlette.testclient.TestClient` requires.                     |
| `https://raw.githubusercontent.com/encode/starlette/master/starlette/testclient.py` | `TestClient.__init__` accepts `client: tuple[str, int] = ("testclient", 50000)` and assigns it straight to `scope["client"]`. So the loopback-vs-non-loopback gate is drivable from tests with `TestClient(app, client=("127.0.0.1", 12345))` and `client=("192.168.1.50", 12345)` — no monkeypatching. The default `("testclient", 50000)` is **not** a parsable IP, which is why the gate must fail closed on an unparsable host. |
| `https://raw.githubusercontent.com/encode/starlette/master/starlette/routing.py` | `Route.matches` returns `Match.PARTIAL` when the path matches but the method is not in `self.methods`, and `Route.handle` then raises `HTTPException(405)` with an `Allow` header. So `POST`/`PUT`/`PATCH`/`DELETE` answer 405 with no code of ours — provided the key check does not run before routing (see the Decisions). |

## Decisions

| Decision                                                                                                                    | Why                                                                                                                                                                                                                                                                                                                     |
| --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GET /api/runs` answers with two separately named collections, `runtime_runs` and `quality_runs`, never one array.            | "No route composes the two stores" has to hold for the index too. Two named collections make the response un-mergeable by shape rather than by convention, and the two CLIs mint independent `run_id`s, so a single sorted list would invite a join that has no meaning. Each collection carries its own `unreadable` count. |
| `GET /api/runs/{run_id}/energy` requires an explicit `?store=runtime\|quality`.                                              | The energy fields live on both row kinds. Probing one store then the other would make the service read both to answer one view, and would leave a response ambiguous about which store a number came from. An explicit parameter is the honest form; a missing or unrecognised value is a named 422, not a guess.           |
| The API-key check is an `APIRouter`-level dependency on `/api`, not HTTP middleware.                                          | Middleware runs before routing, so a non-loopback `POST /api/runs` would answer 401 and the story's "every non-`GET` method answers 405" would be false off-loopback. A router dependency runs after the router has already resolved the method, so 405 stays 405 for every client and the key still gates every `/api/*` route that exists. The cost, stated rather than hidden: an unknown `/api/...` path answers 404 without the key check, disclosing route absence and nothing else. |
| The service loads its own `ServiceSettings`, not `load_settings()`.                                                          | `load_settings` requires `SLM_MODELS_DIR` and `LLAMA_SERVER_PATH` to exist on disk, so a read-only reader of published artifacts would refuse to start on a machine with no local model install. `settings.fiche_registry_dir_from_env` already set this precedent for `fiche_validator`; this follows it, reading the same `DEFAULT_*` constants so the two forms can never resolve a path differently. |
| A view's field list is *partitioned* against `row_contract`, not merely checked as a subset.                                 | The story forbids a hand-maintained parallel list that can drift. `read_model` declares, per row kind, the fields it renders plus the fields it explicitly does not; a test asserts the union equals the contract's own set exactly. A field added to the contract then fails the build until it is either rendered or deliberately declared unrendered — the drift is caught at the contract, not discovered as a silently absent column on a pitch screen. |
