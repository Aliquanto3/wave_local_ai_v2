# Review: Translation suite scored by chrF

- **Verdict**: changes-requested
- **Diff**: `main...feat/translation-suite`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_06
- **Findings**: 0 critical, 4 warning, 3 minor

## Phases

### Phase 1 — The chrF metric, alone and provable

- [x] `chrf` returns a float in `[0, 1]` for every pair including empty and whitespace-only ones, raises nothing, performs no I/O, and reads its parameters from named module constants `METRIC_PARAMS` derives from — `src/wave_local_ai_v2/chrf.py:47-71`, `src/wave_local_ai_v2/chrf.py:117-142`
- [x] Independently verified: an independent transcription of sacreBLEU's non-eps branch agrees over 3010 pairs (max abs diff `1.1e-16`), including the three live-run pairs; one fully hand-worked vector (`chrf("AB C", "AB D") = 7/18`) matches to `1e-15` — sacreBLEU's `CHAR_ORDER 6` / `BETA 2` / `whitespace False` / no-lowercase defaults confirmed against the upstream source
- [x] Three hand-computed vectors pass, one exactly; whitespace invariance; the `beta = 2` asymmetry pinned; fast gate and `pytest` pass — `tests/test_chrf.py:21-81`, 741 passed, `ruff`/`ruff format`/`mypy` clean

### Phase 2 — The translation suite and its graded scorer

- [x] The suite passes `gate_suite` with no indicative reason, 21 hand-written items in exactly three directions, each source language at 33% — `src/wave_local_ai_v2/translation_suite.py:121-281`, `tests/test_translation_suite.py:15-50`
- [x] It declares its own id, version, prompt-set hash (through the shared `prompt_set_hash`) and three generation caps — `src/wave_local_ai_v2/translation_suite.py:39-53`, `src/wave_local_ai_v2/translation_suite.py:287`
- [x] A graded item's score is a chrF in `[0, 1]`; an empty or truncated generation is `0.0` under its named reason and stays in the mean; the per-language breakdown reports score, n and the indicative mark — `src/wave_local_ai_v2/scoring.py:274-382`, `tests/test_scoring.py:290-466`
- [x] `suite_snapshot` writes two files, the translation one carrying `reference` and `target_language` per item, and the classification one is byte-identical to the tracked copy — re-ran `uv run python -m wave_local_ai_v2.suite_snapshot`, `git status` clean
- [x] The new and extended tests pass and coverage stays above the gate — 96.21% against the 80% floor

### Phase 3 — The graded row, the verdict, and the `--suite` seam

- [x] A partial graded block is refused naming every missing field; a graded row with a non-null `correct`/`suite_accuracy`, or a named failure with a non-zero score, is refused; classification and judged probe rows still validate — `src/wave_local_ai_v2/row_contract.py:501-592`, `tests/test_row_contract.py`
- [x] Two runs of the same translation batch return `reproduced` decided on `item_score`, the block names `compared_field`, and a batch with nothing comparable returns `not_comparable` with a reason — `src/wave_local_ai_v2/verdict.py:220-312`; confirmed on the live store, run `696b5376` local and google both `reproduced` / `compared_field: item_score`
- [x] A `--resume` under one suite never skips on another suite's rows — `src/wave_local_ai_v2/results.py:71-113`, `tests/test_quality_cli.py` `test_a_resume_under_one_suite_never_skips_on_another_suites_rows`
- [x] No flag behaves exactly as before; `--suite translation` writes one graded row per item per provider into the same store; an unrecognised suite is refused by argparse naming the valid values — `src/wave_local_ai_v2/quality_cli.py:286-340`
- [x] The full suite passes, the gate passes, coverage holds, and no test starts a real server or makes a live call — 741 passed, every provider call stubbed

### Phase 4 — The live run and the record it leaves

