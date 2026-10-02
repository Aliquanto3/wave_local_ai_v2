# Review: Comparison, family and leader-set records read as a fifth table

## Round 1

VERDICT: CHANGES-REQUIRED

Gates (reviewer run): `uv run pytest -q` => `1814 passed, 2 warnings in 89.69s`, coverage 97.94% (floor 95%); `ruff check` => All checks passed; `ruff format --check` => 603 files already formatted; `mypy src/ scripts/` => no issues in 56 source files.

### Acceptance, condition by condition

1. Fifth table, one row per comparison with its family, plus family and leader-set records, kind readable from a column: met. `bundle_export.py:1956` `_record_rows`; `record_kind` column; comparison rows carry `family_*`. Proved by `test_the_fifth_table_flattens_every_record_kind` (Counter of kinds, `family_family_id` per comparison) and `_assert_the_table_is_the_records` (every leaf of every record has a column).
2. Refused comparison, refused member, named null reason visible: met. Same test: 3 refusal rows, `comparison_adjusted_p_value` empty, `comparison_adjusted_p_value_null_reason == "comparison_refused"`, `comparison_refusal` holds the reason, not-compared subject carries its reason.
3. Superseded family stays a row, link readable: met. Old family stays its own `comparison_family` row; the superseding row's `family_supersedes` names the old `family_id`; the dictionary entry and README state "a record no other record names here is current". No `superseded_by` column: acceptable, the acceptance asks the link readable "from the table", not from the old row, and an inverted column would be a value no record carries (acceptance 4).
4. Export computes nothing: met. `_assert_the_table_is_the_records` checks every cell equals the record value at the dictionary's `source` path, and `fields_not_carried` matches absence, over the constructed and the committed bundle.
5. Dictionary both ways; absent kinds named with owner; header-only table: met for an empty record directory (`test_record_kinds_the_bundle_does_not_hold_are_named`, `test_the_dictionary_and_the_tables_agree_both_ways` iterates `TABLES`). NOT met for a bundle without the directories: see blocking 1.
6. Format pinning, stdlib only, byte-identical rerun: met. `test_two_runs_are_byte_identical_and_the_format_is_pinned` now runs over the constructed records bundle; `test_the_command_uses_the_standard_library_alone` (new imports `comparison`, `leader_set` are stdlib-only too). No committed record edited: `test_the_export_changes_no_bundle_file` hashes `comparisons/` and `leader-sets/`. Every pointer resolved or refused: `test_a_record_citing_what_the_bundle_does_not_hold_is_refused` (supersedes, leader-set family_id, run_id).

### Blocking

1. `src/wave_local_ai_v2/bundle_export.py:1734`: a missing `comparisons/` or `leader-sets/` directory refuses the whole export. When the story was written neither directory existed in the committed bundle (`git ls-tree docs/slice-remaining-epics aidd_docs/results/`; they were added by 74e1b45 and 15e0e5b), and the acceptance's "today all three ... are named in the dictionary as not carried ... and the table is written with its header and no rows rather than omitted" describes exactly that bundle. With this code such a bundle is unexportable. The fiche-directory analogy does not hold: rows require fiches, analysis records are optional per the acceptance. Fix: a missing record directory reads as holding no record of that kind (kinds named `carried=false`, header-only table, manifest row with the path and 0 entries); keep refusing a path that exists but is not a directory, and keep refusing malformed files. Replace the `"no record directory"` case in `test_unreadable_bundle_parts_are_refused` with a test exporting a bundle that has neither directory, and update the `cli.md` / README wording.

### Non-blocking

1. Committed-bundle test asserting no kind is named not carried (`test_blocks_owned_elsewhere_are_named_with_their_owner`, `test_the_fifth_table_over_the_committed_bundle`): fine. "Today all three" is stale since the dependencies landed; the naming path is proved on the constructed bundle.
2. `bundle_export.py:1750` `_check_record_pointers`: a malformed `members`/`subjects`/`supersedes` (not a list of objects) raises `AttributeError`/`TypeError` instead of a named `ExportError`.
3. Version-1 family records leave `adjusted_p_value_null_reason` null on a refusal (empty cell); faithful to the record and stated in the README, but a reader of v1 rows relies on `comparison_refusal` for the reason.
4. Reading the current family requires scanning every `family_supersedes` cell; documented, acceptable.

## Round 2

VERDICT: PASS

Gates (reviewer run): `uv run pytest -q` => `1824 passed, 2 warnings in 91.54s`, coverage 97.95%; ruff check, ruff format --check, mypy clean.

- Round 1 blocking 1 resolved: `_read_records` returns no record for a missing directory, refuses a non-directory path ("is not a record directory") and malformed files. `test_a_bundle_without_record_directories_holds_no_record` proves acceptance 5 for a bundle predating both directories: header-only `comparison_records.csv`, the three kinds `carried=false`, manifest rows with the path and `entries_read` 0, and no directory created. cli.md:156 and results README:99 state the rule.
- Round 1 non-blocking 2 resolved: `_entries` / `_record_id` and the `isinstance(value, str)` pointer check refuse malformed `members`, `subjects`, `supersedes`, ids and pointers with a named `ExportError` (`test_a_malformed_record_is_refused_by_name`, 9 cases).
- Acceptance 1-4 and 6 unchanged from round 1 and still proved.

No blocking findings. Non-blocking: plan.md's Decisions row still says a missing directory refuses (stale task doc, not code).
