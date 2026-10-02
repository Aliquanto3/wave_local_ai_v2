# Review: A thinking switch the template ignores is refused, never published as disabled

- **Verdict**: approve
- **Diff**: `HEAD...working-tree` (uncommitted, branch `docs/slice-remaining-epics` worktree)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_02
- **Findings**: 0 critical, 0 warning, 4 minor

## Phases

### Phase 1 — The thinking-control declaration on a roster entry

- [x] Malformed control refused naming `thinking_control` (empty object, null, other string, list, number) — `src/wave_local_ai_v2/roster.py:262`, `tests/test_roster.py:392`
- [x] `"none"`, an object and an absent key all load — `tests/test_roster.py` `test_a_well_formed_or_absent_thinking_control_loads`
- [x] Every shipped entry declares the Qwen control — `aidd_docs/roster/models.json` (4 entries), `tests/test_roster.py:428`
- [x] Export writes one `thinking_control` JSON cell per roster row — `src/wave_local_ai_v2/bundle_export.py` (`json_cells`), `tests/test_bundle_export.py:74`

### Phase 2 — The client sends the entry's control and verifies it once per batch

- [x] Identical renders raise naming entry, control and template hash before any chat call — `src/wave_local_ai_v2/local_client.py:136,172`, `tests/test_local_client.py:331` (two `/apply-template` POSTs only)
- [x] Differing renders return both strings — `tests/test_local_client.py:362`
- [x] Chat body carries the entry's declared control; Qwen spelling gone as module default — `src/wave_local_ai_v2/local_client.py:98,263`, `tests/test_local_client.py:289`
- [x] `none` sends nothing and is not probed — `tests/test_quality_cli.py:1926`
- [x] Undeclared entry refuses under `disabled`, naming the entry, before launch — `src/wave_local_ai_v2/quality_cli.py:425`, `tests/test_quality_cli.py:1945`
- [x] Refused verification writes no row and runs no cloud batch — `tests/test_quality_cli.py:1903`, `tests/test_judge_probe.py:1012`
- [x] `allowed` sends nothing whatever the entry declares — `tests/test_local_client.py:237`
- [x] Shipped-spelling batch stores the same rendered prompt and hash — `tests/test_quality_cli.py:1962`
- [x] `uv run pytest` at the 95% floor — `1163 passed, 2 warnings in 35.52s`, total coverage 96.47%

### Phase 3 — One live verification against qwen3-0.6b-q8

- [x] Two differing renders and the pass recorded — `evidence/live-verification.md` (template hash, both strings, `Verified: true`)
- [x] `cli.md` names `thinking_control` and the per-batch verification — `aidd_docs/memory/cli.md:164`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | code | 1 | `src/wave_local_ai_v2/roster.py:262`, `src/wave_local_ai_v2/local_client.py:235,263` | Control is spread last into both request bodies; any non-empty object loads, so a control declaring `messages`, `max_tokens` or a sampler key would silently override them | Refuse reserved request keys (`messages`, `max_tokens`, sampler keys) in `_parse_thinking_control` |
| 🟢 minor | fit | 2 | `src/wave_local_ai_v2/quality_cli.py:425-460` | `write_fiche` runs before the verification, so a refused batch still leaves a fiche in the registry (not a row; acceptance holds) | Optional: run the verification-dependent refusal before writing the fiche, or accept as harmless |
| 🟢 minor | fit | 2 | `tests/test_local_client.py:237` | "byte-identical under both policies" for `allowed` is proved at client level only; no batch-level `allowed` test (no suite declares `allowed`) | None required; add a batch-level test if a suite ever declares `allowed` |
| 🟢 minor | conform | 3 | `evidence/live-verification.md:46` | Live evidence produced by a scratch script kept outside the repo; reviewer cannot rerun it without the model | None required by the story; keep the script path in evidence if rerun matters |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (15/15)                                      |
| Files checked | roster.py, local_client.py, quality_cli.py, judge_probe.py, bundle_export.py, models.json, .secrets.baseline, cli.md, test_roster.py, test_local_client.py, test_quality_cli.py, test_judge_probe.py, test_bundle_export.py, evidence/live-verification.md |
| Unchecked     | none                                              |
| Unplanned     | none: `bundle_export.py` forced (`build_table` raises `ExportError` on an undescribed roster field); `judge_probe.py` forced (`render_prompt`/`complete_chat` signatures changed, and it publishes `thinking_policy` rows under `disabled`); `.secrets.baseline` line numbers match a fresh `detect-secrets scan` of `models.json` (10, 44, 48, 83, 87, 122, 126); `cli.md` is phase 3 task 2. Gates: ruff check, ruff format --check, mypy all clean |
