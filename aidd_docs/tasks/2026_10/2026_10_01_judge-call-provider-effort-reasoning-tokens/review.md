# Review: Every judge call names who answered, its reasoning effort, and its reasoning tokens

## Round 1

- **Verdict**: changes-requested (VERDICT: CHANGES-REQUIRED)
- **Diff**: `116a3ad...working tree` (12 modified files, untracked task folder)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_01
- **Findings**: 1 critical, 2 warning, 3 minor
- **Gates**: `uv run pytest -q` => `1052 passed, 2 warnings in 30.92s`, coverage 95.81%; `ruff check` => `All checks passed!`; `ruff format --check` => `480 files already formatted`; `mypy src/ scripts/` => `Success: no issues found in 45 source files`

## Phases

### Phase 1 — The five record fields, the two backends, and the writer gate (schema "13")

- [x] Story AC1: record names the answering provider, response-named else direct endpoint — `judge_backends.py:88-89,155-156`; `test_judge.py:465` (Mistral), `test_judge.py:516` (Google); `response` branch exercised by stub only (`test_row_contract.py` `test_a_record_answered_as_bound_read_from_the_response_validates`), acceptable since neither body names a provider
- [x] Story AC2: no fallback, mismatch refused at write naming both — `row_contract.py:559-573`; `test_judge.py:564`, `test_row_contract.py` `test_a_record_answered_by_another_provider_is_refused_naming_both`; no-reissue is the order-5 contract, backends still catch nothing
- [x] Story AC3: effort as sent, `not_sent` when none — `judge.py` `REASONING_EFFORT_NOT_SENT`; whole-request-body assertions `test_judge.py:465,516`
- [x] Story AC4: reasoning tokens apart from output, null with reason never zero — `google_client.py:242-248`, `judge_backends.py:93-94,158-163`, writer pairing check `row_contract.py:592-606`; `test_judge.py:516`, `test_google_client.py` `test_an_absent_thoughts_count_is_none_not_zero`, `test_row_contract.py:591,598`
- [x] Story AC6: additive under `SCHEMA_VERSION` bump, missing field refused by name, deterministic row unchanged — `row_contract.py:90`; `test_row_contract.py:547` (parametrized over five fields), `test_row_contract.py:510,921`

### Phase 2 — Reasoning tokens and their billing basis in `judge_cost`

- [x] Inside-output reasoning never moves the cost — `cost.py:228-229`; `test_cost.py:231,288`
- [x] Beside-output reasoning priced once — `cost.py:232-233`; `test_cost.py:247`
- [ ] A null beside-output count nulls that provider's cost — implemented (`cost.py:230-231`, `test_cost.py:265`) but this planned rule regresses the shipped judge cost on every real Google call; see Findings row 1
- [x] `cost_total` on the row stays the subject's — `judge_cost` remains its own block; `tokens_out_total` not folded (`test_cost.py:247`)

### Phase 3 — Stable judge-prompt prefix, resume read-back, stubbed evidence