- [x] One run produced rows for local and every cloud subject that answered; `wave-local-ai-v2-validate` exits 0; a second run returns `reproduced` on `item_score` for the local batch; the absent provider is named with the line that says why — 84 translation rows over two run ids, local + google, Mistral's `429` quoted verbatim in `aidd_docs/results/README.md`
- [x] Every published number recomputes from the row itself: all 84 rows re-scored from their own `reference_output`/`subject_output`, 0 mismatches; both `suite_score` values equal the mean of their batch (local 0.7691, google 0.8400)
- [x] The CHANGELOG names the schema bump, the new modules, the new flag and every divergence; the results README carries the run ids, the per-provider suite scores and the single-reference caveat; `cli.md`, `codebase-map.md` and `architecture.md` describe the shipped behaviour with no stale one-hardwired-suite claim — `CHANGELOG.md:12-99`, `aidd_docs/results/README.md:123-239`, `aidd_docs/memory/cli.md:16-71`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | rot | 4 | `aidd_docs/results/README.md:223-229` | The "Reading these scores" table publishes each item's real `item_score` beside a model output with the `<think>\n\n</think>` envelope silently removed. Recomputing chrF from the quoted text gives 0.4205 / 0.4997 / 0.5333, not the 0.408 / 0.476 / 0.513 printed. The stored rows are correct (`subject_output` carries the envelope, verified on all 84 rows); it is the human-readable record that cannot be reproduced from what it prints, in the one section whose purpose is to let a reader check a number. | Quote the completion as stored, or keep the trimmed text and say the `<think>` envelope is elided, giving the enveloped score as published and the trimmed-text score beside it. |
| 🟡 | rot | 4 | `docs/setup.md:299-300` | `sacrebleu --chrf-char-order 6 --chrf-beta 2` computes **BLEU**: sacreBLEU's CLI defaults to `bleu` and selects a metric with `-m/--metrics`, so the two chrF flags parse and are then unused. An auditor following the instruction gets a different metric with no error. | `sacrebleu -m chrf` (the two flags are already the defaults and can go, or stay as documentation of the parameterisation). |
| 🟡 | rot | 4 | `docs/setup.md:307-308` | "Translation adds ~5 minutes of Google pacing over the classification suite's (21 items instead of 20, at two Google calls each)" contradicts the branch's own measurement. One extra item is two extra paced calls, ~8 s; the whole google batch is ~3 minutes per `aidd_docs/results/README.md:159-161`. | State the measured figure: the translation batch costs ~3 minutes of Google pacing, ~8 s more than classification. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/verdict.py:203-217` | `select_quality_references` still keys on `(model_id, suite_version, seed)` — the same cross-suite gap D6 fixed for `resume_skip_reason`, left in the sibling path. One store now holds two suites and so can a reference file; the two suite versions differ today (`"2"` vs `"1"`) only by coincidence, and when they align a mixed reference file makes `quality_verdict` collect both suites' rows, trip the `unmatched_items` guard, and return `not_comparable` for a batch that reproduced perfectly. It fails safe, never a false `reproduced`. | Add `task_suite` to the filter alongside `model_id`/`suite_version`/`seed`, and say in the docstring why the suite is part of the key. |
| 🟢 | rot | 4 | `CHANGELOG.md:88` | "Four divergences from the story" undercounts the plan's and the story's own table of six. D5 (the verdict deciding on `item_score`) and D6 (the `task_suite`-aware resume) are both described earlier in the same entry, so nothing is missing — only the count is wrong. | Say "six" and fold D5/D6 into the enumeration, or drop the number. |
| 🟢 | code | 3 | `src/wave_local_ai_v2/quality_cli.py:196-197,229-230` | Both `score_batch` implementations take `items: Sequence[Any]`, so `item["reference"]` in `_score_translation_batch` and `score_suite_by_language(items, ...)` in the classification one are unchecked by mypy. The `Any` is there to sidestep `ScoreBatch`'s parameter contravariance, but it removes typing exactly where the two suites' item shapes diverge. | Narrow inside the function (`items = cast(Sequence[TranslationItem], items)`) so the body is checked while the callable still matches `ScoreBatch`. |
| 🟢 | code | 3 | `src/wave_local_ai_v2/quality_cli.py:206,247` | The two scorers read `classification_suite.MAX_OUTPUT_TOKENS` / `translation_suite.MAX_OUTPUT_TOKENS` directly while the cap actually sent to providers and written on the row comes from `spec.max_output_tokens`. The same value is declared twice on two paths; a `SuiteSpec` built with a different cap would truncation-classify against the module constant instead of the one the run used. | Pass the spec's cap into `score_batch` (widen the callable), or note on `SuiteSpec` that `max_output_tokens` and the scorer's own constant must stay the same module's. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (13/13)                                      |
| Files checked | `src/wave_local_ai_v2/chrf.py`, `translation_suite.py`, `scoring.py`, `row_contract.py`, `verdict.py`, `results.py`, `judge_probe.py`, `quality_cli.py`, `suite_snapshot.py`, `tests/test_chrf.py`, `test_translation_suite.py`, `test_scoring.py`, `test_row_contract.py`, `test_verdict.py`, `test_results.py`, `test_quality_cli.py`, `test_suite_snapshot.py`, `CHANGELOG.md`, `README.md`, `docs/setup.md`, `aidd_docs/results/README.md`, `aidd_docs/memory/cli.md`, `aidd_docs/memory/codebase-map.md`, `aidd_docs/memory/architecture.md`, `aidd_docs/backlog/stories/translation-scoring-extends-deterministic-coverage.md` |
| Unchecked     | none                                              |
| Unplanned     | `aidd_docs/backlog/tech-debt.md` gains the `<think>`-envelope entry — phase 4 task 1.6 sanctions it as a live finding filed rather than patched; `aidd_docs/results/suite-definitions/translation-business-short-form.json` is committed under phase 2 task 3 and cited by phase 4 |
