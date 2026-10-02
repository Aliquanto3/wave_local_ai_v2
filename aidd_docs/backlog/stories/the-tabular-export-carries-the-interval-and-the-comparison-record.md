---
type: story
status: done
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/every-quality-batch-publishes-its-interval-and-what-it-could-resolve.md
  - aidd_docs/backlog/stories/a-comparison-family-carries-its-adjusted-p-values-and-is-superseded-not-edited.md
order: 6
---

# Story: The tabular export carries the interval and the comparison record

**As** a third-party researcher re-analysing the published results
**I want** each published interval with its qualifiers, and each comparison and family record, in the tabular export beside the per-item scores they were computed from
**So that** I can recompute every interval and every paired test myself without cloning and running the project

Maps to: PRD User Story "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself"; PRD AC "the published results are also available as a tabular export readable outside the repo without running it"; Methodology 24; epic Boundaries "the tabular export carrying the interval and the comparison record"; epic success check 11 (recomputation from the bundle alone).

Needs: none. The export runs over the committed bundle; no model run, API key, hardware or operator is required.

Blocked: the export command does not exist yet (`one-download-holds-the-tables-their-licences-and-how-to-cite-them` has no story), and the split between the two epics is stated only from that epic's side (mechanism, schema and release asset there; existence and correctness of the statistical columns here) while this epic records it as open. Its four declared tables (quality per item, runtime aggregates, fiches, roster) hold no place for a comparison or family record. Owner question in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`.

## Acceptance

- The per-item quality table carries each row's interval block (interval bounds, confidence level, resample count, method, seed, generator identity and version, draw-procedure id), the minimum detectable effect and any named null reason, as columns whose meaning the column dictionary states.
- Every comparison and family record in the bundle reaches the export with every field it carries, including the refusals and the null reasons; a refused comparison is a visible row, never a missing one.
- Rows written before the interval existed show the interval columns as empty cells with a documented meaning, never a zero and never a back-fill.
- From the exported tables alone, a reader recomputes one published interval using its recorded seed, method and resample count, and one published McNemar comparison from the per-item columns, and lands on the published values. This check is run against ourselves and its result recorded.

## Code it changes

- The export command owned by `one-download-holds-the-tables-their-licences-and-how-to-cite-them` (not yet built): the interval columns, and the comparison and family records as tables, defined in its column dictionary. Which epic writes which part is the owner question above.

## Tests it needs

- Over a constructed bundle holding intervals and a family record: every field appears; an interval-less row exports empty cells; a recomputation from the exported tables matches the published interval and p-value.

## Evidence it publishes

- The recomputation from the exported tables, recorded in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
