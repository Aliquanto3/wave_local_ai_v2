# Review: The pitch opens on one card per use case, read from published rows

- **Verdict**: changes-requested
- **Diff**: `main...feat/pitch-overview-one-card-per-use-case` (991a6b3)
- **Axes run**: code, functional, relevancy (plus caller gate: boundary enforced by test, absences render as declared, story status `done`)
- **Date**: 2026_09_22
- **Findings**: 1 critical, 11 warning, 4 minor

## Phases

### Phase 1 — Two read-model selections and the two overview routes, Python tests

- [x] 1: `overview_quality_view` groups by `task_suite`, resolves `leader_set_member`/`provider` via `resolve_field`, no new absence reason, reuses `_quality_entry` — `src/wave_local_ai_v2/read_model.py:1065`, `:1096`, `:1125`
- [x] 2: `overview_runtime_view` groups by `roster_entry_id`, reads only `runtime_path`, `energy_headline` identical to `_energy_entry`'s (shared `_energy_headline_for`) — `read_model.py:787`, `:1190`; `tests/test_read_model.py` `test_overview_runtime_view_over_the_reference_bundle_picks_the_latest_row`
- [x] 3: both routes on the gated `api` router, no new wiring; 401/405 covered by adding them to `ROUTES` — `src/wave_local_ai_v2/service.py:210`, `:223`; `tests/test_service.py:37`
- [x] 4: `uv run pytest tests/test_read_model.py tests/test_service.py` => 159 passed
- [ ] Task 4.2: reference bundle `cloud_comparators == []` — plan premise false: the bundle carries 40 `mistral` rows (grep); test asserts non-local instead, README records it (not-applicable)
- [ ] 5: service store-separation assertion "fails if either route is ever changed to read both stores" — `tests/test_service.py:197`, `:209` assert top-level key sets only; a runtime field nested inside `cloud_comparators[]` or `runtime_headline` would pass (fix)

### Phase 2 — The overview screen: card shell, quality panel, runtime+energy panel, landing wiring, boundary and width guards

- [x] 1: both `types.ts` compile (`tsc -b` exit 0) and import only `api/types` — `frontend/src/views/overview/quality/types.ts:12`, `runtime/types.ts:9`
- [ ] 2-3: panels render every state their Test Scope names — leader-present-but-no-runtime-row, empty `members`, empty `cloud_comparators` render nothing stated (fix)
- [x] 4: `OverviewCard.tsx` imports only the two components — `frontend/src/views/overview/OverviewCard.tsx:1-2`; scanned by `frontend/src/views/boundary.test.ts:136`
- [x] 5-6: `CoverageAbsence` once, one card per real `task_suite`, absent `task_suite` skipped — `OverviewView.test.tsx` (3 cases), `OverviewView.tsx:61`
- [x] 7: root opens on the overview, one click to runs — `frontend/src/App.tsx:70`, `:77`; `frontend/src/App.test.tsx:46`
- [x] 8: overview boundary scan added, break-it proof documented — `frontend/src/views/boundary.test.ts:116`
- [x] 9: `OverviewView` in the width guard — `frontend/src/views/widthGuard.test.tsx:87`
- [ ] 10: `npx vitest run` => 114 passed, but "each fails if a figure not present in its fixture were rendered" is not tested, and assertions hard-code fixture values (`QualityPanel.test.tsx:37`, `RuntimeEnergyPanel.test.tsx:31`, `:38`) (fix)

### Phase 3 — Evidence over the reference bundle and a leader-set fixture bundle, README note

