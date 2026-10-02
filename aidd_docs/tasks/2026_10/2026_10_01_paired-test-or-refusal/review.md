# Review: Two configurations on the same items receive a paired test or a refusal

## Round 1

**VERDICT: PASS**

Gates (run by the reviewer on the uncommitted tree):

- `uv run pytest -q` => `1399 passed, 2 warnings in 46.82s`, coverage 97.25% (floor 95%).
- `uv run ruff check .` => `All checks passed!`; `uv run ruff format --check .` => `535 files already formatted`; `uv run mypy src/ scripts/` => `Success: no issues found in 53 source files`.
- `grep -rn scipy src/ scripts/` => only the docstring at `comparison.py:15`; scipy sits in the `dev` group only (`pyproject.toml`), `uv.lock` adds only `scipy 1.18.1`.
- Stores: `quality-reference.jsonl` and every other committed store are unchanged; only `aidd_docs/results/README.md` (new section) is modified, plus the new `aidd_docs/results/comparisons/` (two records). The story asks for that output ("its output file under `aidd_docs/results/`").

### Acceptance, condition by condition

| # | Condition | Proved by |
|---|-----------|-----------|
| 1 | Named command writes a tracked record; nothing at read time | `comparison.py:922` `main`, `pyproject.toml` entry `wave-local-ai-v2-compare`; `test_the_command_refuses_the_committed_pair_on_thinking_policy`, `test_the_command_writes_to_the_default_comparisons_dir` |
| 2 | Reference/candidate, `reference_run_id`/`candidate_run_id` plus side selector, candidate minus reference | `comparison.py:719-734` (`*_selector`, `difference_convention`), `:774-778`; `test_the_committed_pairs_with_their_constraint_present_reproduce_the_epic` (shared run id split by `model_id`) |
| 3 | Test by scoring kind, named with its reason | `TEST_BY_SCORING_KIND` `:54`, `scoring_kind` `:511`, `TEST_CHOSEN_BECAUSE`; `test_a_classification_suite_routes_to_mcnemar_without_the_caller`, `test_a_translation_suite_routes_to_wilcoxon_without_the_caller` |
| 4 | Suite id/version, paired ids, `compared_field`, statistic, p, direction, effect size + formula, paired n, tie and zero counts, one-sided items named to a side | `:718-805`, `:270-338`, `:397-479`; `test_unpaired_items_are_counted_and_named_to_their_side`, `test_mcnemar_reproduces_the_epics_published_pairs` |
| 5 | Wilcoxon conventions named (Pratt, exact up to 50 non-zero, no continuity correction); both-failed tie kept | `:407-422`; `test_wilcoxon_keeps_a_both_failed_tie_under_pratt` (scipy oracle, zero ranked, W+ 32 / W- 22) |
| 6 | Differing-field set from rows; confound => observation; gpu vs cpu_only well-formed | `differing_fields` `:619`, `_comparison_kind` `:657`; `test_a_gpu_against_cpu_only_row_of_one_model_is_an_observation`, `test_a_confound_outside_the_dimension_makes_an_observation` |
| 7 | Refusal list, absence never a match, partial row set not a refusal | `refusals` `:558`; parametrized `test_a_binary_comparison_is_refused_naming_its_field` (suite_version, max_output_tokens, thinking_policy differs/absent, suite_level), `test_a_differing_metric_version_on_a_graded_row_is_refused`, `test_a_scoring_kind_mismatch_is_refused_naming_it`, `test_a_constraint_absent_on_both_sides_is_never_a_match` |
| 8 | Named null reasons (no discordant, empty cell, all zero, n below minimum) | `test_mcnemar_publishes_named_reasons_never_numbers`, `test_wilcoxon_publishes_named_reasons_never_numbers`, `test_no_paired_item_is_not_comparable` |
| 9 | One verdict among the three literals, raw inputs beside it | `_verdict` `:680`, `VERDICT_*` `:85-87`; routing tests assert `distinguishable` / `not distinguishable`, refusal tests `not comparable` |
| 10 | Family of one, adjusted p = raw p, stated | `build_family_record` `:812`; `test_a_family_of_one_states_its_adjusted_p_and_is_deterministic` |
| 11 | Re-run over the bundle alone is identical | `test_a_published_record_recomputes_from_the_bundle_alone` (byte equality per committed record) |

