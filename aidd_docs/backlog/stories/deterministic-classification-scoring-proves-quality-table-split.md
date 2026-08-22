---
type: story
status: done
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
order: 1
---

# Story: Deterministic classification scoring proves the quality-table split

**As** a consultant
**I want** classification task-suite results scored deterministically against one local model and one cloud model
**So that** I have proof the quality-scoring machinery works end-to-end, in a table kept separate from the existing runtime table, before adding more use cases or models

## Acceptance

- Running the classification task suite against one local SLM and one cloud model produces a deterministic quality score for each, using the same prompts.
- The quality score for each run appears in a quality table, structurally separate from the runtime table.
- No hardware fiche or runtime metric is required to read a quality score, and vice versa.

## Cancellation

n/a — not cancelled.