- [ ] 1: reference screenshot shows "no cloud comparator" — plan premise false (bundle has cloud rows); screenshot shows 40 comparator item rows instead (not-applicable; the real defect is the critical `fit` finding)
- [ ] 2: leader-set screenshot shows two distinct leaders with real headlines — both members share `qwen3.6-35b-a3b-ud-iq4xs`, one headline renders; plan asked for a second `roster_entry_id` with its runtime row (fix)
- [x] 3: README section names the three withheld constructs and their code path / owning epic — `aidd_docs/results/README.md:133`
- [x] 4: `CHANGELOG.md` `Unreleased/Added` names the shipped files — `CHANGELOG.md:10`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | fit | 1 | `src/wave_local_ai_v2/read_model.py:1096`, `:1065` | Quality rows are per item, and `_cloud_comparators`/`_leader_membership` emit one `_quality_entry` per item row. Over the reference bundle the classification card lists 40 comparator lines (`evidence/phase-3-overview-reference-bundle.png`); a leader model would list one "member" per item. Story: "every cloud **subject**", one card read "before the detail". The test at `tests/test_read_model.py:1142` bakes this in (item-1/item-2 of one run as "two leaders"). | Deduplicate to one entry per subject (run_id, or roster_entry_id/model_id + run_id) carrying the suite-level score (`suite_accuracy`/`suite_score`), not the item's `correct`; rewrite the leader test with two distinct subjects; retake both screenshots |
| 🟡 | conform | - | `aidd_docs/backlog/stories/the-pitch-opens-on-one-card-per-use-case-read-from-published-rows.md:3` | Gate: story still `status: ready` (plan says `implemented`, phases `done`) | Set `status: done` in the fix commit, after the critical finding lands |
| 🟡 | fit | - | `aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md:42`, `:71` | The story says the view-boundary carve-out is recorded by amending the epic's Boundaries; the epic is not in the diff, so it still reads "no response that returns both" with no card-shell carve-out | Amend the epic's Boundaries and Success Evidence with the carve-out as the story words it |
| 🟡 | fit | 2 | `frontend/src/views/boundary.test.ts:120` | Gate: the overview quality scan matches only `runtime`; the story requires "imports no runtime **or energy** type", and the existing quality scan at `:100` already checks both. An `overview/quality` import of `views/energy/types` passes | Match `s.includes('runtime') \|\| s.includes('energy')`, the same as `:100` |
| 🟡 | functional | 1 | `tests/test_service.py:197`, `:209` | Gate: store separation over HTTP is checked on top-level keys only (plan task 5.2, story "neither response carries a key from the other store") | Assert that neither JSON body contains any field from `REQUIRED_FIELDS[other] - REQUIRED_FIELDS[self]` and that the quality body has no runtime-only `roster_entry_id` value, as `test_read_model.py` does |
| 🟡 | functional | 2 | `frontend/src/views/overview/runtime/RuntimeEnergyPanel.tsx:119` | Gate: when a leader's `roster_entry_id` has no row in the runtime store, the filter returns `[]` and the panel renders an empty `<section>`, a silent absence | Per requested id with no entry, render `DeclaredAbsenceLabel` naming the id ("no runtime row for …") |
| 🟡 | functional | 2 | `frontend/src/views/overview/quality/QualityPanel.tsx:120`, `:127`; `OverviewView.tsx:68` | Gate: a published leader set whose rows are all `False` renders an empty list, and the runtime panel then says "no leader set published", which is wrong for that case. An empty `cloud_comparators` renders a bare heading | Render a declared absence for an empty `members` ("leader set published, no member") and for empty comparators ("no cloud subject in the store for this suite"); pass the distinction to the runtime panel or word its detail neutrally |
| 🟡 | code | 2 | `frontend/src/views/overview/runtime/RuntimeEnergyPanel.tsx:30` | `String(machine.gpu_name)`: `hardware.py:23` types `gpu_name: str \| None`, so a CPU-only fiche renders the literal "null" (or "undefined" if the key is missing) as the machine | Render the `fiche_hash` reference (the story asks for "its fiche reference") and `gpu_name` only when it is a string, otherwise an `Absent` |
| 🟡 | fit | 1-2 | `read_model.py:1218`; `RuntimeEnergyPanel.tsx:128` | Story: "every figure on a card names the `run_id` and field it was read from" and the headline "carrying its fiche reference". The runtime entry carries no `run_id` and renders no fiche reference | Add the chosen row's `run_id` (and `fiche_hash`) to the runtime entry and render both beside the headline |
| 🟡 | fit | 2 | `frontend/src/views/overview/quality/QualityPanel.tsx:50` | Story label parity names single-judge, contested, caps and `thinking_policy`; the panel renders only contamination-risk, indicative and verdict (the plan narrowed the list). A graded suite's leader would appear without its judge caveats | Render `SingleJudgeLabel`, `ContestedLabel`, caps and `thinking_policy` the way `views/quality/QualityView.tsx:75`, `:182` do |
| 🟡 | functional | 2 | `frontend/src/views/overview/quality/QualityPanel.test.tsx:37`; `runtime/RuntimeEnergyPanel.test.tsx:31`, `:38` | Plan task 10: assert against the fixture's own values, and fail if a figure not in the fixture is rendered. Tests hard-code run ids, roster ids, "RTX 3060" and counts | Derive the expected strings from the fixture objects; add a check that every numeric text node on the card appears in the fixture payload |
| 🟡 | functional | 3 | `aidd_docs/tasks/2026_09/2026_09_22_pitch-overview-one-card-per-use-case/evidence/phase-3-overview-leader-set-bundle.png` | Plan task 3.2 asked for two leaders on distinct `roster_entry_id`s with runtime rows; both members are `qwen3.6-35b-a3b-ud-iq4xs`, so one headline renders | Once the critical finding is fixed, retake with a second local subject plus a matching runtime row in the scratch bundle |
| 🟢 | rot | 2 | `QualityPanel.tsx:28`; `RuntimeEnergyPanel.tsx:36`; `overview/quality/types.ts:73-148` | `renderScore`, `EnergyHeadlineBlock` and a 75-line `QualityEntry` mirror are copied from `QualityView`/`EnergyView`/`quality/types.ts`, while phase 2 tasks 2.2 and 3.3 say "imported, not re-implemented" | Move `renderScore`/headline rendering into `labels/` or `components/` (shared, store-neutral) and import them from both screens; keep the type mirror only if the boundary decision requires it |
| 🟢 | code | 2 | `RuntimeEnergyPanel.tsx:128`, `:54` | Raw floats at pitch distance (`24.801659953618945 tok/s`, `0.0026422160819648713 kWh` in the evidence) | Format for display only (fixed significant digits); the stored value stays unchanged |
| 🟢 | performance | 2 | `QualityPanel.tsx:75` | Each card re-fetches the whole store-wide `/api/overview/quality` (1 + N requests, and each serializes every suite's comparators). Accepted in Decisions, but it grows with the critical finding's per-item payload | Resolved mostly by the dedup; otherwise have `QualityPanel` share a single fetch through a context scoped to `overview/quality` |
| 🟢 | code | 1 | `read_model.py:1081` | `_leader_membership` returns `resolved[0]` when every row is `Absent`, so mixed reasons (`null_in_row` on one row, `predates_schema` elsewhere) report only the first | Prefer a non-`predates_schema` reason when present, or document that the first wins |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 67% (12/18)                                       |
| Files checked | src/wave_local_ai_v2/read_model.py, src/wave_local_ai_v2/service.py, tests/test_read_model.py, tests/test_service.py, frontend/src/App.tsx, frontend/src/App.test.tsx, frontend/src/views/boundary.test.ts, frontend/src/views/widthGuard.test.tsx, frontend/src/views/overview/** (all), CHANGELOG.md, aidd_docs/results/README.md, evidence/*.png, story + epic files |
| Unchecked     | P1 task 4.2: cloud_comparators [] (not-applicable); P1 AC5: HTTP store-separation (fix); P2 AC2-3: every panel state stated (fix); P2 AC10: fixture-traced figures (fix); P3 AC1: no cloud comparator (not-applicable); P3 AC2: two distinct leaders (fix) |
| Unplanned     | `App.test.tsx` mock-ordering race fix (991a6b3, supports P2 AC7); `_energy_entry` refactor into `_energy_headline_for` (planned under P1 task 2.2, listed for traceability) |
