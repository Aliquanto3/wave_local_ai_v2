# Review: Parquet copies ship beside the CSV and never disagree with it

- **Verdict**: approve (VERDICT: PASS)
- **Diff**: `HEAD (c68b23e)...working tree (uncommitted)`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 3 minor

## Phases

### Phase 1 — The pinned `release` group, the Parquet script and the archive's `--parquet`

- [x] `pyarrow==25.0.1` in a non-default `release` group, out of `project.dependencies`; `uv.lock` adds only pyarrow (no transitive deps) and the group entries — `pyproject.toml:75-79`, `uv.lock:1315,2023,2055`; `uv export --locked --no-dev` names no pyarrow (0 matches)
- [x] Image excludes it: Dockerfile `uv sync --locked --no-dev --no-editable` installs no non-default group, and no `default-groups` override exists — `Dockerfile:32`, `test_pyarrow_is_installed_only_inside_the_release_job`, `test_pyarrow_is_pinned_in_the_release_group_and_nowhere_else`
- [x] Audit covers every group: `--all-groups` export is a strict superset of the old one (92 => 93 packages, only `+pyarrow==25.0.1`); `uv run python scripts/audit_dependencies.py` => "no blocking findings", exit 0 — `scripts/audit_dependencies.py:46`
- [x] Types from the dictionary `unit` through an explicit table; unknown unit or missing entry fails — `scripts/release_parquet.py:43-92,130-148`, `test_a_column_without_an_entry_or_with_an_untyped_unit_is_refused`, `test_every_unit_the_dictionary_states_has_a_parquet_type` (runs in the matrix)
- [x] Cell-by-cell check under the types, empty cells included, independent read-back (columns, Arrow type, row count, each cell) — `scripts/release_parquet.py:224-265`; `test_one_altered_cell_fails_the_check`, `test_a_value_where_the_csv_is_empty_fails_the_check`, `test_a_wrong_type_a_missing_row_or_other_columns_fail`; reviewer probe: a one-ULP / one-day / one-microsecond / flipped / +1 change in a float, date, timestamp, boolean, integer cell of every table is detected
- [x] Archive README says the CSV is right and names the pyarrow version — `scripts/assemble_release_archive.py:491-504`; built archive README: "wherever the two could disagree, the CSV is right. The copies were written with pyarrow 25.0.1."
- [x] Archive deterministic: two reviewer builds sha256 `d824276f...` identical, matching the implementer's evidence; non-`--parquet` archive unchanged (`test_two_builds_of_one_commit_are_byte_identical`)

### Phase 2 — The `release` job: on-demand trigger, Parquet step, workflow tests

