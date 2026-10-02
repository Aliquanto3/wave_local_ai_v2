# Review: Each suite and machine publishes the local models not distinguishable from the best

## Round 1

VERDICT: CHANGES-REQUIRED

### Gates

- `uv run pytest -q`: `1804 passed, 2 warnings in 87.09s`, coverage 97.91% (floor 95%).
- `uv run ruff check .`: All checks passed. `uv run ruff format --check .`: 598 files already formatted.
- `uv run mypy src/ scripts/`: no issues in 56 source files.
- detect-secrets over every changed and untracked file: exit 0.
- `tests/test_data_licence.py` + `tests/test_leader_set.py`: 39 passed; `aidd_docs/results/leader-sets/NOTICE.md` exists, `LICENSE-DATA` names the directory.

### Acceptance, condition by condition

| # | Condition | Proved by | Holds |
| - | --------- | --------- | ----- |
| 1 | Analysis command writes one record per suite and machine class beside the families; nothing at read time; no row rewritten | `comparison.py` `--leader-sets` => `leader_set.publish` (`leader_set.py:585`); `test_two_members_one_excluded_and_the_cloud_never_listed`, `test_the_bundle_publishes_the_first_real_leader_set`; read model only reads records (`read_model.py` `_leader_membership`) | yes |
| 2 | Machine class from the fiche (hardware identity + compute mode); record names grouping fields; gpu and cpu_only never share a group | `leader_set.py:44-57,180-184`; `test_a_gpu_and_a_cpu_only_run_of_one_model_are_two_groups`; `grouping_fields`/`grouping_not_recorded` on the record | yes (see note) |
| 3 | Only local subjects; cloud never members | `leader_set.py:197`; cloud batch in `test_two_members_...` and `test_a_single_local_subject_...` | yes |
| 4 | Best = highest published suite score; tie named by a stated deterministic rule; others compared in one family, Holm over the closed set | `Group.reference` `leader_set.py:139-148`, `TIE_RULE`, `tied_at_top`; `test_a_tie_at_the_top_names_the_reference_by_the_stated_rule`; family `adjustment_size == 2` asserted | yes |
| 5 | member / excluded / not compared (naming the refused field), record incomplete | `_compared_entry` `leader_set.py:299-312`; `test_two_members_...`, `test_a_refused_comparison_is_not_compared_and_the_record_incomplete`, `test_an_observation_is_not_compared_naming_its_reason` | yes |
| 6 | Group of one: set of one, no comparison; no local subject: no record | `test_a_single_local_subject_is_a_set_of_one_without_a_comparison`, `test_rows_without_a_local_subject_publish_nothing` | yes |
| 7 | Record carries suite id/version, level, grouping fields and values, reference and tie rule, family id, each subject's run id and status | `build_record` `leader_set.py:371-408`; committed record `leader-sets/classification-support-routing@2.053c65354ff8.json` | yes (`suite_level` null: the bundle's rows predate it) |
| 8 | Immutable; a new family writes a new record superseding by id, old file unchanged | `resolve_record` `leader_set.py:480-506`; `test_a_grown_family_supersedes_the_leader_set_and_keeps_the_old_file` (byte comparison) | yes |
| 9 | Overview reads membership from the current record; no record keeps the stated absence; ranks nothing | `read_model.py` `_leader_membership`; `test_overview_quality_view_groups_by_task_suite_leader_and_cloud_provider` (an excluded higher-scoring run is not shown; suite-b absent), reference-bundle test | yes |
| 10 | Re-run over the published bundle alone returns identical records | `test_a_published_leader_set_recomputes_from_the_bundle_alone` (cited family removed, bytes equal); evidence `leader-sets-output.txt` second run `unchanged` | yes |

### Points judged

