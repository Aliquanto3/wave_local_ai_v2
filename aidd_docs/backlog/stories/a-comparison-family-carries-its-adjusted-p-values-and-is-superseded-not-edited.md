---
type: story
status: done
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/two-configurations-on-the-same-items-receive-a-paired-test-or-a-refusal.md
order: 3
---

# Story: A comparison family carries its adjusted p-values and is superseded, not edited

**As** an academic or technical reviewer reading many pairwise comparisons from one roster
**I want** every comparison published inside a declared, closed family whose multiplicity-adjusted p-values were computed over exactly the comparisons it holds
**So that** a "significant" pair among twenty-eight is not just the one that came up by chance, and an adjusted p I read today is not silently wrong once the family grows

Maps to: PRD AC "given a claim that two models, engines or prompt variants differ, it is shown with a paired ... test's p-value and effect direction, or it is not presented as a difference"; Methodology 24 ("The unit of the published artifact is the comparison family"); Methodology 19 (a store is never rewritten); epic decision "Multiplicity is stated, and the family is the artifact"; epic success check 10.

Needs: none. Constructed rows exercise every case; no model run, API key, hardware or operator is required.

## Acceptance

- One analysis invocation writes one family record holding every comparison it ran, the family's definition, its size, and each member's Holm-adjusted p computed over that closed set.
- The default family is one suite crossed with one compared dimension, closed at analysis time, as Methodology 24 states it. The family definition is written on the record, so a reader can see what was adjusted together.
- Each member's reader-facing verdict (order 2) is evaluated against its adjusted p at the declared alpha, and the raw p stays beside it.
- A family record is immutable once written. Adding a twelfth comparison to a family of eleven writes a new family record that supersedes the old one by id; the old record stays published and unchanged, and no already-published record is rewritten.
- A family of one states an adjusted p equal to its raw p rather than omitting the field.
- A refused comparison is listed in the family as refused, naming its field. It carries no p-value to adjust, and the record states how many members were tested and how many were refused, so the size the adjustment ran over is visible.
- Re-running the analysis over the same bundle and the same family definition returns an identical family record.

## Code it changes

- The comparison module from order 2: the family record, Holm over a closed set, supersede-by-id.
- The analysis command: grouping comparisons into families by the default definition; writing one family record per invocation.

## Tests it needs

- Holm against a published worked example and a hand-computed fixture; a family of one; a family of eleven grown to twelve produces a new record superseding the old, with the old file byte-identical.
- A refused member is listed and excluded from the adjustment count.

## Evidence it publishes

- The family records the analysis command writes over the committed bundle, recorded in `aidd_docs/results/README.md` beside order 2's records.

## Cancellation

n/a: not cancelled.