- [x] `workflow_dispatch` trigger; release `if` = test success and not cancelled, and (tag push with build + verify-tag success, or dispatch) — `.github/workflows/ci.yml:11,232-236`; `test_the_release_job_runs_on_a_tag_after_test_build_and_verify_tag`, `test_the_release_build_runs_on_demand_without_a_tag`
- [x] Tag path keeps every gate: `!cancelled()` disables the implicit `success()`, so build and verify-tag are required explicitly on push; a failed or skipped one skips the job
- [x] No Release and no image on dispatch: "Create the Release" `if: github.event_name == 'push'`; `publish` push-only, tag-push behaviour unchanged (push event + `v*` ref + implicit success of its needs) — `ci.yml:193,285`; `test_the_on_demand_run_creates_no_release_and_pushes_no_image`
- [x] pyarrow installed only in the release job; Parquet tests run there — `ci.yml:254,271`; `test_pyarrow_is_installed_only_inside_the_release_job`
- [x] Coverage-gate test edit is legitimate: the matrix still has exactly one `uv run pytest`, the addopts branch/fail-under assertions are untouched, the release job's run is pinned to the exact Parquet-only string; coverage source is `src/` only — `tests/test_ci_workflow.py:88-107`
- [ ] One on-demand GitHub run performed and its log kept — owner-pending (no dispatch in the night run); local rehearsal of the same commands in `evidence/on-demand-rehearsal.txt`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | code (security) | 2 | `.github/workflows/ci.yml:238-239` | Dispatch path runs dependency code (uv sync, pyarrow, pytest) beside a `contents: write` token it never uses. Not an escalation: dispatch needs repo write access, and a writer can already push a workflow requesting write; the token is not on disk (`persist-credentials: false`) and `GH_TOKEN` is only in the skipped step. Still wider routine exposure than tag-only. | Follow-up: split into `release-build` (`contents: read`, both paths, uploads the zip) and `release-publish` (`contents: write`, push-only, downloads the zip, runs only `gh release create`); permissions cannot be expression-conditional |
| 🟢 minor | code | 1 | `scripts/release_parquet.py:167-171` | A non-UTC offset in a timestamp cell would be stored as the UTC instant; the check passes (same instant) while the offset text is lost. All current values are `+00:00`. | Mention UTC normalisation in the archive README's Parquet section, or refuse non-`+00:00` offsets |
| 🟢 minor | code | 2 | `.github/workflows/ci.yml:232-236` | A dispatch on a `v*` tag ref runs build and verify-tag but the release job does not wait on their success. Harmless (no Release, no image). | None required; optionally require `needs.verify-tag.result != 'failure'` on dispatch |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 92% (12/13) |
| Files checked | .github/workflows/ci.yml, pyproject.toml, uv.lock, Dockerfile, scripts/release_parquet.py, scripts/assemble_release_archive.py, scripts/audit_dependencies.py, tests/test_release_parquet.py, tests/test_ci_workflow.py, tests/test_assemble_release_archive.py, README.md, aidd_docs/memory/cli.md, aidd_docs/memory/coding-assertions.md |
| Unchecked     | One on-demand GitHub run and its kept log — not-applicable (owner-pending, no workflow dispatch in the night run) |
| Unplanned     | none (five tables, not the story's "four": documented plan decision, the fifth table postdates the story) |

Commands run by the reviewer: `uv run pytest -q` => `2888 passed, 20 skipped, 2 warnings in 210.91s`, total coverage 98.49%; Parquet tests in a scratch venv with the `release` group => `27 passed`; `ruff check .`, `ruff format --check .`, `mypy src/ scripts/` => clean; dependency audit => exit 0. The worktree `.venv` was not changed (release group synced into a scratch `UV_PROJECT_ENVIRONMENT`).

## Round 2

- **Verdict**: approve (VERDICT: PASS)
- **Diff**: `HEAD (c68b23e)...working tree (uncommitted)`, round-1 findings 1 and 2 applied
- **Axes run**: code, functional, relevancy (CI split and timestamp refusal)
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 2 minor

### Phases

- [x] `release-build`: `contents: read`, `persist-credentials: false`, no uv cache, same `if` as round 1 (tag push requires test + build + verify-tag success; dispatch requires test), digest step `id: archive` => job output, upload `release-archive` with the pinned `upload-artifact` SHA, `if-no-files-found: error` — `.github/workflows/ci.yml:224-305`
- [x] `release-publish`: `contents: write` + `actions: read`, `needs: [test, build, verify-tag, release-build]`, `if` push + `v*` with no status function => implicit `success()`: any skipped, failed or cancelled need skips it; a dispatch never reaches it — `ci.yml:307-337`; `test_the_on_demand_run_never_reaches_a_release_or_an_image_push`
- [x] Download targets this run only: `gh run download "$GITHUB_RUN_ID" --repo "$GITHUB_REPOSITORY" --name release-archive` (default env vars, nothing inline) — `ci.yml:322`
- [x] Digest: passed through `env: ARCHIVE_SHA256`, never inlined; `sha256sum -c -` fails on a mismatch, a missing file or an empty digest (bash `-eo pipefail`). Build-job dependency code could set the output, but it already controls the archive it builds, so the digest adds no trust there; what it does block is a same-run artifact swap between the jobs — `ci.yml:318-323`
- [x] Write-token job runs no project or dependency code: no checkout, no `uses:`, only the preinstalled `gh` — `test_the_write_token_job_runs_no_project_code`
- [x] No new `${{ }}` in any `run:`; the only ones in `run:` are the pre-existing `needs.*.result` lines in `required` (`ci.yml:345-354`)
- [x] `publish` on a tag push unchanged (`if` push + `v*`, same needs and permissions) — `test_publish_and_verify_tag_are_unchanged_by_the_release_jobs`
- [x] Timestamps refuse any offset but `+00:00`, naive included — `scripts/release_parquet.py:170-173`; `test_a_cell_that_is_not_its_kind_is_refused[timestamp-...+02:00]`; archive still byte-identical (sha256 `d824276f...`)
- [x] Coverage-gate test still admits only the Parquet-only run, now in `release-build` — `tests/test_ci_workflow.py:87-112`
- [ ] One on-demand GitHub run and its kept log — owner-pending (unchanged)

### Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | code | 2 | `tests/test_ci_workflow.py:273-312` | The tests assert `--name release-archive` and `sha256sum -c -` but not that the download names `"$GITHUB_RUN_ID"` and `--repo`, nor that no `run:` in the release jobs holds `${{` | Add both assertions |
| 🟢 minor | fit | 2 | `.github/workflows/ci.yml:307-337` | `release-publish` (in-run `gh run download` of a v4 artifact, `gh` with no checkout) is exercised only by a real tag push; the on-demand run proves `release-build` alone | Owner: check the `release-publish` log on the first tag; the job is re-runnable on its own if it fails |

### Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 90% (9/10) |
| Files checked | .github/workflows/ci.yml, tests/test_ci_workflow.py, scripts/release_parquet.py, tests/test_release_parquet.py, aidd_docs/memory/cli.md, aidd_docs/memory/coding-assertions.md, pyproject.toml |
| Unchecked     | One on-demand GitHub run and its kept log — not-applicable (owner-pending) |
| Unplanned     | none |

Commands: `uv run pytest -q` => `2890 passed, 20 skipped, 2 warnings in 205.70s`, coverage 98.49%; Parquet tests (scratch venv, `release` group) => `28 passed`; `ruff check .`, `ruff format --check .`, `mypy src/ scripts/` => clean; no actionlint available locally.
