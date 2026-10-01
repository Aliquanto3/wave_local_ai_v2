---
type: story
status: ready
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
order: 3
---

# Story: The published bundle reads as four flat tables and their column dictionary

**As** a third-party researcher with a spreadsheet, R or DuckDB and no Python
**I want** the published bundle as flat tables, one row per thing, with every pointer already resolved into columns and a dictionary stating what each column means
**So that** I can recompute the published headline numbers from the per-item rows without cloning the repository, running code, or following a hash across files

Maps to: PRD User Story "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself"; PRD AC "the published results are also available as a tabular export readable outside the repo without running it"; epic Boundaries "a tabular export command over the published bundle", "CSV as the contract" (the CSV half) and "a documented, versioned table schema"; epic decisions "The export is derived, never authoritative" and "The export declares the schema it read"; epic success checks 1 (four tables read with nothing installed), 2 (recomputation, the accuracy half) and 6 (dictionary and tables agree both ways).

Needs: none. The export runs over the committed bundle; no model run, API key, hardware or operator is required.

Current state: the bundle is five parts and "No one file in this set is self-sufficient" (`aidd_docs/results/README.md`). The committed rows are `schema_version` `"7"` while `row_contract.SCHEMA_VERSION` is ahead. Runtime dependencies hold no data stack.

## Acceptance

- A packaged command writes four CSV tables from the published bundle: quality per item (one row per quality row), runtime aggregates (one row per runtime row), fiches (one row per fiche), roster (one row per roster entry). It reads `runtime-reference.jsonl`, `quality-reference.jsonl`, `fiches/`, `aidd_docs/roster/models.json` and `suite-definitions/`, and nothing else: it runs no benchmark, does not read the untracked `runtime.jsonl` or `quality.jsonl` unless explicitly pointed at them, and changes no file of the bundle.
- Every pointer a row carries is resolved into columns of that row: `fiche_hash` into the machine fields of its fiche, `roster_entry_id` into the model fields of its roster entry, `suite_id` and `suite_version` into the suite fields of its definition. Nested fields (`sampling`, `language_breakdown`, `failure_counts`, `verdict`) become named columns. Reading one table needs no join.
- The export computes no number the rows do not carry. Per-repetition arrays stay in the bundle, not in the runtime aggregates table, and the dictionary says so.
- A column dictionary lists every column of every table with its meaning, its unit, and the row field it came from. Every column in the tables is in the dictionary and every dictionary column is in a table; a test fails on either mismatch.
- The export declares the bundle `schema_version` it read (today `"7"`), never the live `row_contract.SCHEMA_VERSION`, and carries each row's own `schema_version` as a column. If the bundle is regenerated first, the declaration follows the bytes with no code change.
- Absence stays absence: a field a row does not carry is an empty cell, never a zero and never a back-fill, and the dictionary states what an empty cell means in each column. Where a row records an explicit null and another row does not carry the field, a reader can tell the two apart.
- Fields this bundle does not hold yet (the interval block, item licence and source, the roster's licence block) are named in the dictionary as not carried by the bundle that was read, with the epic that owns each. Comparison and family records are not a table here: that is owner question Q2 and `the-tabular-export-carries-the-interval-and-the-comparison-record.md`.
- The CSV format is pinned rather than defaulted: encoding, delimiter, quoting, line ending and float formatting are explicit, and floats round-trip to the value in the row. Two runs over the same bundle produce byte-identical files on both CI operating systems.
- The command uses the standard library alone: the runtime dependency set in `pyproject.toml` is unchanged.
- From the quality table alone, each published run's `suite_accuracy` and per-language accuracy are recomputed from the per-item `correct` column and equal the published values. This check is run against the committed bundle and its result recorded.

## Code it changes

- `src/wave_local_ai_v2/`: a new export module and its entry point in `pyproject.toml` `[project.scripts]`; read-only use of `row_contract.py`, `fiche_registry.py`, `roster.py`.
- `aidd_docs/results/README.md`: how to produce the tables, and the recomputation result.

## Tests it needs

- Over the committed bundle: four tables, the declared schema version is `"7"`, every pointer resolved, the dictionary and tables agree both ways, the accuracy recomputation matches.
- Over a constructed bundle: a row missing a field exports an empty cell, a recorded null is distinguishable from a missing field, a float with many digits round-trips, and two runs are byte-identical.

## Evidence it publishes

- The recomputation of every published run's accuracy from the exported quality table, recorded in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
