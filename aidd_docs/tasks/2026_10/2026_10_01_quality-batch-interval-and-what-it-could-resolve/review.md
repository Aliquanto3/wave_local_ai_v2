# Review: Every quality batch publishes its interval and what it could resolve

## Round 1

Reviewed against the story's acceptance as amended in `ec8839b` (exact-binomial reference within 1/n, Wilson coarse check at n=100, MDE = 95% half-width). Change under review: the uncommitted working tree of `wave_local_ai_v2-impl` (14 modified files, `score_interval.py`, `test_score_interval.py`, task folder untracked).

VERDICT: PASS

### Gates

- `uv run pytest -q`: `1972 passed, 2 warnings in 142.72s`, coverage 98.03% (floor 95%).
- `uv run ruff check .`: all checks passed. `uv run ruff format --check .`: 618 files already formatted. `uv run mypy src/ scripts/`: no issues in 58 source files.
- Committed stores untouched: `git status` shows only `aidd_docs/results/README.md` modified under `aidd_docs/results/`, with no `*.jsonl` changes.

### Acceptance, condition by condition

1. **Interval on the suite score and each language cell, exact-match and graded, at development level, with `indicative` kept.** Met. Both aggregates attach it (`scoring_rules.py` `aggregate_exact_label_match` / `aggregate_chrf_against_reference`). Proved by `test_scoring_rules.py::test_an_exact_match_batch_carries_its_interval_over_every_item` and `test_a_graded_batch_carries_its_interval_over_every_item`, plus `test_quality_cli.py::test_every_row_of_a_batch_carries_one_interval_that_replays_from_the_rows[both suites]`, which also asserts `suite_level == "development"` and `indicative`. The publication level goes through the same aggregate, so it is covered by construction rather than by a dedicated test.
2. **Six-value header, versioned draw-procedure id with a published definition, suite unstratified and language stratified.** Met. The header is in `score_interval.interval_block` and pinned by `test_block_carries_the_six_values_beside_the_cells`. Stratification is pinned by `test_suite_resamples_unstratified_and_a_language_within_itself`. The definition (item order, draw order, rejection, statistic, ties, type-7 interpolation, MDE) is the `score_interval.py` module docstring. It is reachable from the bundle dictionary entry for `score_interval.draw_procedure_id` ("defined in score_interval.py"), from the CHANGELOG and from the results README. The bulk `getrandbits(32*m)` read is an implementation of that definition, not a part of it. `test_the_bulk_draw_is_the_one_call_per_draw_procedure` (11 sizes x 3 seeds) pins it equal to the one-call-per-draw loop. `test_hand_computed_interval_on_a_small_fixture` pins the seed-7 bit stream and a hand-derived resample set.
3. **A failed generation stays in the set as a zero.** Met. In `test_an_exact_match_batch_carries_its_interval_over_every_item`, empty generations go into the batch, `failure_counts["empty"] > 0`, and the test asserts block == the interval over every item with zeros and `n == len(items)`. The graded case asserts `item_score == 0.0` on the failure.
4. **Identical block on every row; no published row rewritten.** Met. The equality check is in the CLI test above. `test_a_hundred_item_batch_interrupted_then_resumed_pays_for_no_item_twice` asserts that the resumed rows equal the uninterrupted block with `n == 100`, and that the 37 rows written partial keep `score_interval is None`.
5. **MDE = half-width of the 95% interval, read off the same resample.** Met. `bootstrap_cell` computes it, and `test_minimum_detectable_effect_is_the_half_width_of_the_same_resample` checks it.
6. **A value or exactly one reason; each reason comes only from its own state.** Met. The rule is decided on the item values (`n == 0` gives `no_items`; all values equal gives `zero_width`), never on the computed width. Proved by `test_a_constant_cell_publishes_the_zero_width_reason[1.0, 0.0, 0.5]`, `test_an_empty_cell_publishes_its_reason_not_an_interval_around_zero`, `test_each_reason_is_produced_by_its_own_state_only` (19/20 is defined), and the row-contract xor tests (`test_an_interval_cell_is_values_or_one_reason_never_both`). Analytically, a non-constant cell cannot collapse to zero width: the largest single-value bootstrap mass is about 0.37, well under 0.95.
7. **Bit-for-bit replay from the recorded block; a changed seed changes the interval.** Met. `test_a_recorded_block_replays_bit_for_bit`, `test_a_changed_seed_changes_the_interval`, `test_replay_refuses_a_method_or_procedure_it_does_not_implement`, and the CLI replay from the rows alone.
8. **Exact binomial within 1/n at n=20 and n=100, p=0.80; Wilson within 0.05 at n=100.** Met. `test_bounds_equal_the_exact_binomial_within_one_grid_step[20,100]` and `test_wilson_is_a_coarse_sanity_check_at_n_100`. scipy oracles: `test_percentile_interpolation_matches_scipy_quantile` (type 7) and `test_interval_agrees_with_scipy_bootstrap_within_one_grid_step`. The conventions that differ are documented by `test_convention_the_same_seed_draws_differently_under_numpy` and `test_convention_scipy_publishes_a_zero_width_interval_we_name`. The evidence agrees: at n=20, p=0.80 the interval is [0.600, 0.950], which equals Binomial(20, 0.8) quantiles 12/20 and 19/20 exactly.
9. **Three invariants that fail loudly, including a resumed batch over different item sets.** Met. `score_interval.check_batch_invariants` runs in `quality_cli._score_and_write` before any append. Proved by the invariant tests in `test_score_interval.py`, including `test_a_resumed_batch_whose_interval_covers_other_items_fails`, and end to end by `test_quality_cli.py::test_a_batch_whose_interval_covers_other_items_is_refused_before_writing`.
10. **Standard library at runtime; scipy dev-only and never imported by `src/`.** Met. `scipy>=1.18.1` is already in the `dev` group of `pyproject.toml` (committed earlier for `comparison.py`). `test_src_imports_no_scipy` checks `src/` by AST.
11. **Declared unrendered.** Met. `read_model.QUALITY_FIELDS_NOT_RENDERED` gains `*row_contract.SCORE_INTERVAL_FIELDS`, and the read-model partition tests pass.