- Tie rule: the acceptance requires only a deterministic rule stated on the record; `tie_rule` and `tied_at_top` are on the record and tested. A tied subject is still compared against the reference, and an exact-match tie gives McNemar b = c (p = 1), so the pick does not change membership there. Not blocking.
- Family growth: `837e5355b954` holds the two committed pairs plus the leader comparison (3 members, all refused) and supersedes the head `1e1658cbe073`; no tracked file under `comparisons/` is modified (`git status`). `_suite_family` declares every head comparison, so `resolve_family_record`'s "only grows" check is satisfied; a superseded family is refused (`test_a_leader_set_never_reads_a_superseded_family`). Consistent with order 3.
- `not comparable` => `not compared` + `incomplete`: matches the acceptance for refusals; mapping observations the same way is the conservative reading. Overview shape: `{members, leader_sets}` or `pointer_unresolved` naming `leader_set`; the frontend renders any `Absent` and ignores the extra key, so nothing breaks at runtime (see non-blocking 1).
- `grouping_not_recorded`: acceptable. No code path today can produce a cpu_only run (`compute_mode`/`cpu_only` appear only in `leader_set.py`), the record names what it could not group on, and the separation is proved for fiches that carry the field.
- LICENSE-DATA scope: test passes, NOTICE present.

### Blocking

1. `aidd_docs/results/README.md:200-266`: the overview section is duplicated. Heading "What the overview withholds on day one, and why" appears at lines 200 and 234; the old bullet at 242 still says `leader_set_member` resolves and "Nothing in the repo writes it today", contradicting the new bullet at 208 and the new section at 443; the new block's coverage bullet (226) copies the dashboard section's text instead of the overview's (`CoverageAbsence.tsx`, line 263). Fix: keep one heading, the new leader bullet, the updated runtime bullet, and the original overview coverage bullet; delete the stale copy.

### Non-blocking

1. `frontend/src/views/overview/quality/types.ts:146-151`: `LeaderSet` does not mirror the new `leader_sets` key and the comment still names `leader_set_member`/`predates_schema`; `incomplete` is not shown on the card. Out of this story's scope; worth a follow-up.
2. `leader_set.py:559-560`: `member_key` is directional, so a head family holding B vs A plus a leader comparison A vs B would declare one pair twice and count it twice in Holm. Edge case; normalise or refuse the reversed duplicate.
3. `read_model.py` `_leader_membership`: `record["subjects"]`, `subject["status"]`, `record["incomplete"]` are read outside the guarded `current_leader_sets` call, so a well-formed JSON record missing them raises (500) instead of `pointer_unresolved`.
4. Two batches of one model are two subjects: the committed record lists `Qwen3.6-35B-A3B` as member and as not compared, and so `incomplete`. Defensible under "each subject's run id"; worth the owner's eye.
5. A use case spanning several suite versions or machine classes where only some have a record shows the recorded members without stating the others' absence.

## Round 2

VERDICT: PASS

### Gates

- `uv run pytest -q`: `1809 passed, 2 warnings in 82.64s`, coverage 97.91%.
- ruff check: All checks passed; ruff format: 599 files already formatted; mypy: no issues in 56 source files.

### Round 1 findings

- Blocking 1 (README duplication): fixed. `aidd_docs/results/README.md` holds one "What the overview withholds" heading (line 200) with the new leader bullet (208), the runtime bullet (220) and the overview's own `CoverageAbsence.tsx` coverage bullet (226); no "Nothing in the repo writes it today" text remains.
- Non-blocking 2 (reversed pair): fixed. `leader_set.py:564-567` declares a pair once whatever its direction, and `build_record` (`leader_set.py:353-356`) reads the member in either direction; `test_a_pair_the_family_holds_the_other_way_round_is_not_declared_twice` proves the family is not grown (size 1, same id) and both subjects read `member`.
- Non-blocking 3 (unguarded record reads): fixed. `read_model.py:1222-1241` reads every record field inside `try/except (KeyError, TypeError)` and returns `pointer_unresolved`; `test_a_malformed_leader_set_record_is_unresolved_not_a_failure`, `test_a_leader_set_record_missing_its_incomplete_flag_is_unresolved`.
- Committed records: `leader-sets/classification-support-routing@2.053c65354ff8.json` and `comparisons/classification-support-routing@2.model.837e5355b954.json` keep their content-addressed names, and `test_a_published_leader_set_recomputes_from_the_bundle_alone` still reproduces the leader-set bytes.
- Non-blocking 1, 4 and 5 stand as follow-ups (frontend type mirror, two batches of one model as two subjects, partial-record absence on a multi-suite card).
