---
type: story
status: ready
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
order: 2
---

# Story: LLM-as-judge scoring with inter-judge agreement proves the judged-scoring machinery

**As** a consultant
**I want** rewriting task-suite results scored by two independent cloud LLM judges, with their agreement reported
**So that** I have proof the open-ended judging path works before extending it to more use cases

## Acceptance

- Running the rewriting task suite against one local SLM and one cloud model produces a judged quality score for each, using two independent cloud judges (e.g. Mistral + Google AI).
- Every judged result is shown with both judges' scores and their agreement level — never a judged score without it.
- Judged results appear in the same quality table structure as deterministic results, distinguishable as judged.

## Cancellation

n/a — not cancelled.
