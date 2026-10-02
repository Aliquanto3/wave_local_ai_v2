# Review: each quality item records the tokens and the first-token time its generation took

## Round 1

VERDICT: PASS

Contract: the story text on `docs/slice-remaining-epics` (order 10), owner answer Q24 (a).

### Gates

- `uv run pytest -q`: `1688 passed, 2 warnings in 80.29s`, coverage 97.76% (floor 95%).
- `uv run ruff check .`: all checks passed. `uv run ruff format --check .`: 582 files already formatted. `uv run mypy src/ scripts/`: no issues in 54 files.
- `uv run wave-local-ai-v2-validate` on `aidd_docs/results/quality-reference.jsonl` (80 rows) and `runtime-reference.jsonl` (2 rows): exit 0. Committed rows are below "18". `validate_row` runs only at write time, so they are never re-gated against the new required fields. `git status` shows no committed store or comparison record touched. `test_a_published_record_recomputes_or_is_unedited` still passes, so the score records keep their shape: `compared_quantity` is added only off the default (`comparison.py` `_family_definition`, `compare_sides`).

### Acceptance, one by one

1. Q24 (a): per-item TTFT and tokens are paired, and energy stays per batch. Met. `comparison.py` `MEASUREMENT_QUANTITIES`, `QUANTITY_ENERGY`, `_batch_observation`.
2. Per-item tokens and TTFT, with a source label, a single-generation label, and null with a reason (never zero). Met.
   - Parsing: `timings.parse_item_measurement`.
   - Gate: `row_contract._validate_item_measurement`, which requires exactly one of a value and its reason, a source only beside a TTFT, and the kind constant.
   - Writers: `quality_cli._score_and_write`, `judge_probe._run_local_batch`.
   - Tests: `test_each_local_row_carries_its_own_engine_figures`, `test_a_local_answer_without_timings_publishes_a_null_ttft_with_its_reason`, `test_an_unreported_value_is_null_with_its_reason_never_zero`, `test_a_null_value_without_its_reason_is_refused`, `test_a_source_without_a_ttft_is_refused`.
3. The first generation is marked. Met. `item_first_in_batch=position == 0` in both writers. `test_each_local_row_carries_its_own_engine_figures` asserts `is (n == 0)`, and `test_a_cold_first_item_is_excluded_with_a_selector` shows the exclusion.
4. Paired test over per-item tokens and TTFT, with the scoring-kind rule extended. Met.
   - Code: `SCORING_KIND_CONTINUOUS` maps to `TEST_WILCOXON` in `TEST_BY_SCORING_KIND`, with its own `CHOSEN_BECAUSE_BY_SCORING_KIND` entry.
   - Tests: `test_a_variant_pair_on_output_tokens_is_a_wilcoxon_over_identical_items` (scipy oracle, 12 identical item ids, unpaired 0) and `test_a_ttft_pair_is_a_wilcoxon_too_and_its_null_items_go_unpaired`. Mixed TTFT sources and rows below "18" are refused.
5. Energy is an observation with the reason written. Met. `ENERGY_NO_PAIRED_TEST_REASON` carries the tracker-resolution reason, and the record shows two batch values and their difference. Tests: `test_an_energy_difference_is_an_observation_that_says_why_no_test`, `test_an_energy_side_with_two_batch_values_has_no_difference`. The real record is in `evidence/comparisons/*energy_kwh*.json`.

### Points judged

- `item_ttft_ms = timings.prompt_ms`: accepted.
  - It is the same quantity and `server_reported` label the runtime row's `ttft_ms` already uses (`timings.parse_timings`), so the `ttft_source` discipline holds.
  - My understanding of llama-server (I could not confirm it against the source in this session): the prompt-processing span ends when the first token is sampled (`n_decoded == 1`). If so, it includes the first token's decode and sampling, and excludes HTTP, tokenization and queue time.
  - The docs say exactly what is read: `timings.prompt_ms`, uncached tokens only, not Methodology 6's figure.
- The evidence uses two baseline runs instead of order 4's pair. No acceptance condition is left unproved:
  - The paired output-token record over a variant pair is proved by the constructed test.
  - The real run proves the fields on real engine output.
  - The order 4 pair, and its figures in `aidd_docs/results/README.md`, stay pending evidence for order 4. Log this as evidence pending, not as a gap.
- `item_prompt_tokens_cached`: justified, not scope creep. The live run shows 37 cached tokens per item from item 2 onward, so `prompt_ms` times only the uncached part. Without the count, a reader cannot read a variant's TTFT difference.

### Non-blocking

1. `comparison.py` `_batch_observation`: a side whose energy is null (tracker unavailable) is reported as `no_single_batch_value_on_a_side`. Null energy should get its own reason.
2. An energy-only family prints `1 tested ... Holm over 1` and enters Holm as p = 1, although no test ran. This matches the documented rule, but the console wording misleads.
3. The `item_ttft_ms` field doc (`bundle_export.py`) and the README could add "server-side, ends at the first sampled token, excludes HTTP and queue time" to make the measured span explicit.
