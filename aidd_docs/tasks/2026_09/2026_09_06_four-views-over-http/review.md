# Review: The four views answer over HTTP, and every absence is named

- **Verdict**: changes-requested
- **Diff**: `main...feat/results-service`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_06
- **Findings**: 1 critical, 3 warning, 3 minor

## Phases

### Phase 1 — The floor-aware read path and the service's settings

- [x] A store mixing `"11"`, `"7"`, `"2"`, a version-less row and a malformed line, read at floor `"7"`, returns the first two rows and three named unreadable entries; no exception escapes — `src/wave_local_ai_v2/results.py:111`, `tests/test_results.py`
- [x] A row at `"10"` is returned at floor `"7"`, not counted unreadable — `src/wave_local_ai_v2/results.py:186` (`_as_schema_int`), `tests/test_results.py`
- [x] `read_rows`, `rows_for_run` and `resume_skip_reason` return what they returned before — untouched in the diff; regression test in `tests/test_results.py`
- [x] `SERVICE_API_KEY` unset raises `SettingsError` naming the variable; set, the settings carry the key, `127.0.0.1`, `8000`, floor `"7"` — `src/wave_local_ai_v2/settings.py:228`
- [x] `repr()` of the settings contains no substring of the key — `src/wave_local_ai_v2/settings.py:203` (`field(repr=False)`)
- [x] `load_service_settings` succeeds with `SLM_MODELS_DIR` and `LLAMA_SERVER_PATH` unset — no `_require_existing_path` call in `load_service_settings`
- [x] `.env.example` names the four `SERVICE_*` variables, carries no real key; `detect-secrets` clean — `.env.example:46`, `pre-commit run --all-files` Passed
- [x] `pytest`, `ruff check`, `ruff format --check`, `mypy src/ scripts/` clean — 915 passed, 96.62% coverage

### Phase 2 — The read model: four views, named absences

- [x] `resolve_field` returns three distinct outcomes; the absent-key case names the row's own `schema_version` — `src/wave_local_ai_v2/read_model.py:108`
- [x] A field added to `row_contract.REQUIRED_FIELDS` fails the partition test naming it — `tests/test_read_model.py:156`, verified by the monkeypatched contract test
- [x] A quality row carrying none of `JUDGED_FIELDS` yields a judge block of absences — `src/wave_local_ai_v2/read_model.py:562`
- [x] A runtime row with `gpu_energy_method` removed yields no `energy_headline` value and names the missing label — `src/wave_local_ai_v2/read_model.py:662`
- [x] An unstored `fiche_hash` yields `pointer_unresolved` naming the hash, never `{}` — `src/wave_local_ai_v2/read_model.py:367`
- [x] A row at `"2"` under floor `"7"` lands in `unreadable` naming `"2"`, no partial entry anywhere — `src/wave_local_ai_v2/results.py:160`
- [x] The two score shapes stay separate, neither shape's fields on the other — `src/wave_local_ai_v2/read_model.py:566`
- [x] `pytest` passes; `mypy` clean with `read_model` fully annotated

### Phase 3 — The service: four routes, the key gate, the entry

- [x] `audit_dependencies.py` reports `no blocking findings`, `waivers: []` unchanged, `uv.lock` pins `fastapi`/`uvicorn`/`httpx` — audit run clean, `docs/dependency-waivers.yml:24`
- [x] Non-loopback `GET /api/runs` without the key answers 401 naming the reason; with the key, 200 and the identical loopback body — `tests/test_service.py:209`, `:231`
- [x] A client host of `"testclient"` is treated as non-loopback and refused — `src/wave_local_ai_v2/service.py:61`, `tests/test_service.py:225`
- [x] No response body, log line or startup line contains the key's value — `tests/test_service.py:254`, `:285`
- [x] Each of the four routes answers its view; no body carries both a quality-only and a runtime-only field — `tests/test_service.py:138`
- [x] `POST`/`PUT`/`PATCH`/`DELETE` answer 405 with `Allow: GET` on all four routes, both client kinds — `tests/test_service.py:171`
- [x] The energy route answers 422 with no `store` or `store=both`, and the view with `store=runtime` — `src/wave_local_ai_v2/service.py:42`, `tests/test_service.py:106`
- [x] A `run_id` absent from the named store answers 404 naming the run and the store — `src/wave_local_ai_v2/service.py:87`
- [x] `SERVICE_API_KEY` unset: the entry returns non-zero, names the variable on stderr, binds no socket — `tests/test_service.py:268`
- [x] Store bytes unchanged after the suite, no file created, every route answers with `append_row` raising — `tests/test_service.py:310`, `:330`
- [x] `pytest` passes above the 80% gate; the four before-commit hooks clean — 96.62%, all four Passed

### Phase 4 — The bundle proof, the evidence and the docs

