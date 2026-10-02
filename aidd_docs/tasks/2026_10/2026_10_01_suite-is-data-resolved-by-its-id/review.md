# Review: A suite is data resolved by its id, not an import in the CLI

## Round 1

VERDICT: PASS

Gates (run by the reviewer):

- `uv run pytest -q` => `1201 passed, 2 warnings in 36.69s`, coverage 96.70% (floor 95%).
- `uv run ruff check .` => `All checks passed!`; `uv run ruff format --check .` => `509 files already formatted`; `uv run mypy src/ scripts/` => `Success: no issues found in 49 source files`.

### Acceptance, condition by condition

1. Shape holds id, version, the four M3 constraints, scoring-rule name, items with language/provenance/contamination-risk, items as data: met. `SuiteDefinition` in `src/wave_local_ai_v2/suite_registry.py`; items in `src/wave_local_ai_v2/suite_data/*.json`; per-item tags enforced by the gate at load (`suite_registry.py:185`, `suite_gate._check_item_declaration`).
2. Registry resolves an id; `--suite` takes a registered id; unregistered id refused naming the registered ones; unknown scoring rule refused naming it: met. `suite_registry.py:279-292`, `suite_registry.py:174-180`, `quality_cli.py:226,235`. Tests: `test_an_unregistered_id_is_refused_naming_the_registered_ones`, `test_an_unknown_scoring_rule_is_refused_naming_the_rule` (test_suite_registry.py), `test_an_unregistered_suite_id_is_refused_naming_the_registered_ones` (test_quality_cli.py, also proves no server started and no row written).
3. Every definition gated at load, gate consumed not reimplemented, refused definition never run: met. `suite_registry.py:185` calls `suite_gate.gate_suite`; the CLI reads `spec.gate`. Tests: `test_an_item_missing_its_tag_is_refused_by_the_gate_at_load`, `test_a_definition_the_gate_refuses_is_never_registered`.
4. Two shipped suites migrated with no item, prompt or cap changed; versions and `PROMPT_SET_HASH` unchanged; snapshots byte for byte; no row rewritten: met and independently verified. Reviewer extracted HEAD's `src/` (`git archive HEAD src`) and compared: HEAD constants are `3 / d41a2134...596a / 32 / [] / 32768 / disabled` and `2 / 16150e44...7574 / 128 / [] / 32768 / disabled`, identical to the registry's; HEAD's `classification_snapshot()`/`translation_snapshot()` equal the new `build_snapshot(resolve(id))` exports (`True`). `git diff --exit-code HEAD -- aidd_docs/results/` => exit 0; no untracked file under `aidd_docs/results/`. Tests: `test_a_shipped_suite_keeps_its_version_and_prompt_set_hash` (literal hashes pinned), `test_regenerating_the_snapshots_reproduces_the_committed_files`, `test_every_committed_definition_equals_its_export_byte_for_byte`.
5. A further suite is a new definition plus, where scoring differs, a named rule, with no edit to `quality_cli.py`; shown end to end with HTTP stubbed: met. `test_a_suite_registered_outside_the_cli_runs_end_to_end` registers a fixture definition and a fixture rule and runs `_run` through local + Mistral stubs; rows pass the writer gate (row_contract resolves through the registry, `row_contract.py:566`). `test_the_cli_holds_no_suite_table_and_imports_no_suite_module` guards the CLI.
6. Shape accepts the interval epic's fields as additions without a second shape: met. Unknown top-level keys kept in `extra` (`suite_registry.py:199`) and exported in the snapshot; unknown item keys stay on the item. Test: `test_the_interval_epics_fields_are_additions_to_the_one_shape`.

### Points the caller asked to judge

- Items moved from `src/*.py` literals to `suite_data/*.json`: required, not scope creep. The acceptance says "The items live as data, not as Python literals", and Q1's owner answer (a) is "items stored as data". Q43 itself anticipated this ("two files with mixed terms until Q1 moves items into data").
- Old `--suite classification|translation` refused, no alias: allowed. The acceptance says `--suite` "takes a registered suite id" and refuses an unregistered one; it asks for no alias. Default invocation unchanged (`DEFAULT_SUITE = "classification-support-routing"`). Documented in README, `docs/setup.md`, CHANGELOG, `aidd_docs/memory/cli.md`; no script, CI or doc in the repo still calls the short values (CHANGELOG history line 216 excepted).
- Hashes and snapshots byte-identical: confirmed (see condition 4).

### Blocking findings

None.

### Non-blocking findings

1. Backlog: `aidd_docs/backlog/stories/the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives.md:30,34` (Q43 consequence) names `classification_suite.py`/`translation_suite.py` as modules holding item literals; after this story they hold none. The notice belongs on `src/wave_local_ai_v2/suite_data/` (and `judge_probe.py`, which still holds `JUDGE_PROBE_ITEMS` literals). Needs a backlog edit before that story starts.
2. Backlog: `a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source.md` (interval order 4) still describes its fields as literals in the suite modules; they now land as JSON keys via `extra`/item keys.
3. `exact_label_match` scores against the classification module's fixed `LABELS` (`scoring.py:31,171`), so a further suite reusing that rule with a different label set would mis-score silently; a future label-set suite needs its own rule or a declared label set.
4. Open shape: a misspelt optional key is carried rather than refused (accepted tradeoff in the plan's Decisions); the interval stories should validate the keys they add.
5. Stale comment: `tests/test_results.py:300` still says `--suite translation`.
