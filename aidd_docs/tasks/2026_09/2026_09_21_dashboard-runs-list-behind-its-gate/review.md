# Review: dashboard runs list behind its gate

- **Verdict**: changes-requested
- **Diff**: `main...feat/dashboard-runs-list`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_21
- **Findings**: 1 critical, 1 warning, 6 minor

## Phases

### Phase 1 — Decisions, origin plumbing, runs-view extension

- [x] Decisions table covers all seven decisions — `plan.md` Decisions table
- [x] `/api/runs` carries `release_version`, `commit_sha`, `tree_dirty` on both collections; models deduped; quality suites enumerated; runtime entries carry no `suites` key — `src/wave_local_ai_v2/read_model.py:142-151,495-522`, `tests/test_read_model.py:283-331`
- [x] `GET /` serves the entry document; unknown client route falls back; unknown `/api` path is 404 JSON; foreign-origin preflight not granted — `src/wave_local_ai_v2/service.py:232-260`, `tests/test_service.py:370-426`
- [x] Key gate not weakened: keyless non-loopback `GET /api/runs` => 401 (also with the allowed `Origin`), `HEAD /api/runs` => 405, keyless non-loopback `GET /` => 200 entry document — probe run over the `remote` fixture; `tests/test_service.py:224,266`
- [x] `.pre-commit-config.yaml` has no npm/eslint/prettier/tsc entry; `git check-ignore frontend/node_modules frontend/dist` both ignored — `.pre-commit-config.yaml:4-10`, `.gitignore:5,13`

### Phase 2 — Frontend scaffold, API client, key gate

- [ ] build, lint, format, `tsc --noEmit`, test with coverage all exit 0 — all exit 0, but `npm run typecheck` (`tsc --noEmit` over a `files: []` solution tsconfig) exits 0 with an injected type error: the gate checks nothing
- [x] `apiFetch` attaches the key only when stored; 401 => `UnauthorizedError` + key cleared; rejection => `NetworkError`; other non-2xx => `ApiError` with status — `frontend/src/api/client.ts:42-61`, `frontend/src/api/client.test.ts`
- [x] `KeyGate` withholds children without a key, stores a submitted key, re-prompts with a refusal and clears the key on a reported 401 — `frontend/src/components/KeyGate.tsx:36-83`, `frontend/src/components/KeyGate.test.tsx`

### Phase 3 — Runs list view, absence rendering, local build

- [x] `Absent` renders non-empty named text for every `read_model.ABSENCE_REASONS` value and every detail shape the read model emits (`{row_schema_version}`, `{}`, `{pointer, value}`) — `frontend/src/components/Absent.tsx:3-31`, `frontend/src/components/Absent.test.tsx:6-18`, `src/wave_local_ai_v2/read_model.py:42-47,109-114,354`
- [x] `RunsList` renders fixture values, absent fields through `Absent` (scalars, `models`, `suites`, `tree_dirty`), the empty state and the unreachable state — `frontend/src/views/RunsList.tsx:19-58,129-135`, `frontend/src/views/RunsList.test.tsx`
- [x] Manual walk over the built bundle served by `service.py` documented — `phase-3.md` Task 3 evidence, `evidence/phase-3-manual-verification.jpg`

### Phase 4 — CI `frontend` job, docs, setup path

- [ ] A PR with a failing `frontend` step shows `frontend` and `required` red — branch not pushed, no CI run exists; `required` wiring checked statically — `.github/workflows/ci.yml:214,228-231`
- [x] `tests/test_ci_workflow.py` passes and fails on an unsha'd `uses:` — `tests/test_ci_workflow.py:18,98-104`; 186 passed over the four touched test files
- [ ] Coverage gated at 80% so a dropped test fails the job — threshold present, but coverage counts only files a test loads: deleting `RunsList.test.tsx` raised lines from 93.54% to 96.42%, job green
- [x] `docs/setup.md` and README name the Node prerequisite and the one build command — `docs/setup.md:36-53`, `README.md:73-81`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | functional | 2 | `frontend/package.json:12` | `tsc --noEmit` resolves the root `tsconfig.json` (`files: []`, references only) and type-checks nothing: an injected `const x: number = 'nope'` exits 0, so the CI "Type check" step can never fail | `tsc -b --noEmit`, which walks both referenced projects (injected error => exit 2) |
| 🟡 | functional | 4 | `frontend/vite.config.ts:17-22` | No `coverage.include`: a deleted test file drops its subject from the denominator, so removing `RunsList.test.tsx` raises coverage and the 80% gate stays green | `include: ['src/**/*.{ts,tsx}']`, excluding tests, `setupTests.ts`, fixtures and `main.tsx` (dropped test => 59.34%, exit 1) |
| 🟢 | code | 1 | `src/wave_local_ai_v2/service.py:244-246` | `/assets` is mounted only if it exists at `create_app`; a bundle built after startup serves `index.html` whose assets 404 (blank page) | Mount unconditionally with `StaticFiles(check_dir=False)` |
| 🟢 | code | 1 | `src/wave_local_ai_v2/service.py:256` | `//api/runs` misses the router and gets the entry document with 200: a mistyped endpoint returns HTML, which the story rules out | Normalise leading slashes before the `api/` prefix check |
| 🟢 | fit | 3 | `frontend/src/views/RunsList.tsx:73-74` | `unreadable` is never rendered: a store whose rows all predate the floor shows "no runs recorded" though the API says N rows exist | Render each collection's `unreadable` counts beside the empty state |
| 🟢 | code | 3 | `frontend/src/components/Absent.test.tsx:13` | Asserts only non-empty "not reported", not that each reason's label is distinct as the phase-3 criterion names | Assert each reason's own label text |
| 🟢 | rot | 1 | `src/wave_local_ai_v2/settings.py:119-122` | Comment block about the `DASHBOARD_ORIGIN` default sits among constants with no constant under it; the rule lives in `load_service_settings` | Move the comment to `settings.py:284` |
| 🟢 | rot | 1 | `.gitignore:13` | `frontend/node_modules` duplicates `frontend/.gitignore:10` | Drop the root entry or the nested one |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 81% (13/16)                                       |
| Files checked | `src/wave_local_ai_v2/{read_model,service,settings}.py`, `tests/test_{service,read_model,settings,ci_workflow}.py`, `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `.gitignore`, `README.md`, `docs/setup.md`, `frontend/**` |
| Unchecked     | typecheck gate — fixed; coverage gate — fixed; failing-PR CI evidence — not-applicable (needs a pushed PR; publish at PR time) |
| Unplanned     | `ci.yml` sha-pins every pre-existing `actions/checkout`/`upload-artifact` (required by the story's "every action pinned"); `test_the_schema_and_docs_surfaces_are_not_mounted_by_fastapi` now expects the entry document instead of 404 |
