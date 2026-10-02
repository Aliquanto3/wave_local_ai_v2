---
type: story
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md
  - aidd_docs/backlog/stories/the-same-tool-calling-items-run-under-each-compared-harness.md
order: 8
---

# Story: An agentic plan is scored against its authored step set

**As** a client-side engineer evaluating whether a small model can plan a multi-step task before acting
**I want** an agentic-planning suite whose score comes from the transcript against an expected step set authored and versioned with each item, under `direct` and the campaign's compared harnesses
**So that** a disagreement about a plan's quality is a visible suite-version question rather than a judge's opinion moving a score

Maps to: PRD AC "Given an agentic planning or tool-calling item, its score comes from a deterministic transcript check (expected tool, expected arguments, call count, task success) and never from a judge's opinion ..."; PRD AC "Given the full use-case list, each of the nine task use cases ... has at least one task suite exercising it"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side"; Methodology 3, 4, 5, 9, 23; epic Boundaries "six suites" (agentic planning), "the agentic pair scored deterministically from the transcript"; epic Sequence step 6; epic success check 8.

Needs: a real local model run; a cloud subject key already configured (Mistral or Google AI Studio) for the cloud rows.

Blocked: the open spike `aidd_docs/backlog/spikes/does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it.md`, the same gate as order 6; if it sends tool calling out of scope, agentic planning goes out of scope with it and the coverage record names the finding as the reason.

## Acceptance

- A planning suite is registered through the seam (order 1) with at least 20 items, EN, FR and DE each at 25% or more, every item tagged and provenanced. Each item carries, authored with it and versioned with the suite, its tools, its expected step set (which steps, and the ordering constraints between them that the task actually imposes), and its success condition.
- It reuses order 6's transcript capture, per-task aggregation and generation count, and order 7's adapters for every framework order 7 found comparable, with no planning-specific capture path. If the spike leaves no framework comparable and order 7 is not built, planning runs under `direct` only and states that.
- The score is computed from the transcript against the expected step set and the success condition; a missing, extra or misordered step is recorded by name.
- If an annotation rubric is authored, judge annotations go through the shipped judge protocol, carry no contested threshold, and deleting one leaves the score identical (epic success check 8).
- Empty, truncated or unparseable generations score 0, stay in the denominator, and record their reason.
- At least one local and one cloud batch under `direct`, and one batch under each framework order 7 found comparable, are published, and the coverage record's planning entry moves to `exercised` naming this suite.

## Code it changes

- The suite's data file and its step-set scoring rule; the coverage record entry.

## Tests it needs

- Step-set scoring against fixture transcripts: exact plan, a missing step, an extra step, a violated ordering constraint, each producing its named result.
- An annotated fixture row scores identically with the annotation deleted.

## Evidence it publishes

- The batches with their transcripts, the suite snapshot, and the coverage entry.
- One MoE and one tiny dense roster entry run over the same items at one suite version and published side by side, each citing its roster entry; or, for an entry the tool-calling spike finds unable to emit parseable tool calls, a recorded refusal naming the entry and the finding.

## Cancellation

n/a: not cancelled.
