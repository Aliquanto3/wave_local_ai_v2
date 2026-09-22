# Review: Dense and MoE stand side by side on the same items

- **Verdict**: blocked
- **Diff**: `main...feat/dense-moe-view` (commits `02c9471`, `3f00c63`) plus uncommitted `CHANGELOG.md`, `aidd_docs/results/README.md`, `phase-3.md`, `evidence/`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_21
- **Findings**: 1 critical, 5 warning, 2 minor

## Phases

### Phase 1 — `read_model.comparison_view`, the `/api/comparisons` route, column/cell semantics, tests

- [x] `COMPARISON_DIMENSIONS` exists and is iterated, not hand-listed, when a column's `dimensions` dict is built — `src/wave_local_ai_v2/read_model.py:347`, dict comprehension in `_comparison_columns`
- [x] Two rows sharing `(suite_id, roster_entry_id)` at different `captured_at` collapse into one column backed by the later run — `tests/test_read_model.py` `test_a_comparison_column_is_backed_by_only_the_later_run`
- [x] An item absent from one column's backing rows renders `status: "not_compared"` there and a scored cell elsewhere — `test_a_comparisons_columns_each_name_their_own_suite_version`
- [x] `GET /api/comparisons` returns without a `run_id`, reading only `quality_results_path` — `src/wave_local_ai_v2/service.py:192`
- [x] `pytest tests/test_read_model.py -k comparison` passes, including the field-partition test — `4 passed, 35 deselected` (the test itself is weak, see Findings)

### Phase 2 — The `views/comparison/` screen over fixtures, App.tsx entry point, boundary test extended

- [x] `views/comparison/types.ts` imports nothing from `views/quality/` or `views/runtime/` — `frontend/src/views/comparison/types.ts:7` (only `../../api/types`)
- [x] `ComparisonView` renders one section per suite_id and one column per column entry, each naming its `roster_entry_id` — `ComparisonView.tsx:144-181`, `:94-100`
- [x] `npm test` passes `ComparisonView.test.tsx`, including not-compared and indicative-mark assertions — `vitest run src/views/boundary.test.ts src/views/comparison`: `Tests 8 passed (8)`
- [x] "Compare dense and MoE" reaches the comparison screen without selecting a run — `frontend/src/App.tsx` `selection.status === 'runs'` branch button => `{ status: 'comparison' }`
- [x] `views/boundary.test.ts` fails on a temporary cross-import and passes clean afterward — proof recorded `frontend/src/views/boundary.test.ts:72-76`; clean run green. Boundary holds: 3 pairwise checks pass, comparison branch in `App.tsx` mounts `ComparisonView` alone, which fetches `/api/comparisons` alone, which reads `quality_results_path` alone

### Phase 3 — Evidence over the live store, `aidd_docs/results/README.md`, CHANGELOG

