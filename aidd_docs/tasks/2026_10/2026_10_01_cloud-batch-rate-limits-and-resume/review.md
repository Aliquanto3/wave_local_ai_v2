# Review: a-publication-size-cloud-batch-survives-its-rate-limits-and-resumes-per-item

- **Verdict**: changes-requested
- **Diff**: `HEAD...working tree` (branch `feat/ready-stories-unattended`, uncommitted)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_02
- **Findings**: 1 critical, 2 warning, 3 minor

## Phases

### Phase 1 — The budget rule and the two row fields (schema "17")

- [x] Budget grows with item count, rule is configuration, budget readable off rows — `retry.py:60` `derived_retry_budget`, `settings.py:101-102,461-481`; `test_the_derived_budget_grows_with_the_item_count`, `test_a_twenty_item_cloud_batch_runs_under_four_retries_and_says_so`, `test_a_hundred_item_cloud_batch_survives_429s_a_fixed_four_would_not`
- [x] Budget scaling never masks a refusal — `test_a_refusal_is_never_retried_whatever_the_budget` (test_retry, generic), `test_a_refusal_mid_batch_is_never_retried_whatever_the_budget` (quality_cli, budget 1000, `ModelUnavailableError`); family collision and unparseable reply stay on pre-existing paths that never enter `call_with_retry` (`test_judge.py:358`, `test_judge.py:91`)
- [x] Schema "17" with reason, gate refuses malformed budget/partial and a partial row carrying a score — `row_contract.py:120-133,637-705`; 11 new `test_row_contract.py` tests

### Phase 2 — Per-item resume and partial persistence in the suite CLI

- [x] Resume calls only missing items, key `(run_id, provider, task_suite, item_id)` unique — `results.py:224` `resume_missing_items`; `test_a_hundred_item_batch_interrupted_then_resumed_pays_for_no_item_twice` (63 calls, 100 distinct ids, 0 answered twice)
- [x] Already-written rows unchanged; completed batch score equals uninterrupted — `quality_cli.py:1056-1093`; same test asserts `rows[:37] == before`, equal `suite_accuracy`/`language_breakdown`/`failure_counts`
- [ ] Resume only mixes rows of the same batch configuration — prior rows are aggregated without checking `model_id`/`suite_version`/`prompt_set_hash`/`prompt_variant_*`/`roster_entry_id` (see Findings 1)
- [x] Still-incomplete batch stays partial, names provider and item, no headline — `test_a_resume_that_fails_again_stays_partial_and_names_the_new_item`, `test_a_mid_batch_failure_persists_the_answered_items_as_a_partial_batch`

### Phase 3 — The same rule in the judged probe

- [x] One rule over both CLIs; judged resume re-pays no recorded judge call; agreement, headline, contested set equal uninterrupted — `judge_probe.py:465-494,941-1020`; `test_a_judged_batch_resumed_mid_way_issues_no_judge_call_already_recorded`, `test_a_judge_failure_mid_batch_persists_the_judged_items_as_partial`, `test_every_probe_row_names_the_budget_derived_from_the_items_it_judges`

### Phase 4 — Docs and the 100-item evidence

