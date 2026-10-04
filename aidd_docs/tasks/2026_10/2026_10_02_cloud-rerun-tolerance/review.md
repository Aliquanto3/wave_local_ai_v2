# Review: A cloud subject re-run is decided per item under its suite's declared tolerance

- **Verdict**: approve
- **Diff**: `HEAD...working tree (uncommitted, schema "29")`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — Declared tolerance: gate, registry, suite data and snapshots

- [x] A missing or malformed tolerance is refused by the gate, naming the problem — `src/wave_local_ai_v2/suite_gate.py:178`, `tests/test_suite_gate.py:275` (+ malformed/non-object cases), `tests/test_suite_registry.py` (refused at load)
- [x] Both shipped suites resolve with their tolerance; regenerated snapshots equal the committed ones; old snapshots untouched — `suite_data/*.json:11`, new `suite-definitions/classification-support-routing@5.json` and `translation-business-short-form@4.json`; `git diff aidd_docs/results/` empty (additions only); `prompt_set_hash` identical across @2..@5

### Phase 2 — Per-item cloud verdict, verdict fields (schema "29"), CLI wiring, export docs

- [x] Each story test case returns the stated verdict and names items, rule, tolerance and suite version — `tests/test_verdict.py:727,742,754,766,794,824,834`
- [x] A "29" quality row missing a verdict key is refused; a deterministic local row validates; "28" rows still validate — `src/wave_local_ai_v2/row_contract.py:922,1670`, `tests/test_row_contract.py:2793,2799`
- [x] A CLI run writes rows whose verdict block names the provider's rule and the suite's tolerance — `src/wave_local_ai_v2/quality_cli.py:1519`, `tests/test_quality_cli.py:379,402,432`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | 2 | `src/wave_local_ai_v2/quality_cli.py:834` | `model_not_served` is only a stderr line at pre-flight; no row or record ever carries it, while the PRD AC says "its row is marked". The verdict rule is proven on constructed rows (`tests/test_verdict.py:754`), which is what the story's Tests section asks. | Owner decision: accept as the verdict-level rule, or open a follow-up that persists the mark (a re-run record or a read-side derivation), since published rows are append-only. |
| 🟢 minor | fit | 1 | `src/wave_local_ai_v2/suite_data/translation-business-short-form.json:11` | Translation 0.10 is provisional (no observed cloud re-run, D2); acceptance says each value is "set against an observed cloud re-run". Reason states this honestly. | Cloud-pending: re-set after a Mistral/Google re-run of translation v4 is published. |
| 🟢 minor | fit | 2 | `aidd_docs/results/quality-reference.jsonl` | Published references are classification v2; reference matching keys on `suite_version`, so a v5 cloud re-run is `not_comparable` against them. Pre-existing (refs were already v2 vs v4), not caused by the bump. | Evidence run needs a v5 reference batch plus a re-run (two paid batches), then the README entry. |
| 🟢 minor | rot | 2 | `src/wave_local_ai_v2/judge_probe.py:288,1044` | Probe cloud rows publish `subject_rule: within_tolerance` with a `0.0` tolerance that is never applied, while the plan nulls the tolerance on local blocks precisely so a never-applied value is not suggested. Reason text and `not_comparable` keep it honest. | Optional: accept as is (the row contract requires the shape for cloud rows), or let the judged-re-run story own the probe's value. |
| 🟢 minor | fit | 2 | `src/wave_local_ai_v2/verdict.py:503` | Translation compares `item_score` (chrF float) by exact equality; any wording change diverges, so 0.10 may prove too tight for a graded suite. | Revisit unit with the calibration run. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (5/5)                                        |
| Files checked | verdict.py, suite_gate.py, suite_registry.py, quality_cli.py, row_contract.py, judge_probe.py, bundle_export.py, suite_data/*.json, suite-definitions @5/@4, docs/setup.md, codebase-map.md, tests (13 files) |
| Unchecked     | none (story Evidence line: cloud-pending under D2)  |
| Unplanned     | none (golden definition hash in `tests/test_subset_sampler.py:135` moves only by the fixture's added tolerance: dropping it reproduces the old hash `d9d805...`; ids hash unchanged) |
| Gates         | ruff check, ruff format --check, mypy, merge-bundle --check, detect-secrets (hook exclusions): pass |
| Tests         | `uv run pytest -q`: `2746 passed, 2 warnings in 194.75s`; coverage 98.48% |
