# Review: A publication subset redraws to the same items from its recorded rule

## Round 1

VERDICT: PASS

Gates: `uv run pytest -q` => `1353 passed, 2 warnings in 41.09s`, coverage 97.07% (floor 95%). `ruff check` => all checks passed; `ruff format --check` => 528 files already formatted; `mypy src/ scripts/` => no issues in 52 source files. `git diff --stat -- aidd_docs/results` is empty: committed snapshots and prompt-set hashes are unchanged.

### Acceptance, one by one

1. Rule recorded as data on the suite (benchmarks with licence and revision, seed, sampler version, loader and version, stable source key, canonical ordering): `subset_sampler.selection_rule` (subset_sampler.py:268), refused at load if incomplete or unknown (`check_selection_rule`, :308; registry `_check_selection`, suite_registry.py:223). Proved by `test_the_rule_records_every_field_the_replay_needs`, `test_a_rule_that_cannot_be_replayed_is_refused`. Met.
2. Stratified by construction (language always, label for classification): `_strata` (:446), `_stratify_problems` ties `stratify_by` to `task_suite` (:523). Proved by `test_a_classification_draw_is_stratified_by_language_and_label` (34/34/34, 9/9/8/8), `test_a_translation_draw_is_stratified_by_language_only`, `test_a_non_classification_rule_stratifies_by_language_only`. Met.
3. Retries record attempt count and every seed; final-seed-only refused: `draw_with_retries` (:242), `_seed_problems` (:500). Proved by `test_a_retried_draw_records_every_seed_tried`, the `"1 seeds for 3 attempts"` case, and registry `test_a_rule_recording_only_its_final_seed_never_loads`. Met.
4. Per-item content hash over normalised text, licence, source, revision: `content_hash` (:165). Proved by `test_the_content_hash_ignores_whitespace_and_composition_only`, `test_the_content_hash_covers_the_licence_and_the_revision`. Including the label for a classification source is consistent with the epic ("an upstream retag ... nameable at the item", epic line 40); the label is part of the item's own content, and `_stratify_problems` (:539) refuses a classification rule that leaves it out. Not scope creep. Met.
5. Replay: same rule => same ids and order; seed change differs; shuffled source changes nothing; nothing changed => nothing changes. Proved by `test_the_same_seed_and_source_return_the_same_ids_in_the_same_order`, `test_a_shuffled_source_returns_the_same_ids_in_the_same_order`, `test_a_changed_seed_changes_the_ids`, `test_replaying_the_rule_over_the_same_source_reproduces_it`, and the command-level `test_replaying_over_the_same_source_reproduces_it` / `test_a_changed_seed_fails_the_replay`. Met.
6. Edited source item named by id on replay: `replay` (:412). Proved by `test_an_edited_source_item_is_named_by_its_id_on_replay`, `test_a_retagged_source_item_is_named_by_its_id_on_replay`, `test_an_edited_source_item_is_named_and_fails_the_replay`. Met.
7. Publication gate on the first recorded seed: `test_the_draw_certifies_at_publication_on_the_first_seed` asserts `(attempts, seeds_tried, seed) == (1, [7], 7)` and `gate_suite(level="publication")`; `test_a_drawn_definition_registers_at_publication_with_its_rule` proves it through the registry. Met.
8. Fields are additions to the existing shape, not a fork: rule in `extra`, hash on the item, validated in `suite_registry._check_selection`; snapshot carries both (`test_a_drawn_definition_registers_at_publication_with_its_rule`). Met.

### Points judged

- Modified seam test `test_the_interval_epics_fields_are_additions_to_the_one_shape`: the earlier story's acceptance was "the shape accepts the ... fields as additions, without a second shape; those fields are not built here". The placeholders (`{"seed": 1, "n": 3}`, `"sha256:00"`) are meaningless now that the fields have a contract; the test still proves licence/source/revision/content_hash ride the one shape into the snapshot, and the selection-rule half is re-proved with real values by the drawn-suite test (snapshot equality on `selection_rule`). Property preserved. Acceptable.
- Determinism: no set or dict iteration feeds the draw unsorted (labels `sorted(set)`, languages from the `suite_gate.LANGUAGES` tuple, rows `sorted` by `(source, str(key))`); `random.Random(int)` does not use `hash()`. Verified: the drawn definition's SHA-256 is identical under `PYTHONHASHSEED` 0, 1 and 999 (`cf15ecacccb81870...`). Platform newlines: `normalise_text` collapses `\r\n`; a CRLF JSONL source with CRLF inside the text replays with exit 0.

### Blocking findings

None.

### Non-blocking findings

1. subset_sampler.py:231: the draw relies on CPython's `random.sample`/`_randbelow`, which Python documents as not guaranteed stable across versions (`requires-python = ">=3.12"`, open upper bound); the rule records no generator identity or interpreter version. Record it on the rule, or draw only from the `random()` stream Python guarantees.
2. tests/test_subset_sampler.py: no golden test pins the ids or a content hash for seed 7, so the ubuntu/windows CI matrix cannot catch cross-machine drift, which is the epic's whole point ("hold outside the machine that wrote it"). A pinned first-few-ids plus one hex digest would.
3. subset_sampler.py:460: a classification row without a label becomes a `"None"` stratum that shifts allocation and is refused only if drawn; `canonical_order` should refuse it up front.
4. The content hash is over the source row, not the suite item's `prompt`/`expected_label`; nothing yet ties the scored prompt to the hash ("provably the item that was scored"). Belongs to orders 7 and 8, worth naming there.
5. suite_registry.py:236: an item `content_hash` without a `selection_rule` is only format-checked, never verifiable; acceptable for this story, but a hash with no rule to replay it is decoration.
