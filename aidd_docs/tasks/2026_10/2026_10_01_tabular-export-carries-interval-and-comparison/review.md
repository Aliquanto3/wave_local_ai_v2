# Review: the tabular export carries the interval and the comparison record

## Round 1 (2026-10-02)

VERDICT: PASS

Contract: the PR-head story text on `docs/slice-remaining-epics`, with owner answers Q2 (a) and Q42 (a).

### Acceptance, condition by condition

1. **Interval block as described columns.** Met. The quality table carries `score_interval_*` columns (header, generator, draw procedure, suite and per-language bounds, MDE, null reason). The export refuses any row field the dictionary does not describe. Proved by `test_a_row_carrying_its_interval_exports_every_cell_described` and `test_the_interval_columns_agree_with_the_block_they_describe` (checks `HEADER_KEYS`, `GENERATOR_KEYS`, `CELL_KEYS`, the constants and `NULL_REASONS` against the dictionary). The draw-procedure entry states the procedure in full (`bundle_export.py:491-503`), checked against `score_interval._index_stream`, `quantile` and `bootstrap_cell`.
2. **Record definitions supplied, never redefined, and drift fails a test.** Met. `comparison.FAMILY_RECORD_FIELDS` and `COMPARISON_RECORD_FIELDS`, plus `leader_set.LEADER_SET_RECORD_FIELDS` and `SUBJECT_RECORD_FIELDS`, sit on `field_doc.FieldDoc`, and `bundle_export._record_row` (`:1737-1768`) reads them. Proved by:
   - `test_the_export_reads_the_record_definitions_it_does_not_redefine`: identity of the registries.
   - `test_record_columns_state_the_record_definitions`: each cell, with mutation.
   - `test_every_value_a_record_field_takes_is_named_in_its_definition`: refusals, kinds, verdicts and directions.
   - `test_every_null_reason_the_analysis_writes_is_defined`.
   - `test_every_member_field_the_analysis_writes_is_described`.
3. **Pre-21 rows show empty cells, never zero or back-filled.** Met. In a mixed bundle, the pre-21 row shows empty cells and lists them in `fields_not_carried`. A null-block row also shows empty cells but does not list them. The dictionary states both cases. All of this is in the extended `test_a_row_carrying_its_interval_exports_every_cell_described`. An export where every row predates 21 has no interval columns, and the dictionary names `score_interval` as not carried, with the statistics epic as owner (`test_blocks_owned_elsewhere_are_named_with_their_owner`). That follows the bundle epic's rule of one column per carried field, so it is consistent.
4. **Recomputation from the exported tables alone.** Met against ourselves.
   - `scripts/recompute_from_export.py` uses only the standard library (`test_the_reader_imports_nothing_from_the_project`, which parses its imports with `ast`) and reads only the two CSVs.
   - It recomputes intervals, McNemar and Holm. Writer parity was checked against `holm_adjust`, `HOLM_ADJUSTED_OVER` and `bootstrap_cell`.
   - Tests: `test_every_published_interval_and_comparison_is_recomputed`, `test_a_changed_published_value_is_caught`, and the procedure-refusal, two-blocks and exit-code tests.
   - The result is recorded in `aidd_docs/results/README.md`.
   - Reproduced by the reviewer: committed export gives `0 values recomputed (none), 0 differ`; the built bundle gives `96 values recomputed (holm, interval, mcnemar), 0 differ`.
   - The story's own Tests section prescribes "a constructed bundle", and the README labels the values plainly as not published results. So the condition is proved, and only evidence over real published values is pending.
   - The acceptance asks for one McNemar comparison, not every comparison, so leaving Wilcoxon out is not a gap.

### Gates

- `uv run pytest -q`: `2001 passed, 2 warnings in 152.12s`, coverage 98.04%.
- `uv run ruff check .`, `ruff format --check .` and `uv run mypy src/ scripts/` are clean.
- The export is still byte-identical: two runs over the committed bundle, `diff -r` empty.
- `bundle_export` takes only constants and registries from `score_interval`, `comparison` and `leader_set`, so it computes nothing.
- `git status --short aidd_docs/results` shows only `README.md`, so no committed record was edited.

### Non-blocking findings

1. **Evidence over real values is pending.** The README promises a re-run "once a schema-21 batch and a tested comparison are committed", but no backlog item or owner tracks that re-run.
2. **The leader-set move is beyond orders 2 and 3, but justified.** Q42 (a) puts the leader set with the statistics epic, and the owner cell of the leader-set columns already named that epic. Without the move, "never redefined there" would be false for those columns. The move is small and changes no behaviour (the only removed line in `leader_set.py` is an import).
3. **The reader can false-positive on some batch shapes.** `scripts/recompute_from_export.py:144-175` groups a batch by (run_id, provider, model_id, prompt_variant_id) and resamples every row in the group, including rows with no block. A batch split on another axis, or a probe or partial row sharing the key, would print MISMATCH. This fails loudly, not silently.
4. **Interval meanings hard-code the current constants.** The dictionary entries embed the current `CONFIDENCE_LEVEL`, `RESAMPLES` and draw-procedure text (`bundle_export.py:466-503`). A future block version would read a stale meaning. The reader refuses an unknown procedure, so this is safe for now.
5. **The evidence depends on a test helper.** `evidence/build_published_bundle.py` imports `tests/published_bundle_fixtures.py` through `sys.path`, so the evidence breaks if that helper moves.
