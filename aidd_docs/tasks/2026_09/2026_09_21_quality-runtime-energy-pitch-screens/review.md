# Review: quality-runtime-energy-pitch-screens

- **Verdict**: approve (7 🟡 fixed in the review commit; the diff as first reviewed was changes-requested)
- **Diff**: `main...feat/dashboard-three-views`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_21
- **Findings**: 0 critical, 7 warning, 7 minor

## Phases

### Phase 1 — Read-model verification, the one real gap, route tests

- [x] Field inventory confirmed against `row_contract.py` and the "7" bundle; no gap, `read_model.py` untouched — `plan.md` Decisions, `git diff main...HEAD -- src/` empty
- [x] Three named-field tests pass — `tests/test_read_model.py:594`, `:605`, `:614` (`uv run pytest tests/test_read_model.py tests/test_service.py`: 116 passed)
- [x] Route-level test names `thinking_policy`'s absence and the four other fields over HTTP — `tests/test_service.py:103`

### Phase 2 — The nine mark label components, unit-tested per state

- [x] Each of the nine labels has a `*.test.tsx` covering true/false/`Absent` (verdict: three values + `differingFields`) by text query — `frontend/src/labels/*.test.tsx`
- [x] No label imports a view directory — `grep -rn "views/" frontend/src/labels/` returns nothing

### Phase 3 — The three screens over fixtures, boundary test, no-scroll

- [x] Three per-screen `types.ts`, none importing another's; `tsc -b --noEmit` exit 0 — `frontend/src/views/{quality,runtime,energy}/types.ts`
- [x] Fixtures cover every listed mark (verdict ×3, contested, indicative, contamination, unreliable, withheld headline, scope comparability, absent judge) — `views/*/fixtures/*.fixture.ts`
- [ ] QualityView shows every quality mark; judge-less entry renders `DeclaredAbsenceLabel`, no bare score; exact/graded never share a column — judge absence met (`QualityView.tsx` `renderJudgeBlock`: no agreement and no `single_judge` => `judged-score-withheld`); gaps: an absent breakdown rendered its keys, suite summary repeated per item (fixed)
- [ ] RuntimeView shows the fiche unconditionally, `ttft_source` beside `ttft_ms`, MB vs MiB — fiche's `fiche_hash` slot rendered `fiche.roster_entry_id` (fixed)
- [x] EnergyView withheld entry names the missing channel; labelled entry shows the composite headline with its three channel labels — `EnergyView.tsx` `HeadlineBlock` maps `CHANNELS` over `headline.methods`
- [x] Run click opens that run's screen; tab strip keeps the run — `App.tsx:75`, `RunsList.test.tsx` (tab strip scoped to run kind, deviation recorded in `evidence/phase-4-narrative.md`)
- [x] Boundary test passes and was confirmed failing on a deliberate cross-import — `views/boundary.test.ts:10-13`, `:47-60`
- [x] Width guard passes; 1280×800 walk documented — `views/widthGuard.test.tsx`, `evidence/phase-3-1280x800-check.md`

### Phase 4 — Evidence over the reference bundle and the live store, CHANGELOG, docs

