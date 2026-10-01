---
type: story
status: proposed
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source.md
  - aidd_docs/backlog/stories/a-publication-subset-redraws-to-the-same-items-from-its-recorded-rule.md
  - aidd_docs/backlog/stories/every-quality-batch-publishes-its-interval-and-what-it-could-resolve.md
order: 7
---

# Story: A publication-level classification suite stands beside the hand-written one

**As** an academic or technical reviewer weighing the classification results
**I want** a classification score over a seeded subset of a named public benchmark, at the publication level, published beside the hand-written 20-item score and never averaged with it
**So that** I can see whether a finding on the small, uncontaminated suite survives at a scale where a 10-point gap can be resolved

Maps to: PRD AC "Given a published suite, its rows state whether it was built to the development or the publication level, and a publication-level suite names each public benchmark its subset came from, that benchmark's licence, and the selection rule that produced the subset"; PRD AC "Given a published quality score, it is shown with a bootstrap confidence interval"; PRD Dependencies "Licence and redistribution terms of the public benchmarks whose subsets seed the publication-level suites"; Methodology 4, 5, 24; epic decisions "The two levels coexist", "The licence spike returns one of three verdicts, each with its consequence written in advance"; epic success check 12 (classification half).

Needs: a real local model run (one published batch on the bench machine), after the licence spike has returned its verdict.

Blocked: by the spike `aidd_docs/backlog/spikes/which-public-classification-benchmark-seeds-the-publication-suite-and-on-what-terms.md`, and by owner question Q3 (cloud retry budget and per-item resume at this scale, cloud batches only) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`. Q1 is answered (a): the suite seam is `aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md`, declared in `depends_on`.

## Acceptance

- A new classification suite id exists beside `classification-support-routing`. The hand-written suite keeps its id, its items, its CC-BY 4.0 licence, its published rows and its `development` level.
- The new suite certifies at `publication` (order 4): it holds 300 items where its source supplies them and never fewer than 100, records which target it was built to and why, and each of EN, FR and DE holds at least 25% of its items.
- Its items are drawn by order 5's sampler from the benchmark the spike names, stratified by language and label, with the selection rule, each item's licence, source, source revision and content hash recorded. Replaying the rule returns the same item ids in the same order.
- Every drawn item is marked contamination-risk under Methodology 5.
- The spike's verdict is applied as the epic wrote it in advance: permissive ships items and rows unchanged; share-alike segregates the drawn items and their derived rows under their own licence file; no-redistribution carries `prompt` and `expected_label` on the rows redacted to the per-item content hash. Whichever applies is written into `aidd_docs/results/README.md` beside the statement of what the bundle is.
- The coverage record's `exercised` entry for classification gains this second suite id, on the shape `no-use-case-is-silently-absent` agrees; no new use-case entry is created.
- At least one batch over the new suite is published in the reference bundle as new rows, carrying its level and its interval block, under the supersede-don't-backfill discipline.
- No published table averages the two levels: the development-level score leads and the publication-level score sits beside it as the scale check. [Methodology 4]

## Code it changes

- The suite definition and its items, in the form the suite seam settles (data rather than generated Python source is the epic's stated direction; the decision is the seam's).
- `quality_cli.py`'s suite selection, through the registry if it exists by then.

## Tests it needs

- The suite certifies at `publication`; its replay returns the recorded ids; every item carries licence, source, revision, content hash and contamination-risk; the hand-written suite's snapshot and `prompt_set_hash` are unchanged.

## Evidence it publishes

- The selection-rule record, the published batch with its intervals, and the README section stating the licence rung applied.

## Cancellation

n/a: not cancelled.
