---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
order: 2
---

# Story: Rows carry a schema version and a writer gate refuses an incomplete row

**As** a client-side engineer auditing a published row
**I want** every row to declare the schema it was written under, and the harness to refuse to write a row missing a required field
**So that** a missing value means the value was genuinely unavailable rather than that the code forgot it, and every schema-shaped criterion has a way to fail

## Acceptance

- Methodology 19: every runtime and quality row carries `schema_version`; a reader selects rows by that version.
- Methodology 19: a live per-machine store is never rotated or rewritten when the schema moves; rows of several versions coexist in one file and are separated at read time.
- A row missing any field the contract requires for its kind cannot be written: the writer raises, names the missing fields, and appends nothing.
- The contract is declared in one place per row kind (runtime, quality) and is the single list every later story extends; adding a required field to it fails the tests of any writer that does not supply it.
- A field whose value was genuinely unavailable is written as an explicit null, which the gate accepts; an absent key is not.

## Code it changes

- `src/wave_local_ai_v2/row_contract.py` (new) — `SCHEMA_VERSION`, the required-field set per row kind, and the validation that names what is missing.
- `src/wave_local_ai_v2/results.py` — `append_row` validates against the contract before writing; `read_rows` gains selection by schema version.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — both writers stamp `schema_version` and pass their row kind.

## Tests it needs

- `tests/test_row_contract.py` (new) — a complete constructed row passes; a row missing one required field is refused with that field named; an explicit null passes.
- `tests/test_results.py` — nothing is appended when validation fails (file unchanged, no partial line); rows of two schema versions in one file are selectable by version.
- `tests/test_cli.py`, `tests/test_quality_cli.py` — both CLIs write a contract-valid row against stubbed HTTP.

## Evidence it publishes

- `tests/test_row_contract.py` is the epic's first success check — the one that makes criteria 2, 3, 5, 9, 13, 15, 16 and 19 able to fail rather than only able to be described.
- `schema_version` appears on every row of the regenerated reference bundle (order 19).

## Cancellation

n/a — not cancelled.