Evidence: the README section is an analysis over the committed `classification-support-routing` rows, with the script and output under `evidence/`. Its figures match `classification-intervals.txt`, including the eight `zero_width` cells out of twelve. Nothing is written back onto the rows.

### Points judged

- **Percentile bootstrap.** Correct. Items are taken in `item_id` order. Each cell draws from a fresh `Random(seed)`. Rejection sampling uses `n.bit_length()` bits, as CPython's own `_randbelow` does. The statistic is the `fsum` mean. Bounds are type-7 quantiles at `(B-1)q`. Ties are equal floats, so their order cannot move a bound.
- **Judge probe writes null.** Consistent with the acceptance, which scopes the interval to "the exact-match and the graded scorer alike". The epic (line 137) defers a judged-score interval until judged rows exist.
- **Interval computed twice per batch.** Correctness is unaffected. The first computation comes from `SuiteDefinition.score_items` calling the full rule over the subset, and its aggregate is discarded.
- **Suite at about 142 s.** No test in `test_score_interval.py` reaches the slowest-25 list (all under 0.72 s). The extra cost is spread across the CLI tests: about 70 ms per 20-item block, about 380 ms per 100-item block, twice per batch, over three providers. The two 100-item CLI tests take 16 s and 12 s. There is no CI timeout risk.

### Blocking findings

None.

### Non-blocking findings

1. `suite_registry.py:119` `score_items` runs the whole rule, so every batch computes and discards a 10 000-resample block over the subset. Scoring per item only (or splitting the rule into per-item and aggregate parts) would roughly halve the suite's added time.
2. `score_interval.py:146-153`: the bulk read materialises `count * 2^bits / n` words as a tuple of Python ints. At n=1000 that is about 16M ints, roughly 1 GB transient. Reading in fixed-size chunks would keep the same stream at bounded memory before any large publication suite.
3. `score_interval.py:24-26`: the docstring says the Mersenne Twister bit stream is "stable across Python versions". The Python docs only guarantee `random()` under a compatible seeder. Word it as "stable in practice, recorded by generator version, not formally guaranteed".
4. `score_interval.item_value` is used only by tests and the evidence script, while `scoring_rules.py` builds the same values inline. Use it in both aggregates so the replay values and the writer values cannot drift apart.
5. `bundle_export.py` column docs for `score_interval` overlap the first acceptance condition of the sibling story `the-tabular-export-carries-the-interval-and-the-comparison-record.md`. They are needed here, because `bundle_export` refuses undocumented fields. Note it when that story is picked up. Also, `row_contract._validate_interval_cell` accepts `no_items` with n > 0 (only the writer and the invariants enforce consistency), which is a cheap check to add later.

## Round 2

Scope: the post-review fixes for Round 1 non-blocking findings 2, 3 and 5b. Finding 1 was not done; it stays non-blocking.

VERDICT: PASS

- **Gates.** `uv run pytest -q`: `1977 passed, 2 warnings in 146.79s`, coverage 98.03%. ruff check is clean, ruff format reports 619 files already formatted, and mypy reports no issues.
- **Finding 2 (chunked read): fixed and bit-identical.** `score_interval._index_stream` reads `getrandbits(32 * 65536)` per chunk. Consecutive calls continue the same Mersenne Twister word sequence, and each chunk is unpacked little-endian in draw order, then shifted and filtered as before. The seam therefore adds no reorder and drops no word. `resample_values` streams through `islice` + `batched`, so it holds only one chunk and the 10 000 means. `test_the_bulk_draw_is_the_one_call_per_draw_procedure` now covers n=1000 and n=1025 with `count = 3 * 65536` accepted draws. That spans about 3 chunks at n=1000 (acceptance 1000/1024) and about 6 at n=1025 (acceptance about 0.5), across 3 seeds, so the seam is exercised.
- **Finding 3 (docstring): fixed.** The docstring now says that Python guarantees reproducibility only for `random()`, that `getrandbits` has been stable in practice, and that the generator version is recorded.
- **Finding 5b (row contract): fixed.** `row_contract._validate_interval_cell` refuses `no_items` at n > 0, `zero_width` at n=0, and an interval over n=0. `test_row_contract.py::test_an_interval_reason_is_only_the_one_its_item_count_names` covers all three.
- **Blocking findings:** none.
- **Non-blocking, still open:** Round 1 finding 1 (`score_items` computes a discarded block on every batch). Round 1 finding 4 (`item_value` is not used by the writers) is unchanged.
