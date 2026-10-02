---
type: story
status: ready
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/every-quality-batch-publishes-its-interval-and-what-it-could-resolve.md
  - aidd_docs/backlog/stories/a-comparison-family-carries-its-adjusted-p-values-and-is-superseded-not-edited.md
  - aidd_docs/backlog/stories/the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary.md
  - aidd_docs/backlog/stories/comparison-family-and-leader-set-records-read-as-a-fifth-table.md
order: 6
---

# Story: The tabular export carries the interval and the comparison record

**As** a third-party researcher re-analysing the published results
**I want** each published interval with its qualifiers, and each comparison and family record, in the tabular export beside the per-item scores they were computed from
**So that** I can recompute every interval and every paired test myself without cloning and running the project

Maps to: PRD User Story "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself"; PRD AC "the published results are also available as a tabular export readable outside the repo without running it"; Methodology 24; epic Boundaries "the tabular export carrying the interval and the comparison record"; epic success check 11 (recomputation from the bundle alone); owner answer to Q2 (option a, 2026-10-01).

Needs: none. The export runs over the committed bundle; no model run, API key, hardware or operator is required.

Split, per the owner's answer to Q2 (`aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`): `one-download-holds-the-tables-their-licences-and-how-to-cite-them` owns the export command, its schema, its column dictionary and the release asset, and its fifth table carries the comparison, family and leader-set records. This story owns the existence and correctness of the statistical columns: it supplies their definitions and proves, against ourselves, that a reader recomputes the published values from the exported tables.

## Acceptance

- The per-item quality table carries each row's interval block (interval bounds, confidence level, resample count, method, seed, generator identity and version, draw-procedure id), the minimum detectable effect and any named null reason, as columns whose meaning, unit and null reasons this story defines and the column dictionary states.
- The column definitions of the comparison and family records (every field order 2 and order 3 write, including the refusals and the null reasons) are supplied to the fifth table's dictionary from this epic, never redefined there; a dictionary entry for a statistical column that disagrees with the record definition fails a test.
- Rows written before the interval existed show the interval columns as empty cells with a documented meaning, never a zero and never a back-fill.
- From the exported tables alone, a reader recomputes one published interval using its recorded seed, method and resample count, and one published McNemar comparison from the per-item columns, and lands on the values the quality table and the fifth table publish. This check is run against ourselves and its result recorded.

## Code it changes

- The export module and column dictionary of `the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary.md`: the interval block columns of the quality table and their dictionary entries.
- The record definitions of orders 2 and 3, exposed as the column definitions the fifth table (`comparison-family-and-leader-set-records-read-as-a-fifth-table.md`) reads.

## Tests it needs

- Over a constructed bundle holding intervals and a family record: every interval column appears; an interval-less row exports empty cells; the dictionary's statistical entries match the record definitions; a recomputation from the exported tables matches the published interval and p-value.

## Evidence it publishes

- The recomputation from the exported tables, recorded in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
