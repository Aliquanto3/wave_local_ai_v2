# Review: the laptop proves both modes and republishes the bundle once

## Round 1 (2026-10-04, independent reviewer)

VERDICT: CHANGES-REQUIRED

### Gates re-run by the reviewer

- `timeout 900 uv run pytest -q`: `3047 passed, 20 skipped, 2 warnings in 212.78s`, coverage 98.53%.
- `uv run ruff check .` clean; `ruff format --check .` clean; `mypy src/ scripts/` no issues.
- `uv run wave-local-ai-v2-merge-bundle --check`: `committed bundle equals the merge (6 runtime, 80 quality, 0 refusals)`, exit 0.
- `uv run wave-local-ai-v2-validate` on `runtime-reference.jsonl` and `quality-reference.jsonl`: `checked 86 row(s)`, exit 0 (each file alone: 6 and 80, exit 0).
- `git diff --cached -M --summary`: all 7 superseded files are `rename ... (100%)`, none modified in the working tree.
- Secrets: the diff plus every untracked file hold 0 mixed-case 24+ char tokens, 0 near the provider name, a key variable name or an authorization header; the only value assigned to the Mistral key variable is the `.env.example` placeholder; no `.env` in the worktree. `detect_secrets.pre_commit_hook` (baseline copied to scratch) over all changed and new files: exit 0. The 3 fiches match the hook's `fiches.[0-9a-f]{64}[.]json$` exclusion.
- `uv run --isolated --locked --group release pytest tests/test_release_parquet.py --no-cov`: `1 failed, 17 passed, 10 errors` (see blocking 1). The same Parquet build over the schema-7 export succeeds; over the current export it fails.

### Blocking

1. `scripts/release_parquet.py:165` (`parse_cell`, FLOAT): the release Parquet build refuses the republished bundle: `runtime_aggregates.csv vram_used_mib: 'not_applicable' is not a float`. The first `cpu_only` rows in the bundle break the `release-build` job (tag push and `workflow_dispatch`; the PR matrix skips these tests because pyarrow is absent, so PR CI stays green and hides it). Fix: type the `cpu_only` sentinel (`row_contract.VRAM_NOT_APPLICABLE`) on every column that can carry it (an explicit null-with-meaning, or a string column), in the export or the Parquet step, and add a `test_release_parquet.py` case over a `not_applicable` cell; prove with `uv run --group release pytest tests/test_release_parquet.py --no-cov` green against the current bundle.

### Non-blocking

1. `aidd_docs/results/README.md:608-609`: the leader-set table still names `leader-sets/...` and `comparisons/...` for records now in the `.schema-7/` directories (the superseded note above it covers intent; update the two paths).
2. `tests/test_reference_bundle.py` `test_a_field_the_schema_7_bundle_predated_is_now_the_rows_value` pairs view `entries[0]` with `read_rows(...)[0]` by position; and `retries`/`resumed` absence over real schema-7 rows is no longer asserted anywhere (only `thinking_policy`, `tests/test_read_model.py:1073`). Parametrize that read-model test over the three fields.
3. Every `gpu` repetition carries `gpu_throttle_reasons` `sw_power_cap` + `sw_thermal_slowdown` (already set at idle: `machine-state.txt` `0x24`), where the schema-7 rows read `gpu_idle`. The README's quiet-window paragraph and its flagship 21.2 vs 25.4 tok/s observation should name it.
4. Acceptance names "the laptop's own pull request"; D6 authorizes one night-run PR. State in the PR body that this story lands inside it. `docs/setup.md` 6.1 already says the laptop "republished it through this loop" before that PR exists.
5. The validator's `edited` proof ran with the fiche uncommitted, so `changed_fields` reads "unavailable" (stated honestly in the README). A re-run after commit would show the field-naming half.

### Acceptance

| Line | Status | Evidence |
| --- | --- | --- |
| Fresh clone, `docs/setup.md` alone, declared machine id and per-mode profiles | proven | `evidence/setup-walk.md`; rows `commit_sha` `32da6f9`, `tree_dirty: false`, `profile_id` per mode, `profile_overrides: {}` |
| Bundle regenerated under the final schema on Story 19's protocol; superseded files `git mv`-renamed, unedited | proven (quiet window asserted under D8, owner acceptance pending) | rows `"30"` = `row_contract.SCHEMA_VERSION`; flagship `12d19a0c` `reproduced` vs `78e5d7ef`; quality `68ac4f21` `reproduced` vs `acb6e894` (local, mistral); validator exit 0; renames R100; `.schema-7/` moves justified by `bundle_export.py:1813` (export refuses a record citing a run the bundle does not hold) |
| Qwen3-0.6B both modes, two runs each, own-first verdicts, `cpu_only` VRAM not applicable, no cross-mode throughput verdict | proven | `test_a_runtime_verdict_never_crosses_a_model_or_a_compute_mode`, `test_a_cpu_only_row_reads_vram_as_not_applicable_everywhere`; three distinct fiches; ratio stated as an observation (values re-derived: 0.254x gen, 0.052x prompt, 19.2x TTFT) |
| German routing item resolved or re-deferred by name | proven | `tech-debt.md` 2026-08-27 row; README section; labels re-checked in the rows (`account-de-01` misrouted in run 1 only, `other-de-01` in both) |
| Promoted, merged by order 5's step, lands on `main` via PR with CI green; `PUBLISHED_BUNDLE_SCHEMA_VERSION` final | promoted, merged, constant `"30"`: proven; PR and CI: pending (orchestrator); release-build red until blocking 1 is fixed | `merge-bundle --check` exit 0; machine location byte-equal to the bundle; `PRE_MERGE_SNAPSHOT` and its 4 tests gone, no reference left outside CHANGELOG |
| Setup gaps added to `docs/setup.md` and listed | proven | G1 (placeholder keys) and G2 (second run against its own first) in `docs/setup.md` and the README |

