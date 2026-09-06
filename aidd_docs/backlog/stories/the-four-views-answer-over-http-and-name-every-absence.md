---
type: story
status: ready
source: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
order: 1
---

# Story: The four views answer over HTTP, and every absence is named

**As** a consultant preparing a pitch, and the client-side engineer who will audit it
**I want** a read-only service that answers the four views the PRD names, over the two stores as they actually stand, reporting every field a row does not carry as an explicit absence
**So that** the numbers become reachable without a terminal without any of them being invented, defaulted or inferred on the way out

## Acceptance

- PRD AC "a read-only results service exposes the list of runs, the quality table, the runtime table with its fiche, and the per-run energy detail": four separate routes answer them — `GET /api/runs`, `GET /api/runs/{run_id}/quality`, `GET /api/runs/{run_id}/runtime`, `GET /api/runs/{run_id}/energy`.
- No route returns a quality figure and a runtime figure in one response, and no route composes the two stores. The architecture rule ("the two are never merged into a single table") holds because there is no endpoint that could, not because of a convention about how pages are laid out.
- The service is read-only in the strict sense: every store file is opened for reading, every non-`GET` method on every route answers 405, and no code path in the service calls `results.append_row` or writes any file.
- **Declared-absent contract.** Every field a view names resolves to one of two states: a value, or an absence carrying its reason. Nothing is defaulted, zero-filled, back-filled or inferred. The reasons are named and finite: the row's `schema_version` predates the field, the row carries the key as `null`, or a pointer the row cites did not resolve.
- Methodology 19: the read-model selects rows by `schema_version` and never rewrites a store. A row below the service's declared floor is reported in an `unreadable` count naming its version, not rendered as a partial row and not silently dropped.
- Methodology 11 and PRD AC "never presented without both judges' scores and their agreement level ... visibly flagged single-judge": a quality row carrying no judge block is reported as a declared absence, never as zero and never as an unlabelled number. Neither store holds a judged row today, so this is the live path this story ships, not a path reserved for later.
- Methodology 15 and PRD AC "a single headline number in kg CO2e is displayed together with its energy_method label": the energy view returns `cpu_energy_kwh`/`gpu_energy_kwh`/`ram_energy_kwh` each beside its own method label, plus `energy_kwh`, `emissions_kg`, the factor, the region, `emissions_scope`, `emissions_scope_formula_id` and `scope_comparability`. The composite carries no single method label, and a row missing any one of the three channel labels yields no composite headline and names the missing label. (This corrects the epic, which was written against the retired single `energy_method` field; `row_contract.SCHEMA_VERSION` has carried three per-channel labels since `"4"`.)
- Methodology 14 and PRD AC "it always references a hardware fiche ... identified by the fiche's content hash": the runtime view resolves `fiche_hash` against the configured fiche registry and returns the fiche beside the row. A hash that does not resolve is an absence naming the hash, never an empty object.
- Methodology 8 and PRD AC "an explicit verdict of reproduced, not reproduced, or not comparable": each row's `verdict` block is returned as it stands, with its `reference_run_id` and `differing_fields`. The service computes no verdict, no agreement, no score and no aggregate — a number absent from a row is absent from the response.
- Methodology 4: per-language cells are returned with their `n` and their `indicative` mark. The two quality score shapes stay separate all the way out — an exact-match row's `correct`/`suite_accuracy`/`language_breakdown` and a graded row's `item_score`/`suite_score`/`score_breakdown` are never merged into one column, and a response mixing suites states which shape each row carries.
- PRD AC "the key is read from the environment ... and the service refuses to start without one": the service refuses to start when no API key is in the environment, on a loopback bind too, and every `/api/*` request from a non-loopback client is refused without a matching `X-API-Key`. Bind address, TLS and the browser's side of the key are order 5; this story ships only the two halves the PRD states unconditionally, so no later story retrofits a key into an origin that never had one.
- Store paths, fiche registry path, roster path and the schema floor are configuration, defaulting to the live per-machine stores. Pointing the same settings at `aidd_docs/results/*-reference.jsonl` serves the committed bundle without a code change.

## Code it changes

- `pyproject.toml` — `fastapi` and an ASGI server as pinned runtime dependencies (the first this project adds since its five benchmark-side ones), plus a `wave-local-ai-v2-serve` console script beside the four existing ones.
- `src/wave_local_ai_v2/read_model.py` (new) — the typed layer over the stores: one view model per route, the `Absent` value with its reason, the schema-floor selection, and the resolution of `fiche_hash`, `roster_entry_id` and `suite_id`/`suite_version` against their registries.
- `src/wave_local_ai_v2/service.py` (new) — the FastAPI app, the four routes, the startup key check, the non-loopback key gate, and the read-only posture.
- `src/wave_local_ai_v2/settings.py` — service bind host and port, API key, schema floor, and the store/registry paths as configured values beside the existing `DEFAULT_*` constants.
- `src/wave_local_ai_v2/results.py` — a read path that reports rows it cannot read rather than filtering them away; the writers are untouched.

## Tests it needs

- `tests/test_read_model.py` (new) — one case per absence reason: a quality row with no judge block; a runtime row missing one of the three energy channel labels; a `fiche_hash` with no file behind it; a row below the schema floor; a `roster_entry_id` absent from the roster. Plus: an exact-match row and a graded row in one response keep their two shapes and no field of one appears on the other.
- `tests/test_service.py` (new) — the four routes over a temporary store; no route's response body carries both a quality and a runtime field; `POST`/`PUT`/`PATCH`/`DELETE` answer 405 on every route; startup raises when the key is absent from the environment; a non-loopback request without the key is refused and the same request with it is answered.
- `tests/test_reference_bundle.py` — extended: the read-model answers all four views over the committed bundle, whose rows sit at `schema_version` `"7"`, and reports every field that version predates as a declared absence rather than failing.

## Evidence it publishes

- The four view responses captured over the committed reference bundle and over the live stores, filed with the delivery task — the first showing a mostly-absent shape at `"7"`, the second a mostly-populated one at `"11"`, from one unchanged service.
- No results row. This story's code writes nothing to either store, and the responses above are its own output, not a benchmark artifact.

## Cancellation

n/a — not cancelled.
