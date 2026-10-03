# Review: Every view names the machine and the mode, and a cpu_only row's VRAM reads not applicable

- **Verdict**: approve
- **Diff**: `HEAD (c68b23e)...working tree (uncommitted, schema "25")`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — Row-level VRAM not-applicable across repetitions, aggregate and contract

- [x] cpu_only repetition carries `"not_applicable"`, gpu carries the read or null — `repetitions.py:186`; `tests/test_repetitions.py:332`; `tests/test_cli.py:1023`, `:1046`, `:1055`
- [x] Marker-only peaks to marker; a mix raises; numbers peak as before — `aggregation.py:136`; `tests/test_aggregation.py:213`, `:223`, `:234`
- [x] cpu_only row with any VRAM number (zero included) refused; gpu row with marker refused; rows below "25" untouched — `row_contract.py:1348`; `tests/test_row_contract.py:2444`, `:2465`, `:2472`
- [x] GPU fields stay on the cpu_only fiche; GPU energy channel keeps its measurement and label — fiche code untouched; `tests/test_cli.py:1042-1043`; `evidence/fiches/d8524577...json` (gpu_name, gpu_driver_version present)

### Phase 2 — Read model: machine pointer, comparison dimensions, absence reason

- [x] cpu_only VRAM reads `not_applicable`; null VRAM still `null_in_row` — `read_model.py:146`; `tests/test_read_model.py:1605`, `:1620`
- [x] Declared id resolves with sources; unknown id `pointer_unresolved` naming `machine_id`; partition tests hold — `read_model.py:613`; `tests/test_read_model.py:1585`, `:1641`; `tests/test_service.py:116`
- [x] Two rows differing only in machine open two columns naming machine and mode — `read_model.py:475`; `tests/test_read_model.py:973`; existing comparison tests green

### Phase 3 — Front end: runtime and comparison views

- [x] "not applicable" distinct from "not reported" — `Absent.tsx`; `Absent.test.tsx`; `RuntimeView.test.tsx:135`
- [x] Machine id, mode, memory type/speed/GPU presence each marked declared; unresolved id named — `RuntimeView.tsx:92`; `RuntimeView.test.tsx:123`, `:146`
- [x] Column header names its machine and mode — `ComparisonView.tsx:61`; `ComparisonView.test.tsx:54`

### Phase 4 — Live cpu_only row viewed in the dashboard; CHANGELOG and memory

- [x] Live row carries `not_applicable` in all VRAM places and validates — `evidence/vram-grep.log`, `evidence/validate.log` (`checked 1 row(s)`)
- [x] CHANGELOG and memory state the change — `CHANGELOG.md`, `aidd_docs/memory/architecture.md`, `cli.md`, `codebase-map.md`
- [ ] Per-view dashboard screenshots — pending (no browser session or TLS pair in the unattended run); story "Evidence it publishes", not an Acceptance condition: blocks neither the commit nor `done` under the contract, owed as evidence

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | - | story title | Title says "Every view"; Acceptance names only the runtime and comparison views, and the epic Boundaries exclude rendering the machine dimension elsewhere (pitch epic owns it). Quality and energy views do not name machine/mode | Retitle the story, or file a follow-up in the pitch epic; not owed under the Acceptance as written |
| 🟢 minor | functional | 4 | `evidence/evidence.md` §3 | Per-view screenshots pending | Owner captures one screenshot per view over the evidence store when a browser + TLS pair is available; file under `evidence/` |
| 🟢 minor | code | 2 | `settings.py:265` | `machine_registry_path` is cwd-relative with no env override (unlike `ROSTER_PATH`); a service started outside the repo root renders every machine as unresolved (named, not blank) | Add a `MACHINE_REGISTRY_PATH` env read in `load_service_settings` if the service ever runs from another cwd |
| 🟢 minor | code | 2 | `read_model.py:475` | Column key now includes `machine`/`compute_mode`: two runs of one key straddling schema "23" (predates_schema vs value) open two columns instead of superseding. No effect on committed stores (all schema "7", one value per key) | None required; note in the comparison docs if it surprises a reader |
| 🟢 minor | conform | 3 | `frontend/src` | `prettier --check` flags 62 files including untouched ones (CRLF checkout), not caused by this diff; ESLint 0 errors | None for this story |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 92% (12/13) |
| Files checked | row_contract.py, repetitions.py, aggregation.py, gpu.py, __init__.py, read_model.py, service.py, settings.py, bundle_export.py, RuntimeView.tsx, ComparisonView.tsx, Absent.tsx, api/types.ts, runtime/types.ts, tests/*, evidence/* |
| Unchecked     | Per-view screenshots — not-applicable (Evidence, not Acceptance; pending owner browser session) |
| Unplanned     | none (bundle_export FieldDoc wording traces to the marker) |

Commands run: `uv run pytest -q` => `2307 passed, 2 warnings in 156.89s`, coverage 98.22%; `ruff check` all passed; `ruff format --check` 670 files formatted; `mypy src/ scripts/` no issues; `npm test` (offline) 27 files / 124 tests passed; `npm run typecheck` clean. `git status aidd_docs/results` clean (reference stores untouched); `frontend/node_modules` ignored by `frontend/.gitignore:10`.