- [ ] Six screenshots, each reference-bundle screen showing a named absence — six present (`.jpg`); `phase-4-runtime-reference-bundle.jpg` shows no absence because the "7" runtime row resolves every rendered field
- [x] Same bundle and process family for both walks, stated — `evidence/phase-4-narrative.md:3-7`
- [x] README names the three withheld constructs and their code path or owner — `aidd_docs/results/README.md` "What the dashboard withholds, and why"
- [ ] CHANGELOG accurately names what shipped — described a `Quality | Runtime | Energy` tab strip that `App.tsx` no longer has (fixed)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | code | 3 | `frontend/src/views/runtime/RuntimeView.tsx:55` | `fiche_hash` label rendered `fiche.roster_entry_id`; the fiche carries no hash, so the pitch screen showed `qwen3.6-35b-a3b-ud-iq4xs` as the hash (visible in `phase-4-runtime-reference-bundle.jpg`) | Fixed: `FicheBlock` takes `entry.fiche_hash`, wraps via `.fiche-hash`; test asserts the hash sits under the `fiche_hash` label |
| 🟡 | fit | 3 | `frontend/src/views/runtime/RuntimeView.tsx:75-91` | Spreads never rendered unless `unreliable` was true (Methodology 7, phase 2 task 5: the caller shows the bare spread); the `!isAbsent(unreliable) && unreliable` guard silently dropped an `Absent` flag instead of routing it through `UnreliableLabel` | Fixed: `ThroughputCell` always shows `(spread x)` and always renders `UnreliableLabel`, which owns the true/false/`Absent` states |
| 🟡 | code | 3 | `frontend/src/views/quality/QualityView.tsx:88-110` | `Object.entries` over a breakdown that is itself `Absent` (`_resolve_language_cells` returns one for a predating row) rendered `absent: undefined`, `reason: ...` as language cells | Fixed: `renderLanguageBreakdown` routes a whole-breakdown absence through `Absent`; test covers it |
| 🟡 | fit | 3 | `frontend/src/views/quality/QualityView.tsx:142-164` | Suite-level summary rendered once per item (phase 3 task 3.5: one `IndicativeLabel` per suite), repeating the suite mark and exclusion count N times, contested labels with no item id | Fixed: grouped by `suite_id`/`suite_version`; a raised mark on any row wins; contested items named by id; test asserts one row per suite |
| 🟡 | fit | 3 | `frontend/src/views/energy/EnergyView.tsx:54-56` | Headline's three channel labels ran together with the figures: `kg CO2ecpu: estimated_tdpgpu: measured_nvmlram: ...` (`phase-4-energy-reference-bundle.jpg`), unreadable at pitch distance | Fixed: ` · ` separator before each `EnergyMethodLabel`; test asserts `CO2e · cpu: .. · gpu: .. · ram:` |
| 🟡 | fit | 3 | `frontend/src/views/energy/EnergyView.tsx:94-98` | `ScopeComparabilityLabel` sat alone in its own footer row, not beside the figure it qualifies (phase 3 task 5.3); its absent state read as an orphan "not reported" | Fixed: rendered inline after `emissions_scope` as `(scope comparability: ...)` |
| 🟡 | rot | 4 | `CHANGELOG.md:16` | Entry described a `Quality \| Runtime \| Energy` run-scoped tab strip; the shipped strip is run-kind scoped (quality XOR runtime, plus Energy) | Fixed: entry rewritten to the run-kind strip |
| 🟢 | rot | 3 | `frontend/src/views/boundary.test.ts:47-60` | Only quality↔runtime dirs scanned; a third module importing both view-model types passes; `includes('runtime')` false-positives on e.g. `react/jsx-runtime`. No such module exists today (import grep over `src/`: only `App.tsx` imports both screen components, no module imports both `types.ts`) | tech-debt.md |
| 🟢 | code | 3 | `frontend/src/views/quality/QualityView.tsx` (`renderLanguageBreakdown`) | `reasons={[]}` renders `indicative ()` | tech-debt.md |
| 🟢 | code | 3 | `frontend/src/App.tsx:85` | Screen setter spreads a `runs` selection into an invalid union shape if ever called there | tech-debt.md |
| 🟢 | code | 3 | `frontend/src/views/runtime/RuntimeView.tsx` (`FicheBlock`) | Missing fiche key renders literal `undefined`; raw float precision on throughputs | tech-debt.md |
| 🟢 | fit | 3 | `frontend/src/App.tsx` | No App-level navigation test for criterion 6 | tech-debt.md |
| 🟢 | rot | 4 | `evidence/phase-4-*.jpg` | Two byte-identical duplicate screenshots | tech-debt.md |
| 🟢 | conform | - | `frontend/` | `prettier --check` fails on 29 files, new `views/` files included; pre-existing on `main` and ungated | tech-debt.md |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 76% (13/17)                                       |
| Files checked | `frontend/src/App.tsx`, `frontend/src/labels/*.tsx`, `frontend/src/views/{quality,runtime,energy}/*.tsx`, `views/*/types.ts`, `views/*/fixtures/*.ts`, `views/boundary.test.ts`, `views/widthGuard.test.tsx`, `views/RunsList.tsx`, `tests/test_read_model.py`, `tests/test_service.py`, `CHANGELOG.md`, `aidd_docs/results/README.md`, `evidence/*` |
| Unchecked     | P3 QualityView marks — fixed; P3 RuntimeView fiche — fixed; P4 named absence on every reference screen — not-applicable (the "7" runtime row has no absent rendered field); P4 CHANGELOG accuracy — fixed |
| Unplanned     | Run-kind tab strip replacing the planned shared-`run_id` strip (`App.tsx`), forced by independent run ids per store, recorded in `evidence/phase-4-narrative.md` |
