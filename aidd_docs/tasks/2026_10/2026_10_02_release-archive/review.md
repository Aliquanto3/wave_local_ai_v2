# Review: Each release attaches one archive that needs no clone

## Round 1

VERDICT: PASS

Evidence run by the reviewer (worktree `wave_local_ai_v2-night`, HEAD `28bb23d` plus the uncommitted diff):

- `uv run pytest -q`: `2865 passed, 9 skipped, 2 warnings in 201.12s`, coverage 98.49%. The new and related files alone: `118 passed, 1 skipped` (the skip is the off-tag `PLACEHOLDER-` release gate, `tests/test_citation.py:245`).
- `ruff check`, `ruff format --check` and `mypy src/ scripts/` are clean.
- Two CLI builds into a temp dir gave the same sha256, `82f93c64...f6802`. The zip has 39 entries under one top folder, all dated 1980-01-01 with mode 0644, and no absolute or `..` names.
- `verify --tag v0.3.0` exits 1 because the tag disagrees with the package and with `CITATION.cff`. A zip whose `roster.csv` was edited exits 1 with `table roster.csv differs from what the bundle at 28bb23d... derives`.

### Acceptance

| # | Condition | Status | Proof |
| - | --------- | ------ | ----- |
| 1 | On `v*`, after test/build/verify-tag, CI builds the export and one archive any desktop OS opens | Proven in code; the tag push is pending on the owner | `ci.yml` `release` job; `test_the_release_job_runs_on_a_tag_after_test_build_and_verify_tag`, `test_the_archive_is_one_zip_named_after_the_release` |
| 2 | Tables, dictionary, five bundle parts, both licences, stamped citation, README with release/commit/schema/files/citation | Proven | `test_the_archive_holds_every_listed_file`, `test_the_readme_names_release_commit_schema_files_and_citation`, `test_the_shipped_citation_is_the_repository_one_stamped_with_the_commit` |
| 3 | Self-describing, and a check fails the build when it is not | Met with a reviewed exception list; the owner should confirm it | `test_no_file_names_a_path_only_a_clone_holds`, `test_a_clone_only_path_fails`, `test_an_exception_holds_only_in_the_files_it_names`. See finding N3 |
| 4 | The Release is created with the archive attached; `contents: write` is on that job only, and the other permissions are unchanged | Proven in code; the Release URL is pending on the owner | `test_only_the_release_job_may_write_contents`, `test_publish_and_verify_tag_are_unchanged_by_the_release_job`. The diff touches no existing job |
| 5 | The derivation is proven, so a hand-edited table fails | Proven | `test_a_hand_edited_table_fails_the_derivation`, `test_an_edited_bundle_copy_fails`, and the reviewer's CLI run |
| 6 | Tag, package, citation and README agree, the commit equals the tag's, and otherwise there is no Release | Proven | `test_a_tag_that_is_not_the_packaged_version_is_refused`, `test_a_tag_disagreeing_with_the_citation_is_refused`, `test_a_commit_that_is_not_the_checkout_is_refused`, `test_a_readme_or_citation_naming_another_release_fails`, `test_the_release_is_created_only_after_the_archive_verifies` |
| 7 | The repository README says where the archive is | Met | `README.md` section "Download the results (no clone)". No test; checked by reading |
| Evidence | Release URL, plus opening the tables with no clone and no Python | Pending on the owner | Story "Evidence it publishes" |

Supply chain:
- `$GITHUB_REF_NAME` and `$GITHUB_SHA` reach the shell only as environment variables. No `${{ }}` is placed inline in a `run:`.
- `GH_TOKEN` is set on the `gh` step only.
- The actions are pinned by SHA, the same pins the existing jobs use.

The `CITATION.cff` placeholder gate still blocks a tag build. `tests/test_citation.py` fails on `refs/tags/` while placeholders remain, `test` runs it, and `release` needs `test`.

The story says four tables and the archive has five. This is stale wording, not a conflict: the epic was amended to five (epic lines 40 and 69, the 2026-10-01 Q2 (a) amendment).

The `bundle_export.py` rewording is scope-justified. The self-describing check would otherwise fail on the column dictionary. No committed bundle file or committed export changed: `git status` shows nothing under `aidd_docs/results/` or `aidd_docs/roster/`.

### Blocking findings

None.

### Non-blocking findings

1. `.github/workflows/ci.yml` `release` job: `actions/checkout` keeps its default `persist-credentials: true`. That leaves the `contents: write` token in `.git/config` while `uv sync` and `uv run` execute dependency code. Add `persist-credentials: false`, since `gh` reads `GH_TOKEN`. Also consider dropping `enable-cache` in this one write-scoped job.
2. `scripts/assemble_release_archive.py:581`: `verify` skips the byte comparison for `README.md` and `CITATION.cff`, contrary to its docstring at :569. A supplied zip with an altered README body still verifies as long as its identity lines are intact. Compare both files to the expected bytes as well. The `build` path is unaffected.
3. `PATHS_NOT_SHIPPED` (`assemble_release_archive.py:122-174`) is honest and narrowly scoped (each path is allowed only in the files that name it), and the archive README links each path at the commit. Taken literally, though, `LICENSE-DATA`, `models.json` and the shipped table `roster.csv` still name repository paths. They need a browser, not a clone. Two of them, the untracked `runtime.jsonl` and `quality.jsonl`, exist in no commit at all. The owner should accept this reading of "needs no clone", or open follow-ups to reword the roster `read_from` notes and the `LICENSE-DATA` scope list.
4. `assemble_release_archive.py:370-375`: `manifest_versions` splits CSV lines on commas, so a quoted cell would break it. Use the `csv` module.
5. `release` runs beside `publish`, so a failed archive check still lets the image be pushed. Re-running the job after a Release already exists fails at `gh release create`. Neither breaks the acceptance, which only requires that no Release is created.
