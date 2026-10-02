# Review: Every row records whether its prompt left the machine

## Round 1

VERDICT: PASS

### Gates

- `uv run pytest -q`: `1571 passed, 2 warnings in 49.12s`, coverage 97.59% (floor 95%).
- `uv run ruff check .`: all checks passed. `uv run ruff format --check .`: 568 files already formatted. `uv run mypy src/ scripts/`: no issues in 54 source files.
- `uv run wave-local-ai-v2-validate aidd_docs/results/runtime-reference.jsonl aidd_docs/results/quality-reference.jsonl`: `checked 82 row(s)`, exit 0. With no arguments it needs `LLAMA_SERVER_PATH` (environment, not this change). The command checks fiche integrity only; `row_contract.validate_row` runs on write (`results.append_row`) only, so committed rows (schema "7", "2", "13") are never put through the new required set. No committed `.jsonl` is modified (`git status`).

### Acceptance

1. Field on every row, never null: required on both kinds (`row_contract.py:182`, `:290`); runtime writer stamps `none` (`__init__.py:423`), quality writer stamps `subject_egress_for(provider)` (`quality_cli.py:968`). Proved by `test_cli.py::test_the_runtime_row_records_that_its_prompt_never_left_the_machine` and `test_quality_cli.py::test_every_row_records_where_its_subject_prompt_went` (local => `none`, mistral => `mistral`, google => `google`, HTTP stubbed). Met.
2. Gate refuses absent or null, naming the field, appends nothing: `_validate_subject_egress` (`row_contract.py:563`); `test_a_row_missing_its_subject_egress_is_refused_by_name`, `test_a_row_with_a_null_subject_egress_is_refused_by_name`, `test_the_writer_gate_appends_nothing_for_a_row_without_subject_egress` (both kinds). Met.
3. Contradiction with `provider` refused: `test_a_local_quality_row_recording_a_provider_is_refused`, `test_a_cloud_quality_row_recording_none_is_refused`, plus the stricter `..._recording_another_provider_is_refused`. Met.
4. Runtime row records `none`: writer + test in (1). Met (enforced by writer, not by the gate; see N2).
5. Judge egress kept apart: `JUDGE_EGRESS_FIELDS` untouched; `test_a_judged_row_keeps_its_judge_egress_beside_the_subject_egress`, `test_judge_probe.py::test_each_probe_row_records_its_subject_egress_apart_from_the_judges`. Met.
6. Additive bump with reason, old rows not rewritten: `SCHEMA_VERSION = "16"` with comment block (`row_contract.py:112-120`); no store edited; README and CHANGELOG state the reference rows carry it from their next regeneration. Met.

### Points judged

- comparison.py: the plan's rationale is wrong in wording. A difference outside the compared dimension does not refuse: `_comparison_kind` (`comparison.py:667-687`) makes it a confound and the member an observation (verdict `not comparable`, p kept in `result`). The decision itself is right: without it every local-vs-cloud `model` comparison would be downgraded from a test to an observation over a field that the gate holds equal to `subject_egress_for(provider)`, i.e. no information beyond `provider`. Nothing is hidden: `differing_fields` still lists `subject_egress` on the member (asserted in `test_a_local_and_a_cloud_subject_differ_on_egress_without_a_confound`).
- judge_probe.py:748: necessary. The probe writes quality rows through the same gate (`judge_probe.py:917`, `:1029`, `append_row(..., "quality", row)`); without the field every probe row is refused. A gap in the story's "Code it changes", correctly recorded in the plan.

### Blocking findings

None.

### Non-blocking findings

- N1. `plan.md` Decisions row on comparison says the comparison "would otherwise be refused"; it would be an observation. Fix the wording.
- N2. The gate accepts any non-empty string on a runtime row (e.g. `"mistral"`); `none` is held by the writer and its test only. Within the acceptance's wording; a one-line `kind == "runtime"` equality check would make the gate enforce it.
- N3. Mixed-schema `prompt_variant` comparisons (a pre-"16" row vs a "16" row) now show `subject_egress` (absent vs `none`) as a confound, so the member becomes an observation. Honest, but worth knowing when comparing against the current reference rows.
- N4. `plan.md` says the read model reports the field as `predates_schema` on older rows; it is in both not-rendered sets, so the read model never reports it.

## Round 2

VERDICT: PASS

Scope: the post-review fixes.

- `uv run pytest -q`: `1573 passed, 2 warnings in 48.73s`. ruff check, ruff format --check (569 files) and mypy (54 files) are clean.
- N2 resolved: `_validate_subject_egress` refuses a runtime row whose `subject_egress` is not `none` (`row_contract.py`, `kind == "runtime"` branch). Proved by `test_row_contract.py::test_a_runtime_row_recording_a_provider_is_refused` (mistral and google). Acceptance 4 is now enforced by both the gate and the writer.
- N1 and N4 resolved: plan.md Decisions now says a confound makes an observation (`not_comparable`), not a refusal, and says the read model renders the field in no view.
- CHANGELOG and README describe the runtime refusal. The acceptance results from Round 1 are unchanged.
- Blocking findings: none. N3 (a mixed-schema `prompt_variant` comparison becomes an observation) stands as a non-blocking note.