- [x] Story AC7: byte-identical prefix ending after the rubric, misordered shell fails a test — `test_judge_protocol.py:202,214,251`
- [x] Story AC8: resume reads new fields back unchanged, re-issues nothing — `test_judge_probe.py:775`
- [x] Evidence: stubbed judged row read back — `evidence/stubbed-judged-row-read-back.json` (but see Findings row 5)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | functional | 2 | `cost.py:230-231`, `judge_backends.py:158-163` | The pinned Google judge never emits `thoughtsTokenCount` (memory `google-ai-studio-api.md:69`: "totalTokenCount always equalled prompt + candidates"), so every real Google judge cost, and the row's aggregate `judge_cost.cost_total`, flips from a correct number to null. The acceptance asks for reasoning tokens beside output and a stated billing basis, not for nulling a cost the response itself determines; it defeats the epic's "what a call cost is reportable" (epic:58) and the rewriting-suite story's "README states the batch's total judge spend" | Price from what the response proves: when `thoughtsTokenCount` is absent but `totalTokenCount` is present, derive the hidden count as `total - prompt - candidates` (record it, with a source/reason distinguishing "derived from totals" so it is never an assumed zero), or keep `reasoning_tokens` null but bill `totalTokenCount - promptTokenCount` as output; null the cost only when the totals are also missing. Add a test with the pinned model's real usage shape (no thoughts, total = prompt + candidates) asserting a non-null Google cost |
| 🟡 | code | 2 | `row_contract.py:542` | `judge_cost.per_provider` entries' new keys (`reasoning_tokens`, `reasoning_tokens_null_reason`, `reasoning_tokens_billing`) are not checked at write; AC5 "states whether that provider bills them" is guaranteed only by the producer | Validate each `per_provider` entry's key set (or at least `reasoning_tokens_billing` in the two declared values) and test a missing one is refused by name |
| 🟡 | code | 1 | `row_contract.py:592-606` | `reasoning_tokens` type unchecked at write: `"12"`, `-1` or `True` validates | Require `int` (not `bool`) `>= 0` or `None`, as `google_client.py:242-248` already does at read |
| 🟢 | fit | 2 | `cost.py:100-103` | Mistral `inside_output` is inferred from the usage shape, not confirmed against a live reasoning-capable call or Mistral's billing docs | Cite the doc line or flag it as an assumption in the comment |
| 🟢 | fit | 3 | `evidence/stubbed-judged-row-read-back.json` | Evidence shows Google with `reasoning_tokens: 86` on `gemini-3.5-flash-lite`, a shape the pinned model never returns; the real-call path (null count) is not what the evidence shows | Regenerate evidence with the pinned model's real usage shape once row 1 is fixed |
| 🟢 | rot | 1 | `test_judge.py:206-207` | `_fixed_score_backend` gives the Google stub `provider_reports_no_reasoning_count`, which the real Google backend never records | Use `REASONING_TOKENS_ABSENT_FROM_RESPONSE` for Google stubs |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 92% (11/12) |
| Files checked | cost.py, google_client.py, judge.py, judge_backends.py, judge_protocol.py, row_contract.py, test_cost.py, test_google_client.py, test_judge.py, test_judge_probe.py, test_judge_protocol.py, test_row_contract.py, evidence/* |
| Unchecked     | Phase 2 "null beside-output count nulls the cost" — fix |
| Unplanned     | none (`judge_protocol.py` change is a comment only) |

## Round 2

- **Verdict**: approve (VERDICT: PASS)
- **Diff**: `116a3ad...working tree` (12 modified files, untracked task folder)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_01
- **Findings**: 0 critical, 0 warning, 3 minor
- **Gates**: `uv run pytest -q` => `1074 passed, 2 warnings in 32.51s`, coverage 95.88%; `ruff check` => `All checks passed!`; `ruff format --check` => `481 files already formatted`; `mypy src/ scripts/` => `Success: no issues found in 45 source files`

### Round 1 findings

- [x] 🔴 Google cost nulled on the pinned model: fixed. `google_client.py:268-300` derives `total - prompt - candidates` when `thoughtsTokenCount` is absent, refuses a negative (`:294`); tagged `derived_from_totals` via `judge_backends.py:171-188`; `test_judge.py:584` (pinned shape => non-null Google and aggregate `cost_total`), `test_google_client.py` `test_the_pinned_models_usage_shape_yields_a_derived_reasoning_count`, `test_totals_that_contradict_themselves_are_refused`, `test_with_no_thoughts_count_and_a_total_missing_the_count_is_none`
- [x] 🟡 `per_provider` keys unchecked: fixed. `row_contract.py:652` checks `JUDGE_COST_PROVIDER_FIELDS` and the billing basis; tests `test_a_per_provider_cost_entry_missing_a_reasoning_field_is_refused_by_name`, `..._unknown_billing_basis_is_refused`, `test_a_malformed_per_provider_cost_record_is_refused`
- [x] 🟡 `reasoning_tokens` type unchecked: fixed. `row_contract.py:614-616`; `test_a_reasoning_count_that_is_not_a_non_negative_integer_is_refused` over `"12"`, `-1`, `True`, `1.5`
- [x] 🟢 Mistral billing basis: flagged `ASSUMED` with the revisit condition, `cost.py:91`
- [x] 🟢 Evidence: regenerated on the pinned shape (`reasoning_tokens: 0`, `derived_from_totals`, non-null Google `cost_total`), `evidence/stubbed-judged-row-read-back.json`
- [x] 🟢 Google stub null reason: Google stubs now carry the derived 0, `test_judge.py` `_fixed_score_backend`

### Phases

#### Phase 1: six record fields, two backends, writer gate (schema "13")

- [x] AC1 answering provider, response-named else direct endpoint: `judge_backends.py:89,157`; `test_judge.py:485,537`; `response` source validated in `test_row_contract.py` `test_a_record_answered_as_bound_read_from_the_response_validates`
- [x] AC2 no fallback, mismatch refused at write naming both: `row_contract.py:590`; `test_judge.py:624`, `test_row_contract.py` `test_a_record_answered_by_another_provider_is_refused_naming_both`; no re-issue stays order 5's contract (backends catch nothing)
- [x] AC3 effort as sent, `not_sent` when none: whole-request-body assertions `test_judge.py:485,537`
- [x] AC4 reasoning tokens apart from output, null with reason never zero: Mistral null + `provider_reports_no_reasoning_count`; Google reported / derived / null + `reasoning_count_absent_from_response`; writer pairing checks `row_contract.py:612-650`
- [x] AC6 additive under bump, missing field refused by name, deterministic row unchanged: `row_contract.py:92`; `test_a_judge_record_missing_a_schema_13_field_is_refused_by_name` (parametrized over all six), `test_row_contract.py:530`

#### Phase 2: reasoning tokens and billing basis in `judge_cost`

- [x] AC5 per-provider reasoning beside output with billing basis: `cost.py:219-260`; `test_cost.py` `test_reasoning_billed_inside_the_output_count_is_not_added_twice`, `test_reasoning_billed_beside_the_output_count_is_priced_once` (asserts not twice, not zero, `tokens_out_total` unfolded)
- [x] Null beside-output count => unknown cost, reached only with totals missing: `test_cost.py` `test_a_null_reasoning_count_billed_beside_output_makes_the_cost_unknown`, `test_judge.py:584`
- [x] Undeclared billing basis refused by name: `test_a_provider_with_no_declared_billing_basis_is_refused_by_name`, `test_every_priced_provider_declares_a_reasoning_billing_basis`

#### Phase 3: stable prefix, resume read-back, evidence

- [x] AC7 byte-identical prefix after the rubric, misordered shell fails a test: `test_judge_protocol.py:202,214,251`
- [x] AC8 resume reads new fields back unchanged, re-issues nothing: `test_judge_probe.py:778`
- [x] Evidence: `evidence/stubbed-judged-row-read-back.json`

### Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 | fit | 1 | `google_client.py:284-290` | The sixth field `reasoning_tokens_source` is justified, not creep: without it a derived 0 reads as a reported "judge did not reason", which AC4 forbids. Residual tension: the pinned model arguably "does not report reasoning tokens", and AC4's literal text asks null there; the derived 0 is a defensible reading backed by the response's own totals | Owner to confirm the reading; if accepted, add one clause to the story's AC4 so the derived-from-totals case is in the contract |
| 🟢 | fit | 1 | `google_client.py:284-290` | An empty generation (`candidatesTokenCount` absent) yields a null count, so that item's Google judge cost and the row aggregate go null, although `total - prompt` would be exact | Optional: derive with candidates=0 when the key is absent and `finishReason` is OK, or leave as the conservative choice and note it |
| 🟢 | fit | 2 | `cost.py:256-260` | `per_provider` carries `reasoning_tokens_null_reason` but not the aggregated `reasoning_tokens_source`, so a derived count is indistinguishable from a reported one at the cost-block level | Optional: carry the joined sources like the null reasons; not required by AC5 |

### Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (12/12) |
| Files checked | cost.py, google_client.py, judge.py, judge_backends.py, judge_protocol.py, row_contract.py, test_cost.py, test_google_client.py, test_judge.py, test_judge_probe.py, test_judge_protocol.py, test_row_contract.py, evidence/* |
| Unchecked     | none |
| Unplanned     | `google_client.py` derivation (planned in round-1 fix decision; plan.md updated) |