- [ ] Two screenshots exist, captioned with run_ids and figures matching the README tables — screenshots exist, figures 0.45/0.60/0.70/1.00 and 0.5121/0.7107/0.7252/0.8002 match, but no caption names the run_ids, the `gemini-3.5-flash-lite` column the task requires is absent from both, no version caveat shows, and task 1.4's "every item shared" note is missing
- [x] README note names the live route and does not restate the tables — `aidd_docs/results/README.md:543-547`
- [ ] CHANGELOG `Unreleased/Added` names the route and the screen, not a restatement of the acceptance — it names both, but restates the acceptance ("never a blank or a zero", dimensions, boundary) and claims `boundary.test.ts` enforces "no import from `views/quality/`", which it does not

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | fit | 1 | `src/wave_local_ai_v2/read_model.py:846` | Column key `(suite_id, roster_entry_id)` merges different models. Live store: the cited `google`/`gemini-3.5-flash-lite` rows carry `roster_entry_id: qwen3.6-35b-a3b-ud-iq4xs`, so they share the MoE's group and the later local MoE run wins; gemini disappears silently. The plan's own worked example (comparator at an older `suite_version` as its own column) never renders, and the version caveat never fires on real data | Add the row's model identity (`provider` + `model_id`, via `resolve_field`) to the column key, or as a row-resolved entry in `COMPARISON_DIMENSIONS` that also keys the group; add a test with two rows sharing `roster_entry_id` but different `provider` asserting two columns; then fix the `<th key>` in `ComparisonView.tsx:96`, which would collide once two columns share an id |
| 🟡 | fit | 1 | `src/wave_local_ai_v2/read_model.py:935` | Story: "No runtime, energy or cost column is reachable from it." Each compared cell spreads all of `_quality_entry`, so `/api/comparisons` ships `cost_total`, `cost_currency`, `cost_per_million_tokens`, `kwh_price_*`, `list_price_*`, `tokens_*_total` per item | Project the compared cell to the score/label fields the screen renders (score shape, breakdowns, `contamination_risk`, `verdict`, `failure_counts`, identity); drop pricing/cost/token totals |
| 🟡 | code | 1 | `tests/test_read_model.py:818` | Field-partition test asserts over a hand-listed `COMPARISON_ENTRY_FIELDS`, never over `comparison_view`'s output, and `RUNTIME_EXCLUSIVE_FIELDS` (`:843`) subtracts `QUALITY_VIEW_FIELDS`, making most of the intersection empty by construction. A `ttft_ms` key added to `comparison_view` would still pass | Build the field set from the function's declared projection (a module-level constant the cell builder uses) and assert it disjoint from `RUNTIME_VIEW_FIELDS - RUNS_VIEW_FIELDS`, `ENERGY_VIEW_FIELDS`, and any `cost*`/`*price*` field; the story asks "over the type", so the constant must be the one the code uses |
| 🟡 | frontend | 2 | `frontend/src/views/comparison/ComparisonView.tsx:97-128` | No CSS for any `comparison-*` class (`index.css` has none): header spans run together (`q8{"kind":"dense","expert_count":0,"active_params_b":0.6}Q8_0suite_version 3disabled` in `evidence/phase-3-comparison-classification.png`), cells concatenate (`n=5not comparable`), and the table overflows horizontally with the MoE column cut off. Unreadable at pitch distance; `widthGuard.test.tsx` does not cover this screen | Style the header spans as stacked labelled lines, render `architecture` as `dense` / `moe (N experts, X B active)` with the raw dict as fallback for unknown dimensions, round scores like `QualityView`, and extend `widthGuard.test.tsx` to `ComparisonView` |
| 🟡 | functional | 3 | `aidd_docs/tasks/2026_09/2026_09_21_dense-and-moe-side-by-side/evidence/` | Evidence criterion unmet: no captions with run_ids, gemini column absent, no version caveat, no "every item shared" note | After the 🔴 fix, recapture both screens showing the gemini column and caveat, add a caption file naming run_ids and figures, and state explicitly whether any not-compared cell exists on live data |
| 🟡 | functional | 3 | `CHANGELOG.md:12-24` | Entry restates the acceptance and claims `views/boundary.test.ts` enforces "no import from `views/quality/`" for the comparison screen; the third check only rejects `runtime` specifiers | Cut to route + screen + entry point in one or two lines; either drop the quality-import claim or add that check to `boundary.test.ts` |
| 🟢 | conform | 2 | `frontend/src/views/boundary.test.ts:77-83` | Third check matches only `runtime`; `views/energy/` (runtime-store data) is importable from `views/comparison/` without failing, while the story also forbids energy | Match `runtime` or `energy` in the comparison check |
| 🟢 | rot | 2 | `frontend/src/views/comparison/types.ts:70-145` | ~75 lines restate `QualityEntry` field by field; drift from `_quality_entry` goes undetected (plan-mandated duplication) | Shrinks automatically once the 🟡 cell projection lands; otherwise log to tech-debt |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 85% (11/13) |
| Files checked | `src/wave_local_ai_v2/read_model.py`, `src/wave_local_ai_v2/service.py`, `tests/test_read_model.py`, `frontend/src/App.tsx`, `frontend/src/views/boundary.test.ts`, `frontend/src/views/comparison/ComparisonView.tsx`, `frontend/src/views/comparison/ComparisonView.test.tsx`, `frontend/src/views/comparison/types.ts`, `frontend/src/views/comparison/fixtures/comparisonView.fixture.ts`, `CHANGELOG.md`, `aidd_docs/results/README.md`, `evidence/*.png`, `aidd_docs/results/quality.jsonl` (read-only probe) |
| Unchecked     | Phase 3 evidence captions/gemini column — fix; Phase 3 CHANGELOG restatement — fix |
| Unplanned     | `service.py` module docstring "four" => "five" routes (consistent); 42 working-tree files under `frontend/src/` report modified with no content diff (line-ending stat noise, nothing to commit) |