- [x] Evidence recorded — `evidence/stubbed-hundred-item-resume.md` (38 + 63 calls, 0 items answered twice, 0.6600 = 0.6600)
- [x] Docs name the rule and fields — `aidd_docs/memory/cli.md:63`, `CHANGELOG.md:14-21`, `aidd_docs/results/README.md`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 critical | code (backend) | 2, 3 | `quality_cli.py:1072-1093`, `judge_probe.py:940-975`, `results.py:224` | `--resume` folds prior rows' per-item outcomes into the published suite score with no check that they were produced under the same configuration. Realistic path: Mistral model retired mid-batch (PRD AC failure case) → partial; operator bumps `mistral_client.MODEL` (or the suite file's `suite_version`, or `ROSTER_ENTRY_ID` for local) and resumes → one "complete" batch whose rows carry two `model_id`/`suite_version` values and whose `suite_accuracy` mixes both. The old code could not mix (partial was refused). | Before running missing items, compare the prior batch rows' identity fields (`model_id`, `suite_version`, `prompt_set_hash`, `prompt_variant_id`/`_version`, `sampling`, `roster_entry_id`; judge model ids on the probe) with this invocation's and refuse the resume naming the differing field; add one test per CLI. |
| 🟡 warning | fit | 2 | `comparison.py:146-147,783-800` | `partial_failure` is excluded from differing fields and a side holding only partial rows still gets a McNemar/Wilcoxon p-value over its first-N items (unpaired items listed, but the partial state is not named). Not a headline score, but a test over a non-random prefix. | Refuse (or mark as observation naming `partial_failure`) a side whose batch has no row with `partial_failure` null. |
| 🟡 warning | rot | 1 | `bundle_export.py:386-391`, `:498`, `:549` | Empty-cell docs for `suite_accuracy` ("Not an exact-match row."), `suite_score`, `judged_headline_score` now misdescribe a partial row's null. | Extend each `empty` text with "or the batch was partial (see partial_failure)". |
| 🟢 minor | rot | 1 | `aidd_docs/backlog/tech-debt.md:92` | Open debt row about `CLOUD_RETRY_MAX_ATTEMPTS` naming; the variable is removed (replaced by `CLOUD_RETRY_MIN_RETRIES`, which is named as retries). | Close the row as resolved by this story. |
| 🟢 minor | fit | 2 | `read_model.py:362-370` | `partial_failure` is not rendered; a fully partial card shows an absent score with no reason. | Pitch epic decision; note only. |
| 🟢 minor | code (performance) | 2 | `tests/test_quality_cli.py:1758,1791` | ~17.5 s added by two 100-item tests; profile shows 9.2 s of 10.3 s in file close (`append_row`, 912 closes), not sleep (`time.sleep` is patched, `test_quality_cli.py:298`). | Acceptable; optionally batch-write in a fixture if suite time matters. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 89% (8/9) |
| Files checked | settings.py, retry.py, results.py, row_contract.py, quality_cli.py, judge_probe.py, scoring_rules.py, suite_registry.py, read_model.py, comparison.py, bundle_export.py, verdict.py, tests (retry, results, quality_cli, judge_probe, row_contract, read_model, settings), cli.md, CHANGELOG.md, evidence |
| Unchecked     | Resume refuses a configuration-mismatched batch — fix |
| Unplanned     | none (`scoring_rules.BATCH_AGGREGATES` and `suite_registry` aggregate split trace to the plan's "same function on both paths" decision) |

Gate evidence: `uv run pytest -q` → `1618 passed, 2 warnings in 68.66s`, coverage 97.69%; `ruff check` → `All checks passed!`; `ruff format --check` → `575 files already formatted`; `mypy src/ scripts/` → `Success: no issues found in 54 source files`. Touched test files re-run with `HTTPS_PROXY`/`HTTP_PROXY=http://127.0.0.1:9` → `441 passed`: no real HTTP call. Cost/token totals per resumed segment: the acceptance asks for no batch total, so the plan's tradeoff stands.

## Round 2

- **Verdict**: approve (VERDICT: PASS)
- **Date**: 2026_10_02
- **Findings**: 0 critical, 0 warning, 2 minor

| Round 1 finding | Status | Evidence |
| --- | --- | --- |
| 🔴 resume mixes configurations | fixed | `results.py:267` `resume_configuration_conflict` (absent field counts as differing); `quality_cli.py:270,542-597` checks local/mistral/google before build_flags, server or any call, `main` exits 1 on `ResumeConfigurationError` (`:229`); `judge_probe.py:444-445,568-621` adds judge model ids, runs before both `check_model_available` pre-flights (`:414`). Tests: `test_a_resume_over_rows_of_another_configuration_is_refused_writing_nothing` (9 fields, asserts no server, no call, store unchanged), `test_a_resume_after_the_cloud_model_changed_is_refused`, `test_a_resume_under_the_same_configuration_completes_the_batch`, `test_a_probe_resume_over_rows_of_another_configuration_is_refused`, `test_a_probe_resume_under_the_same_configuration_completes_the_batch` |
| 🟡 comparison scores a partial side | fixed | `comparison.py:669-684,822-838`: a side whose rows all carry `partial_failure` becomes an observation naming it. A resumed segment that fails again writes rows that are themselves partial (`quality_cli.py` `_score_and_write`, `judge_probe.py` local batch), so an incomplete resumed side is still all-partial; only a completed resume adds rows with `partial_failure` null. Tests: `test_a_side_whose_batch_stayed_partial_is_an_observation_naming_it`, `test_a_batch_completed_by_resume_is_still_a_clean_test` |
| 🟡 bundle empty-cell text | fixed | `bundle_export.py` `_PARTIAL_SCORE_DOC` appended to `suite_accuracy`, `language_breakdown`, `suite_score`, `score_breakdown`, `judged_headline_score` |
| 🟢 tech-debt `CLOUD_RETRY_MAX_ATTEMPTS` | fixed | `tech-debt.md` row closed; no reference left in src, `.env.example`, `docs/` |
| 🟢 tech-debt "positional 6-tuple" closure | verified true | `_mistral_batch`/`_google_batch` return `_CloudBatch` (`TypedDict`), call site reads by key |

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | 2 | `comparison.py:669` | Completeness is "some row has `partial_failure` null", not item coverage: a process killed inside the append loop of a completing segment leaves a not-all-partial incomplete side that still gets a plain test (append-loop crash, same as before this story). | Optionally derive completeness from item coverage against the suite. |
| 🟢 minor | code (backend) | 2 | `tests/test_quality_cli.py` | No test resumes a partly written **Google** batch under the same configuration (a false refusal would go unseen). The constants match by reading `quality_cli.py:758` and `:125`. | Add one same-config Google resume test. |

| Metric | Value |
| --- | --- |
| Verified | 100% (9/9) |
| Gate | `uv run pytest -q` → `1635 passed, 2 warnings in 74.49s`, coverage 97.71%; ruff `All checks passed!`; format `576 files already formatted`; mypy `Success: no issues found in 54 source files` |
| No HTTP | quality_cli, judge_probe, comparison, results tests with `HTTP(S)_PROXY=http://127.0.0.1:9` → `253 passed` |