Scope beyond the story's file list (`bundle_export.py` `retry_budget` JSON cell and suite `level`/`divergence_tolerance` docs, `assemble_release_archive.py` not-shipped paths, `LICENSE-DATA` scope): justified by the republished bundle and tested (`test_the_current_bundle_exports`, `test_the_committed_bundle_recomputes_to_every_published_value`, the 29 archive tests including `test_two_builds_of_one_commit_are_byte_identical` and `test_the_top_level_split_covers_every_tracked_entry`). The `test_release_parquet.py` unit-set relaxation (`- {""}`) is justified: the 3 empty-unit rows are "not in the bundle read" record kinds, and table columns stay covered by `test_every_table_column_is_typed`.

## Round 2 (2026-10-04, independent reviewer)

VERDICT: PASS

Round 1's secrets line is reworded so it no longer quotes the key-variable assignment or the keyword list. Before the change, the hook flagged it as a `Secret Keyword` at line 14; after it, the hook exits 0 on this file.

### Gates re-run by the reviewer

- `timeout 900 uv run pytest -q`: `3051 passed, 20 skipped, 2 warnings in 217.50s`, coverage 98.53%.
- `uv run --isolated --locked --group release pytest tests/test_release_parquet.py --no-cov`: `29 passed` (round 1: 1 failed, 10 errors). `test_the_command_prints_every_table_compared` builds the archive with its Parquet copies and verifies it.
- ruff check, ruff format --check and mypy are clean. `merge-bundle --check` exit 0 (6 runtime, 80 quality, 0 refusals). Validator `checked 86 row(s)`, exit 0. The 7 renames are still `(100%)`.
- `detect_secrets.pre_commit_hook` (baseline copied to scratch) over every changed and new file, this one included: exit 0 after the rewording.

### Blocking 1 (resolved)

`runtime_aggregates.vram_used_mib` is now a STRING column in the Parquet copy (`scripts/release_parquet.py` `UNIT_KINDS[bundle_export.VRAM_UNIT]`). Its unit is "MiB (2^20 bytes), or the identifier not_applicable", and the CSV is unchanged. The choice is sound: it is lossless, and it keeps the three states apart (a number, `not_applicable`, and an empty cell meaning a failed read). A float column with null would have folded `not_applicable` into a failed read. The tradeoff is that a Parquet reader must cast the `gpu` rows' numbers itself. The column dictionary says so ("Read it as a number only where it is not that identifier"), and CHANGELOG `### Fixed` names the change.

Nothing still claims a numeric type for that column:
- The old unit "MiB (2^20 bytes)" was used by this column alone, so removing its FLOAT mapping orphans no other column. `"MiB"` (sandbox memory cap) is a separate unit.
- No script reads `vram_used_mib`.
- `docs/zenodo-deposit.md` and `cli.md:224` only say "typed copies, types from the unit".
- `README.md:1348` describes the CSV/README table unit, not the Parquet type.

The new test `test_a_cpu_only_vram_cell_keeps_its_identifier_apart_from_a_failed_read` runs in the default environment, not the pyarrow-only path, so PR CI now guards it.

### Round 1 non-blocking items

1. README:608-609 now name the `.schema-7/` paths: fixed.
2. The pairing test now matches on `(run_id, provider, item_id)` (`tests/test_reference_bundle.py:349-361`). `tests/test_read_model.py:1076` parametrizes the schema-7 absence over `thinking_policy`, `retries` and `resumed`: fixed.
3. README:827-831 and :865-866 name `0x24` at idle and `sw_power_cap`/`sw_thermal_slowdown` on every `gpu` repetition. The note "some repetitions of both `cpu_only` runs" checks out: the warmups carry those reasons, the counted repetitions read `gpu_idle`. Fixed.
4. `docs/setup.md:793-797` now says the republication lands inside the night-run's draft PR rather than a laptop branch: fixed. The owner still has to accept that deviation from "the laptop's own pull request".
5. The validator's field-naming half still waits for the commit. It is stated as such and is not blocking.

### Acceptance

Unchanged from round 1, except that the release-build path no longer blocks:
- Lines 1, 3, 4 and 6: proven.
- Line 2: proven. The quiet window is asserted under D8; owner acceptance is pending.
- Line 5: promote, merge and `PUBLISHED_BUNDLE_SCHEMA_VERSION` `"30"` are proven. The PR landing on `main` with CI green is pending (the orchestrator opens the draft PR).