- [x] All four views answer over the committed bundle at floor `"7"`, every field `"7"` predates reported as `predates_schema` — `tests/test_reference_bundle.py`
- [x] No bundle row yields a `pointer_unresolved` in any view — `tests/test_reference_bundle.py`
- [x] Every row of a `*.schema-1.jsonl` file lands in `unreadable` at floor `"7"` — `tests/test_reference_bundle.py::test_every_row_of_a_superseded_file_lands_in_unreadable`
- [x] `PUBLISHED_BUNDLE_SCHEMA_VERSION` unchanged, no `*-reference*.jsonl` byte touched — diff stat lists no reference store
- [x] Eight bodies filed under `evidence/`, bundle four at `"7"`, live four at `"11"`, capture commands recorded — `evidence/README.md:40`
- [x] No change to `runtime.jsonl` or `quality.jsonl`, neither grew a line — `git status` clean, neither in the diff
- [ ] The memory files describe the service as shipped — `cli.md` states "no proxy header is read", which uvicorn's default `proxy_headers=True` falsifies at run time (see the critical finding). True again once that finding is fixed.
- [x] `pre-commit run --all-files`, `pytest` and `audit_dependencies.py` clean

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | code | 3 | `src/wave_local_ai_v2/service.py:230` | `uvicorn.run` defaults to `proxy_headers=True`, so `ProxyHeadersMiddleware` rewrites `scope["client"]` from `X-Forwarded-For` before the gate reads it. `is_loopback_client`'s docstring ("Reads no proxy header... the peer address is the only input") is false as deployed. Demonstrated against a real uvicorn server: a loopback client sending `X-Forwarded-For: 192.168.1.50` is answered 401 instead of 200. The reverse — a remote client forging `X-Forwarded-For: 127.0.0.1` into the keyless path — is blocked today only by `forwarded_allow_ips` defaulting to `127.0.0.1`, and `load_service_settings` calls `load_dotenv()`, so a `FORWARDED_ALLOW_IPS=*` line in an operator's `.env` reaches uvicorn and opens the bypass. `TestClient` calls the app directly and never loads this middleware, which is why the suite does not see it. | Pass `proxy_headers=False` to `uvicorn.run`, so the peer address really is the only input; assert it in a test on `main()`, and say in the docstring that the property is owned here rather than assumed. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/service.py:113` | `FastAPI()` mounts `/openapi.json`, `/docs` and `/redoc` outside the gated `/api` router. All three answer 200 to a non-loopback client with no key, disclosing all four route templates, their parameters and the app description. plan.md's Decision names the cost of the router-dependency choice as "route absence and nothing else"; this is the whole route list. | Build the app with `openapi_url=None, docs_url=None, redoc_url=None` — `cli.md` documents the four routes and nothing consumes the schema — and test that an ungated client gets 404 on each. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/service.py:83` | `hmac.compare_digest` on two `str` raises `TypeError` when either carries a non-ASCII character. Starlette decodes header values as latin-1, so `X-API-Key: cl\xe9` from any non-loopback client raises out of the gate: 500 with a traceback in the log instead of the named 401. Attacker-reachable with one `curl`. Contradicts `_require_key`'s own docstring, which says the refusal carries no traceback. | Compare the wire bytes: `presented_key.encode("latin-1")` against `settings.api_key.encode("utf-8")`. Add a test sending a non-ASCII byte header. |
| 🟡 | code | 2 | `src/wave_local_ai_v2/read_model.py:365` | `read_fiche` ends in `json.loads(path.read_text(...))` and `resolve_fiche` catches nothing, so one corrupt or unreadable file in the fiche registry raises `JSONDecodeError` out of the runtime and quality routes as a 500. Both sibling resolvers degrade instead: `resolve_suite_definition` catches `(OSError, JSONDecodeError)` and `load_roster_file` catches `RosterError`, and `read_rows_from_floor`'s docstring states the rule ("would take down a read-only service on one hand-edited line"). | Wrap the `read_fiche` call in `except (OSError, json.JSONDecodeError)` returning `_unresolved(POINTER_FICHE_HASH, fiche_hash)`, matching `resolve_suite_definition`. Add a corrupt-fiche test. |
| 🟢 | rot | 2 | `tests/test_read_model.py:119` | The partition tests are parametrized over a hardcoded `["runtime", "quality"]`, and `test_a_field_added_to_the_contract_fails_the_partition` exercises `"runtime"` alone. A third `RowKind` added to `row_contract.REQUIRED_FIELDS` would be rendered by no view and fail no test — the one drift the partition exists to catch that it does not catch. | Parametrize over `list(row_contract.REQUIRED_FIELDS)`, so a new kind raises `KeyError` in `RENDERED_SETS[kind]`. |
| 🟢 | code | 3 | `src/wave_local_ai_v2/service.py:136` | `loaded_roster()` re-opens and re-parses the roster on every request, and each view re-reads its whole store; a 591-row quality store is re-parsed per call. Deliberate (no cache, no invalidation) but undeclared. | Note the choice in the module docstring, or memoise per-app once a store grows past a pitch-sized file. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/settings.py:194` | `SERVICE_PORT` is validated with `minimum=1` and no upper bound, so `SERVICE_PORT=99999` passes settings and fails at bind with a raw `OSError` traceback instead of a named `SettingsError`. | Give `_require_numeric` an optional `maximum` and cap the port at 65535. |

## Verification

| Metric        | Value                                                                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Verified      | 97% (34/35)                                                                                                                               |
| Files checked | `src/wave_local_ai_v2/{service,read_model,results,settings}.py`, `tests/{test_service,test_read_model,test_results,test_settings,test_reference_bundle,store_fixtures,conftest}.py`, `pyproject.toml`, `uv.lock`, `.env.example`, `CHANGELOG.md`, `aidd_docs/memory/{cli,codebase-map,ecosystem,architecture}.md`, `evidence/` |
| Unchecked     | Phase 4 — the memory files describe the service as shipped: `fixed` (the critical finding's fix restores `cli.md`'s "no proxy header is read") |
| Unplanned     | none — every changed file is named in a phase's architecture projection                                                                    |
