---
type: story
status: ready
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
depends_on:
  - aidd_docs/backlog/stories/deterministic-classification-scoring-proves-quality-table-split.md
  - aidd_docs/backlog/stories/judge-scoring-with-inter-judge-agreement-proves-judged-machinery.md
  - aidd_docs/backlog/stories/translation-scoring-extends-deterministic-coverage.md
order: 4
---

# Story: Tiny dense models compared alongside MoE across all three use cases

**As** a consultant
**I want** tiny dense candidates (e.g. Granite 4 350M/1B, Qwen3 0.6B/1.7B/4B, Phi-4-mini, SmolLM3, Llama 3.2) scored on classification, translation, and rewriting alongside the MoE candidate already benchmarked
**So that** I can recommend whichever architecture actually performs best per use case, not assume MoE by default

## Acceptance

- For each of the three use cases, at least one tiny dense model and the MoE candidate are both present in the quality table with directly comparable scores.
- Results are shown side by side per use case, distinguishing which model produced which score.

## Cancellation

n/a — not cancelled.
