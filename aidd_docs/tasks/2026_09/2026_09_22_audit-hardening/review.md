# Review: Audit hardening increment

- **Verdict**: changes-requested
- **Diff**: `main...fix/audit-hardening`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_22
- **Findings**: 0 critical, 1 warning (fixed), 4 minor

## Phases

### Phase 1 — Reproduction verdict: the named run is the compared run, and unknowns never match

- [x] Two reference runs => `reference_run_id` names the deciding run; a disagreement confined to it changes the verdict — `src/wave_local_ai_v2/verdict.py:313`, `tests/test_verdict.py:334`, `tests/test_verdict.py:343`
- [x] Existing quality verdict tests pass unchanged — `uv run pytest`: 979 passed; no pre-existing test in `tests/test_verdict.py` edited
- [x] `llama_cpp_build` null on both fiches => `not_comparable` naming it — `src/wave_local_ai_v2/verdict.py:77,112`, `tests/test_verdict.py:197`
- [x] Null on one side only => `not_comparable` naming the field — `src/wave_local_ai_v2/verdict.py:176`, `tests/test_verdict.py:210`, `tests/test_verdict.py:225`
- [x] All blocking fields non-null => behavior unchanged — existing runtime tests pass unchanged (979 passed)
- [x] PRD Methodology 8 states the null rule in one sentence, no other PRD line changes — `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md:50` (single-line diff)

### Phase 2 — Read side: runtime label on its own metric, comparison key built from the dimension list

- [x] Flagged entry => label on gen tok/s only, prompt shows spread without label — `frontend/src/views/runtime/RuntimeView.tsx:113`, `frontend/src/views/runtime/RuntimeView.test.tsx:67`
- [x] Unflagged entry renders as before — `npx vitest run --coverage`: 97 passed
- [x] Appending a row-resolved dimension splits columns with no loop edit — `src/wave_local_ai_v2/read_model.py:904`, `tests/test_read_model.py:800`
- [x] `COMPARISON_DIMENSIONS == ("architecture",)` => response unchanged — `tests/test_read_model.py:785`, existing comparison tests pass

### Phase 3 — CI integrity guards: committed evidence re-verified, sampling parity, branch coverage

- [x] Committed fiche no longer hashing to its name fails, naming the hash — `tests/test_reference_bundle.py:67`
- [x] Committed suite snapshot differing from its builder fails, naming the file — `tests/test_suite_snapshot.py:114`
- [x] One-sided sampling, timeout, retry-delay or seed edit fails, naming the value — `tests/test_judge_probe.py:870`, `tests/test_judge_probe.py:878`
- [x] `finish_reason="length"` probe generation recorded as truncated — `tests/test_judge_probe.py:884`
- [x] Both coverage gates enforce branches and pass on the committed tree — `pyproject.toml:26` (95.66% combined, floor 80), `frontend/vite.config.ts:33` (66.77% branches, floor 66), `tests/test_ci_workflow.py:86`; see the `fit` warning on the Python floor's slack

### Phase 4 — Backlog: close fixed rows, log story-sized items without duplicates

- [x] Repr, `LLAMA_CPP_BUILD`, action-pinning and sampling-copy rows read `closed` with evidence — `aidd_docs/backlog/tech-debt.md:9,20,38,100`
- [x] Writer extraction recorded once, on the existing duplication row, citing audit ids — `aidd_docs/backlog/tech-debt.md:15` (W9 appears on exactly one row)
- [x] Frontend-type binding on exactly one new row — `aidd_docs/backlog/tech-debt.md:140`
- [x] No other row added — diff adds a single row (`tech-debt.md:140`)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 fixed | fit | 3 | `pyproject.toml:26` | `--cov-branch` joins a combined floor of 80 against a measured 95.66%: with 764 branches and 59 missed, branch coverage could fall to roughly 12% before the gate fails, so W21's intent (early-return metric branches enforced) is not held. The frontend gate uses the measured floor (`frontend/vite.config.ts:31-33`), the Python one does not. **Fixed 2026-09-22**: `pyproject.toml:26` sets `--cov-fail-under=95` (measured 95.66%, rounded down); `coverage.py`'s `results.py` confirms `--cov-fail-under` has no separate branch-only mode, only a combined `pc_covered`, so the floor must sit near the measured combined total — noted in a `pyproject.toml` comment and at `aidd_docs/memory/coding-assertions.md:41`. |
| 🟢 minor | code | 2 | `src/wave_local_ai_v2/read_model.py:899-905,924-930` | Roster entry and every dimension are resolved per row to build the key, then resolved again per column for `dimensions`; phase-2 task 2.2 asked for one resolution when simple. | Carry the resolved dimension values with the group (e.g. the tail of `entry_key` paired with the raw values) and build `dimensions` from them. |
| 🟢 minor | code | 1 | `src/wave_local_ai_v2/verdict.py:175-176,71` | `runtime_verdict` resolves the candidate fiche from disk, then `select_runtime_reference` and `_closest_reference_differing_fields` resolve it again; the null guard runs twice. The guard in `select_runtime_reference` is justified (public function), the extra disk reads are not. | Resolve the candidate fiche once in `runtime_verdict` and pass it to the two helpers, keeping the public guard. |
| 🟢 minor | fit | 3 | `tests/test_reference_bundle.py:68-69` | Comment says a hand-edited fiche "is no longer the fiche the harness wrote" and fails; `flags` is a verdict-blocking field (`verdict.py`) but outside the hashed projection (`hardware.py:39-43`), so an edit to `flags` still verifies `ok`. Plan Decisions defers fiche-hash alignment, so the gap is known but unstated at the guard. | Narrow the comment to the hashed projection and append the `flags` blind spot to the existing Decisions deferral's backlog record rather than a new row. |
| 🟢 minor | rot | 2 | `src/wave_local_ai_v2/read_model.py:340-346` | Comment edit left a mid-sentence break ("appending a name here and, once it" on its own short line). | Reflow the comment block. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (19/19) |
| Files checked | `src/wave_local_ai_v2/verdict.py`, `src/wave_local_ai_v2/read_model.py`, `frontend/src/views/runtime/RuntimeView.tsx`, `frontend/src/views/runtime/RuntimeView.test.tsx`, `frontend/vite.config.ts`, `pyproject.toml`, `tests/test_verdict.py`, `tests/test_read_model.py`, `tests/test_reference_bundle.py`, `tests/test_suite_snapshot.py`, `tests/test_judge_probe.py`, `tests/test_ci_workflow.py`, `aidd_docs/backlog/tech-debt.md`, `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`, `aidd_docs/memory/coding-assertions.md` |
| Unchecked     | none |
| Unplanned     | `aidd_docs/memory/coding-assertions.md:41` gate wording (doc sync for W21); `_dedup_key` dict/list support at `src/wave_local_ai_v2/read_model.py:540-543` (needed for `architecture` in the key, traces to phase-2 task 2) |
