---
type: story
status: done
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
order: 4
---

# Story: A suite is certified to its declared level, and every item names its licence and source

**As** an academic or technical reviewer reading a published score
**I want** every row to name the level its suite was certified to, and a suite that declares the publication level to fail at that level when it is too small, unbalanced or carries an item without a licence and a source
**So that** a 20-item development score is never mistaken for a publication-level one, and a suite that falls short of what it claims fails loudly instead of passing quietly at the lower level

Maps to: PRD AC "Given a published suite, its rows state whether it was built to the development or the publication level, and a publication-level suite names each public benchmark its subset came from, that benchmark's licence, and the selection rule that produced the subset" (the level, licence and source halves; the selection rule is order 5); Methodology 4, 5; epic decisions "The two levels coexist", "The licence lives on the item, not only on the suite", "Provenance and licence stay author declarations"; epic success check 1.

Needs: none. Constructed suites exercise every case; no model run, API key, hardware or operator is required.

Current state: `suite_gate.py` knows one level (`MIN_SUITE_ITEMS = 20`, `MIN_LANGUAGE_SHARE = 0.25`, `MIN_PER_LANGUAGE_CELL_ITEMS = 10`) and returns `indicative` with its reasons. `_VALID_PROVENANCE` already accepts `licensed`, but no item records which licence or which source.

## Acceptance

- A suite declares its level, `development` or `publication`. `development` keeps today's constants and behaviour unchanged.
- `publication` requires at least 100 items, keeps the 25% share for each of EN, FR and DE, and requires every item to carry a licence and a source with that source's revision. A publication suite also records which size target it was built to, 300 items where its public source supplies them or the 100-item floor where it does not, and why; the gate checks the item count against the target the suite declared. [Methodology 4]
- `gate_suite` returns the level it certified. A suite declaring `publication` with 99 items fails to that level naming the count; the same suite at 100 items with one language below 25% fails naming the language. It never passes quietly at `development` instead.
- Every quality row names the level its suite was certified at. `classification-support-routing` and `translation-business-short-form` still certify at `development` with the same verdict as today, and their rows name that level.
- An item's licence is carried on the item, not only on the suite: the source's own licence for a drawn item, CC-BY 4.0 for the repo's hand-written items. Adding these declarations to the hand-written items changes neither their text nor their `prompt_set_hash`.
- `contamination_risk` stays forced to `provenance == "public"`; nothing here verifies that a declared licence or source is true, and `aidd_docs/results/README.md` says so.
- The new contract fields (the level, the item licence, the item source and its revision) are declared unrendered in the view partition; whether the pitch renders them is that epic's call.

## Code it changes

- `src/wave_local_ai_v2/suite_gate.py`: the second level, its checks and the certified level in `SuiteGateResult`.
- `src/wave_local_ai_v2/classification_suite.py`, `translation_suite.py`: the level declaration and the per-item licence on the hand-written items.
- `src/wave_local_ai_v2/row_contract.py`, `quality_rows.py`: the level on every quality row; `SCHEMA_VERSION` bump.
- `src/wave_local_ai_v2/read_model.py`: the new fields declared unrendered.
- `src/wave_local_ai_v2/suite_snapshot.py`: the published snapshot carries the level and the item licence.

## Tests it needs

- `tests/test_suite_gate.py`: 99 items at `publication` fails naming the count; 100 items with one language at 24% fails naming the language; an item without a licence or a source fails at `publication` naming the item; a suite declaring the 300 target and holding 250 fails naming the target; both hand-written suites certify at `development` unchanged.
- Rows from a development and a publication fixture each name their level.

## Evidence it publishes

- A snapshot export of each hand-written suite carrying its level and item licences, its `prompt_set_hash` shown unchanged; an already-published snapshot file is never overwritten.

## Cancellation

n/a: not cancelled.
