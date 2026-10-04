# Review: A drawn item reaches the download under its own terms, or as a visible hole

## Round 1

VERDICT: PASS

Scope: the uncommitted working tree on top of `c830e6e` (10 modified files, `tests/drawn_bundle_fixtures.py`, this task folder). Commit `c830e6e` itself is outside this story.

### Gates run by the reviewer

- `timeout 900 uv run pytest -q`: `3183 passed, 20 skipped, 2 warnings in 293.08s`, coverage 98.53% (floor 95%).
- `timeout 900 uv run --isolated --locked --group release pytest tests/test_assemble_release_archive.py tests/test_release_parquet.py --no-cov`: `67 passed in 37.21s`.
- `uv run ruff check .`, `ruff format --check .`, `mypy src/ scripts/`: all clean. `detect_secrets` pre-commit hook on the changed files: exit 0, and `.secrets.baseline` is unchanged.
- The live archive was built twice at `HEAD` without `--parquet`. Both zips have SHA-256 `8da9bcf7...`, so the builds are byte-identical. Each holds 46 entries, which is the evidence's 51 minus its 5 Parquet copies, and no code entry.

### Acceptance

1. Item-terms columns. Proven. `test_a_drawn_item_exports_its_terms_and_a_hand_written_one_its_named_hole` (tests/test_bundle_export.py) checks that drawn rows match their suite item's licence, source, revision and hash. It also checks that a hand-written row has `CC-BY-4.0` and an empty hash cell whose dictionary reason names `prompt_set_hash` (`ITEM_TERMS_FIELDS`, bundle_export.py). When a row and its item disagree, `_agreed` refuses the export (test case `hash`).
2. LICENSE-DATA section 2, repeated in the archive README. Proven. `test_the_readme_repeats_licence_data_section_two` checks the verbatim copy on the live archive and on all three constructed archives. `test_a_permissive_archive_holds_each_source_s_notices` checks the Apache-2.0 text beside the WMT24++ items, the five CC BY 4.0 elements for MInDS-14 and "Changes made". The rung rules and the content-hash recipe are tested by `test_section_two_states_what_each_rung_does_and_the_content_hash_recipe`.
3. Share-alike. Proven on a constructed bundle. `test_a_share_alike_set_ships_apart_under_its_own_licence_file` checks that the set's `LICENSE`, rows and snapshot all sit under `aidd_docs/results/share-alike/CC-BY-SA-4.0/`, that none of it appears in the CC-BY 4.0 files, and that only those 2 rows carry `item_licence_file`.
4. No redistribution. Proven on a constructed bundle. `test_a_redacted_item_is_a_visible_hole_its_reader_can_fill_by_hand` checks that no archive file holds the withheld text and that the row carries the redaction mark, revision and key. It recomputes the hash with an independent implementation of the README recipe from a fixture source row. It also checks that the README gives exactly one instruction for the source, and that the redacted snapshot items use only the allow-listed keys. Malformed shapes are refused by 20 parametrised cases in `test_item_terms_the_export_cannot_state_faithfully_are_refused`. The dictionary's "cannot be recomputed" statement is asserted.
5. `provenance` entry. Proven. `test_every_provenance_value_exported_is_named_in_its_entry` checks it on the live export, and an unnamed value is refused (case `provenance`). A grep finds no remaining "hand-written only" or "nothing drawn" statement in LICENSE-DATA, the results README, the snapshot NOTICE or the export.
6. Archive refusals. Proven. The archive now refuses an undeclared source or a source at the wrong rung (`test_a_drawn_source_licence_data_does_not_name_at_its_rung_is_refused`), a redacted snapshot item that still holds text, and a `.py` entry (`test_a_shipped_script_or_an_unredacted_snapshot_fails_verify`). Existing gates keep their tests green.
7. Evidence it publishes. Pending (owner). The first `v*` tag with a drawn subset and its Release asset are still to come. The local build and the constructed redacted row are in `evidence/`.

### Implementer choices

- The share-alike area under `aidd_docs/results/` is justified: LICENSE-DATA places it "in the published results directory", and the archive ships bundle parts at their repository paths.
- Nulling `prompt_before_template` is justified, since it carries the same text and "no file carries the text" requires it.
- The new `source_key` / `item_source_key` fields are justified: today's items hold the key only inside `item_id`, and the acceptance names the key as a value of its own.
- `pragma: allowlist secret` appears only on public dataset revisions, public content hashes and the fictional `0123...` revision.

### Non-blocking

1. scripts/assemble_release_archive.py (PATHS_NOT_SHIPPED): `README.md` was added to `named_by` for `machines/`, `suite_data/` and `scripts/wmt24pp_suite.py`. This narrowly widens the clone-only gate, and it is needed by the verbatim repeat of section 2.
2. bundle_export.py `_read_share_alike`: `item_licence_file` is `licence.as_posix()`, so an absolute `--share-alike-dir` leaks a machine path into the table. The archive and the default CLI use relative paths, so they are not affected.
3. On a redacted classification row, `predicted_label` is not nulled. A correct row therefore reveals the withheld `expected_label`. This is within the acceptance's letter (it names three fields), but worth an owner note before a real no-redistribution source lands.
4. The README instruction says only "obtain it from its publisher". It gives no URL, although the section 2 subsection repeated above it would carry one.
5. `item_redaction` `not_redacted` is defaulted by the export for rows that predate the field. This is a documented decision (plan, Decisions table), not a read value.
