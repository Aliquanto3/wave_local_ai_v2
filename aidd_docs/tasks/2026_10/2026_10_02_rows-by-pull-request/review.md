# Review: Each machine returns its rows by pull request, and a hash collision is refused

- **Verdict**: changes-requested
- **Diff**: `777778b..4327561...working tree (uncommitted)`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 1 critical, 2 warning, 3 minor

## Phases

### Phase 1 — Per-machine tracked locations and the promotion command

- [x] One tracked location per declared machine holding runtime, quality, refusals — `machine_results.py` `Location`; `.gitignore:32` ignores only top-level `*.jsonl` (`git check-ignore` on `machines/laptop-mobile-gpu/runtime.jsonl`: not ignored)
- [x] Named run's rows land with their fiches — `test_machine_results.py::test_a_named_run_lands_in_its_machines_location_with_its_fiches`, `::test_the_promoted_lines_are_the_live_lines_byte_for_byte`
- [x] Foreign `machine_id` refused — `::test_a_row_of_another_machine_is_refused_naming_it`, `::test_a_row_with_no_machine_id_is_refused`
- [x] Unknown `run_id` refused naming it — `::test_an_unknown_run_id_is_refused_naming_it`
- [x] Promoting twice is idempotent — `::test_promoting_twice_is_idempotent`
- [x] Fiches content-addressed, never overwritten — `::test_a_differing_tracked_fiche_is_refused_never_overwritten`, `::test_a_fiche_missing_from_the_live_registry_is_refused`
- [x] Refusals moved from `REFUSALS_DIR` to `machines/<id>/refusals.jsonl`: justified (location's third file, no second tracked copy; no refusal file was ever committed under `aidd_docs/results/refusals/`); story 4 tests green (`test_preflight.py`, `test_cli.py`, `test_quality_cli.py`, `test_judge_probe.py` in the 2444 passed)

### Phase 2 — The merge command, its collision and undeclared-machine refusals

- [x] Byte-identical re-merge — `test_bundle_merge.py::test_two_machines_merge_into_one_deterministic_bundle`
- [x] Collision refused naming both rows, both machine ids, the hash, never choosing — `::test_a_collision_is_refused_naming_both_rows_ids_and_hash`, `::test_the_cli_writes_then_checks_then_refuses`; evidence `dryrun-output.txt`
- [x] Undeclared machine id refused — `::test_an_undeclared_machine_id_is_refused`; undeclared location `::test_a_location_of_an_undeclared_machine_is_refused`
- [x] Refusal records only in `refusals-reference.jsonl` — `::test_refusal_records_go_only_into_the_refusals_file`

### Phase 3 — The derived-bundle CI check and the three bundle-level assertions

- [x] CI "Derived bundle" step runs `--check` after pytest in both matrix legs, gated by `required` — `.github/workflows/ci.yml:37-41`; `test_ci_workflow.py::test_the_test_job_checks_the_bundle_is_derived`
- [x] Hand-edited bundle fails — `test_bundle_merge.py::test_a_hand_edited_bundle_fails_the_check`, `::test_a_hand_edit_of_the_pinned_snapshot_fails_the_check`
- [x] `PRE_MERGE_SNAPSHOT` pin tested both ways (passes only with empty locations and unchanged bytes; fails on edit or promoted row; write refuses overwrite) — `::test_the_pinned_snapshot_passes_only_while_no_location_holds_a_record`, `::test_the_merge_never_overwrites_the_pinned_snapshot`, `::test_the_cli_reports_the_pinned_snapshot_and_refuses_to_overwrite_it`; nothing outside `bundle_merge.py` and those tests references it; order 6's `git mv` makes `_snapshot_copy` tests fail, forcing its removal
- [x] Three bundle assertions in `tests/test_reference_bundle.py` — vacuous on the schema-7 snapshot, proven to bite by `::test_the_three_bundle_assertions_refuse_a_constructed_violation`
- [x] Real repo: `uv run wave-local-ai-v2-merge-bundle --check` => "committed bundle is the pinned schema-7 snapshot, unchanged", exit 0

### Phase 4 — The per-machine loop and the operator-carried fallback in docs; results README; CHANGELOG; constructed dry run

- [x] README replaces the "no CLI ever writes to them" rule and says so — `aidd_docs/results/README.md:17-18`
- [x] Fallback documented with operator-carried trailers — `docs/setup.md` 6.2; proven in throwaway local repos only (`evidence/gitflow.sh`: bare repo in scratch, `remote -v` shows only it, no real push/PR)
- [ ] Per-machine loop passes the check suite — `docs/setup.md:731-745`: the machine PR adds rows without regenerating the bundle, so its own "Derived bundle" step is red (reproduced in scratch: second machine's rows + previous bundle => `--check` exit 1, "differs from what the merge derives")
- [ ] Real per-machine PRs (three machines, one with no GPU) — legitimately pending: operator + other machines (epic Success Evidence), pro-PC waived by D1; republished bundle pending order 6

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 critical | functional | 4 | `docs/setup.md:731-745`, `:781` | Documented loop is unpassable: step 5 says merge the machine PR "once `required` is green", but a PR that adds location rows without the derived bundle always fails `--check`; step 6 regenerates the bundle only after merge. The gitflow evidence merges locally and never runs `--check` per branch, so it hides this. | Make the machine PR run `wave-local-ai-v2-merge-bundle` and commit the regenerated bundle with its location (on a conflict after another machine's PR lands: rebase, re-run the merge, never hand-resolve); drop or rewrite step 6 and fallback step 5; add a `--check` per branch in `gitflow.sh` |
| 🟡 warning | rot | 4 | `aidd_docs/memory/coding-assertions.md:36-42` | CI table lists 3 steps per leg; the new "Derived bundle" step is missing from the contract table | Add the row `uv run wave-local-ai-v2-merge-bundle --check` |
| 🟡 warning | fit | 3 | `src/wave_local_ai_v2/bundle_merge.py:50`, `:264` | Until order 6, any committed record (incl. a pre-flight refusal written straight into a location) turns CI red and write mode refuses; transitional, intended, but undocumented in setup.md | State in setup.md 6.1 that no location may be committed before the bundle republication story |
| 🟢 minor | rot | 4 | `CHANGELOG.md:48` | Story 4's Unreleased entry still names `aidd_docs/results/refusals/<machine_id>.jsonl` (`REFUSALS_DIR`), removed in the same release | Point it to the location or rely on the `Changed` entry explicitly |
| 🟢 minor | rot | - | `.gitignore:30` | Comment still calls the `*-reference.jsonl` files "curated snapshots" | Reword to "derived bundle" |
| 🟢 minor | code | 2 | `src/wave_local_ai_v2/bundle_merge.py:202` | A row with no `run_id` keys as `"None"`; two such rows in two locations get a misleading "run 'None' is in both" refusal | Refuse a row without `run_id` explicitly |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 89% (17/19)                                       |
| Files checked | bundle_merge.py, machine_results.py, fiche_registry.py, results.py, settings.py, preflight.py, ci.yml, test_bundle_merge.py, test_machine_results.py, test_reference_bundle.py, test_ci_workflow.py, docs/setup.md, results/README.md, CHANGELOG.md, evidence/* |
| Unchecked     | per-machine loop passes the check suite — fix; real per-machine PRs and republished bundle — not-applicable (operator, other machines, order 6) |
| Unplanned     | none                                              |

Gates: `uv run pytest -q` => `2444 passed, 2 warnings in 167.45s`; ruff check, ruff format --check, mypy src/ scripts/ clean.

## Round 2

- **Verdict**: approve
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 1 minor

| Round-1 finding | Status | Evidence |
| --- | --- | --- |
| 🔴 loop unpassable | fixed | `docs/setup.md` 6.1 steps 5-7: merge + `--check` on the branch, one commit with location, fiches, bundle; rebase, take `main`'s bundle, re-merge, never hand-resolve; 6.2 step 5 same. `evidence/gitflow-output.txt`: `--check` exit 0 on every branch tip, tower branch "conflicts with main (bundle files)" then rebase + re-merge => "2 runtime, 1 quality", final main check exit 0; remotes only the scratch bare repo |
| 🟡 coding-assertions CI table | fixed | `aidd_docs/memory/coding-assertions.md` row 3 `merge-bundle --check` |
| 🟡 CI-red until order 6 undocumented | fixed | `docs/setup.md` "Until the bundle republication story" paragraph |
| 🟢 CHANGELOG story 4 path | fixed | `CHANGELOG.md:48-49` names `machines/<machine_id>/refusals.jsonl` |
| 🟢 `.gitignore` comment | fixed | `.gitignore:30-32` |
| 🟢 missing `run_id` | fixed | `bundle_merge.py:203-208` (rows only, refusals untouched); `test_bundle_merge.py::test_a_row_without_a_run_id_is_refused_naming_it` |

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | rot | 4 | `evidence/gitflow.sh` (pro-pc refusal line) | Constructed refusal record carries `run_id`, a field outside `row_contract.REFUSAL_FIELDS` | Drop it from the fixture line |

Gates: `uv run pytest -q` => `2445 passed, 2 warnings in 165.34s`; ruff, format, mypy clean; real repo `merge-bundle --check` => pinned schema-7 snapshot unchanged, exit 0.

Status: story can be marked `done`. Remaining evidence (real per-machine PRs on three machines, republished bundle) is legitimately pending: operator, other machines (D1 waives pro-PC), order 6; no acceptance line of this story requires it.