Statistics checked by hand: McNemar `2 * sum_{k<=min(b,c)} C(b+c,k) / 2^(b+c)` capped at 1 gives 6/16 = 0.375 (b=1, c=4) and 44/64 = 0.6875 (b=2, c=4); the sign-flip count table is a correct 0/1 subset-sum over doubled ranks; the normal branch's Cureton mean/variance and `sum(t^3 - t)/48` tie term are correct; scipy `binomtest` and `wilcoxon` (exact, Pratt, asymptotic) oracles agree.

### Judgement calls (plan.md Decisions)

- `compared_field` kept on `verdict.py`'s meaning plus a declared `compared_dimension`: satisfies the acceptance. Read literally ("differ on more than the compared field", with `compared_field` = `correct`) every comparison would be an observation, so a declared axis is the only coherent reading; it matches PRD Methodology 24's "suite crossed with compared dimension".
- `model` dimension absorbing provider/endpoint/template/sampling/`fiche_hash`: consistent with the epic's own thesis (its "pairable" Qwen-vs-mistral pairs are local vs cloud). It does read looser than epic success check 11 ("differ on more than one row field") for `sampling` and `fiche_hash`; nothing is hidden since `differing_fields` still lists them. Owner should confirm (non-blocking 1).
- Absence rule: applied to the four constraints and the metric triple as the acceptance and Q4 (a) require; extended to suite identity (stricter, conservative, no committed pair affected); not applied to `suite_level`, matching "two different suite levels". Verdict strings with spaces are the acceptance's own literals; `verdict.py`'s `not_comparable` is a different (reproduction) vocabulary.

### Blocking findings

None.

### Non-blocking findings

1. `comparison.py:223-238`: `sampling` and `fiche_hash` inside the `model` dimension let a same-provider pair differing in temperature or machine read as a clean `test`; flag for the owner against epic success check 11.
2. `comparison.py:680-687`: an `observation` keeps a p-based `distinguishable` verdict; a renderer showing only `verdict` would present a confounded pair as a finding. Consider a distinct verdict or require consumers to read `comparison_kind`.
3. `comparison.py:949`: `rows_source` is the caller's path string, so `--rows ./aidd_docs/...` or an absolute path yields a different `family_id` and a second record for the same comparison.
4. Tests: no case for the metric identity absent on a graded row, nor for `prompt_set_hash`, `stop_sequences` or `context_length` refusals individually (same code path as tested fields).
5. `compared_field` refusal can only ever fire together with `scoring_kind`, since it is derived from it; harmless but redundant.

## Round 2

**VERDICT: PASS**

Scope: the two post-review fixes for Round 1 non-blocking findings 2 and 3.

- Gates: `uv run pytest -q` => `1401 passed, 2 warnings in 45.24s`, coverage 97.25%; ruff check, ruff format --check (536 files) and mypy all pass.
- (a) `rows_source_name()` (`comparison.py:867`) resolves the path, then stores it relative to the working directory when it lies under it, otherwise as an absolute POSIX path. `test_two_spellings_of_one_rows_file_give_one_family_id` gives byte-identical records for 3 spellings; `test_a_rows_file_outside_the_working_directory_is_named_absolutely` covers the fallback. Acceptance 11 (identical re-run) is still proved by `test_a_published_record_recomputes_from_the_bundle_alone`.
- (b) `_verdict` (`comparison.py:682-692`) returns `not comparable` for an observation, and the p stays in `result`. `VERDICT_RULE` states this. Proved by `test_a_gpu_against_cpu_only_row_of_one_model_is_an_observation` and `test_a_confound_outside_the_dimension_makes_an_observation` (p <= 0.05, verdict `not comparable`). This fits acceptance 6 ("never as a clean test") and 9 (one of the three literals, raw inputs kept beside it).
- Regenerated records: `comparisons/` holds exactly `classification-support-routing@2.model.d4641d06a525.json` (5e13166d) and `...2ef9fd3581d2.json` (d20afbda), both rows_source `aidd_docs/results/quality-reference.jsonl`, both `not comparable`. The old `7ab16cb6`/`e03515e1` files are gone, and outside this review no file references them. The README table names the new files.

Blocking findings: none. Round 1 non-blocking 1, 4 and 5 still stand (owner confirmation for `sampling`/`fiche_hash` in the `model` dimension; missing per-field refusal tests; redundant `compared_field` refusal).
