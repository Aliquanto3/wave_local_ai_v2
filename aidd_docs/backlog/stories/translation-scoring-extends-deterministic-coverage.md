---
type: story
status: ready
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
depends_on: aidd_docs/backlog/stories/deterministic-classification-scoring-proves-quality-table-split.md
order: 3
---

# Story: Translation scoring extends deterministic coverage to a second use case

**As** a consultant
**I want** the translation task suite scored deterministically against the same models
**So that** I can show a second use case works on the proven scoring machinery, without yet widening the model roster

## Acceptance

- Running the translation task suite against the same local SLM and cloud model used in the classification Story produces a deterministic quality score for each.
- The result appears in the quality table alongside classification and rewriting results, attributable to the translation use case.

## Cancellation

n/a — not cancelled.
