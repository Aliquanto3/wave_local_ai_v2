# Review: Each client showing is logged as a record someone who was not there can read back

## Round 1

VERDICT: PASS

Gate evidence: `uv run pytest -q` => `2970 passed, 20 skipped, 2 warnings in 207.16s`, coverage 98.52% (floor 95%). `ruff check`, `ruff format --check`, `mypy src/ scripts/` clean. detect-secrets hook over the new files exits 0, `.secrets.baseline` untouched. Targeted run of `test_client_sessions.py`, `test_data_licence.py`, `test_assemble_release_archive.py` => `118 passed`, no skip (the repository-history walk ran on a non-shallow history).

### Acceptance, line by line

| # | Acceptance line | Status | Evidence |
| - | --------------- | ------ | -------- |
| 1 | One append-only JSONL file, tracked by its own negation, `--no-index` test | proven | `.gitignore:36-38`; `test_the_record_file_is_tracked_by_no_ignore_rule` (tests/test_client_sessions.py:97); verified by hand: `git check-ignore --no-index` exits 1 on the record, 0 on a sibling `other.jsonl` |
| 2 | The record's fields, id patterns, release or `unreleased` + 40-hex commit checked by `git cat-file -e` | proven | `RECORD_KEYS`/`CHALLENGE_KEYS`, `_check_release` (client_sessions.py); `git_commit_exists`; `test_an_unreleased_commit_resolves_against_the_real_repository`; parametrized refusals for unknown commit and short hash |
| 3 | Two field classes; content fields reported incomplete; stated-empty distinguishable from absent | proven | `REQUIRED_*`/`CONTENT_FIELDS`; `test_a_left_out_content_field_is_incomplete_not_refused`, `test_a_content_field_stated_empty_is_incomplete_and_says_so`, `test_an_explicitly_empty_challenge_list_is_complete`; absent `release`, `claims`, `shown`, `resolving_evidence` refused in `test_a_planted_defect_is_refused_naming_line_and_field` |
| 4 | Check over the committed file on every push; every listed refusal names line and field; empty file passes | proven | `test_the_committed_record_file_passes_the_check`, `test_a_planted_malformed_committed_file_fails_the_check`, the 47-case parametrized refusal test, duplicate-id and `corrects` tests, command exit 0/1/2 tests |
| 5 | Claims follow from the criterion: the procedure says so | proven (doc) | docs/client-session-record.md step 3 "The claims must follow from the criterion"; the read-back is order 4 |
| 6 | Backfilled marking and the Q67 entry rule | proven | `backfilled` required bool; read-back marking in `test_a_well_formed_file_reads_back_with_its_markings`; procedure section "Showings that predate the record" |
| 7 | No client name, client material or deal outcome; mapping outside the repo; checked by reading | proven | unknown keys refused at record and challenge level (`client_name`, `challenges[0].document` cases); ids are prefix + hex only; procedure "what never goes in the record" states the reading check |
| 8 | Append-only; corrections by appended record; history walk via blobs along `--first-parent`; shallow + CI fails; `fetch-depth: 0` | proven | `append_only_violations`; tests for append, edit, removal and deletion, merge of two appending branches, shallow clone under CI; ci.yml `fetch-depth: 0`. Extra check by hand: a side branch editing line 2, merged with `--no-ff`, is reported at the merge commit (git compares first parent only under `--first-parent`) |
| 9 | Written procedure, linked from results README, key order, output reading, id minting, mapping, English, correction, worked example in the doc | proven (content) / pending (walk) | `test_the_procedure_is_linked_from_the_results_readme`, `test_the_procedures_worked_example_passes_the_check_in_key_order`; walk by a non-author is the orchestrator's (evidence/walk-scenario.md) |
| 10 | `LICENSE-DATA` and `NOTICE.md` name the record under CC-BY 4.0; path required by the licence test | proven | LICENSE-DATA scope line; NOTICE.md; `tests/test_data_licence.py:145`; legal-code sha256 test passes |
| E | Evidence: the procedure walked once by someone other than its author | pending | the independent walk runs concurrently outside the worktree |

### Points the orchestrator asked to judge

- `fetch-depth: 0` on the `test` job: justified (the acceptance names it) and weakens nothing; it only fetches more history and tags. `release_version` tests mock `git describe`, so tag presence does not change them.
- The repository-history test reads blobs only (`git show <rev>:<path>`); on the committed state it walks one empty version and passes; before the commit it walks none and passes vacuously. It does not read the working tree.
- Robustness: root commit fine; file deletion or rename away is reported (the missing blob reads as empty); a rename into the path walks only the new path's history (acceptable). Shallow raises outside CI and is a violation under CI.
- Implementer additions (`challenges` required with `[]`, `release_commit` refused on a dated release, unknown keys refused, `shown` stated empty refused): consistent with the acceptance's "every format field in exactly one class" and "no field for" rules; none blocks a legitimate record the procedure describes.
- `PATHS_NOT_SHIPPED` entry: required once `LICENSE-DATA` names the record (archive `verify` refuses unlisted clone-only paths); static entry, archive stays deterministic; archive tests pass.
- The record file is 0 bytes: no fabricated session.

### Non-blocking findings

1. src/wave_local_ai_v2/client_sessions.py:472: `git log`'s return code is ignored, so a failing `git log` (bad HEAD, not a repository) reads as zero revisions and the walk passes vacuously; fail when `returncode != 0`.
2. docs/client-session-record.md:46-53: step 2 does not say the `release_commit` must exist in the clone the check runs in (pushed and fetched), so a commit made on another machine is refused with no hint why.
3. scripts/assemble_release_archive.py:140: the archive README links the record at the release commit, which by the entry's own reason is a stale snapshot (or absent for releases older than the record); consider wording the reason so a reader goes to `main` for the current version.
4. The CC-BY wrap in aidd_docs/results/NOTICE.md leaves a short ragged line ("here, are licensed under the Creative Commons"); cosmetic.
