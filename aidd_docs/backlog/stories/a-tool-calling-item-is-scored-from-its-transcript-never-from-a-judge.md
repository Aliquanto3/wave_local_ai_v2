---
type: story
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish.md
  - aidd_docs/backlog/tasks/register-the-closed-harness-candidate-set-and-its-three-row-fields.md
order: 6
---

# Story: A tool-calling item is scored from its transcript, never from a judge

**As** a client-side engineer deciding whether a local model can drive our internal tools
**I want** an agentic tool-calling suite, run under `direct`, whose score is read off the stored transcript (the tool chosen, the arguments passed, the number of calls, whether the task succeeded) with the task's tokens, duration and energy summed over every generation it took
**So that** a low score reads as a named mismatch against the expected calls, and a model that needs twelve calls is never priced like one that needs three

Maps to: PRD AC "Given an agentic planning or tool-calling item, its score comes from a deterministic transcript check (expected tool, expected arguments, call count, task success) and never from a judge's opinion; the row names the harness used and its version, reports that harness's per-call prompt overhead separately from the task's own tokens, and reports tokens, duration and energy for the complete task alongside the number of generations it took"; PRD AC "Given the full use-case list, each of the nine task use cases ... has at least one task suite exercising it"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side"; Methodology 3, 4, 5, 9, 23; epic Boundaries "the agentic pair scored deterministically from the transcript", "agentic metrics aggregated per complete task", "tool-call transcript capture"; epic Sequence step 5; epic success checks 7, 8 and 10.

Needs: a real local model run; a cloud subject key already configured (Mistral or Google AI Studio) for the cloud rows.

Blocked: the open spike `aidd_docs/backlog/spikes/does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it.md`; if it finds that transcripts measure chat templates rather than models, this story is not built and the coverage record marks agentic tool calling `out-of-scope-this-release` with the finding as its reason.

## Acceptance

- A tool-calling suite is registered through the seam (order 1) with at least 20 items, EN, FR and DE each at 25% or more, every item tagged and provenanced. Each item carries, authored with it and versioned with the suite, its tool definitions, its expected tool, its expected arguments, its expected call count and its success condition.
- Local generations go through llama-server's `/v1/chat/completions` with the item's `tools` array under the model's own chat template; cloud generations go through the provider's chat API with the same tool definitions. The full transcript (every request, every returned tool call, every tool result fed back) is stored on the row.
- The score is computed from the transcript alone: tool selected, arguments passed, number of calls, task success. A mismatch is recorded as which of the four failed and what was expected, so it reads as a mismatch rather than as an unexplained low score (epic success check 7).
- A judge may annotate a row; deleting the annotation and recomputing leaves the score identical (epic success check 8). No contested threshold applies.
- Tokens, wall-clock duration and energy on the row are sums over every generation the task took, and the row records the generation count; for a planted task needing a known number of calls, the count on the row equals the calls in the transcript (epic success check 10).
- Every row carries the harness task's fields with harness `direct`.
- A generation that is empty, truncated, or whose tool call cannot be parsed scores 0, stays in the denominator, and records its reason.
- At least one local and one cloud batch are published, and the coverage record's tool-calling entry moves to `exercised` naming this suite.

## Code it changes

- `src/wave_local_ai_v2/local_client.py`: a tool-call path over `/v1/chat/completions` returning the transcript rather than one string.
- `src/wave_local_ai_v2/mistral_client.py`, `google_client.py`: the same for the cloud subjects.
- The suite's data file, its transcript scoring rule, and the per-task aggregation; the coverage record entry.

## Tests it needs

- Transcript scoring against fixture transcripts: right tool and arguments, wrong tool, wrong argument, extra call, no call, each producing its named result.
- A row's score is unchanged with its annotation deleted.
- A three-call fixture task records generation count 3 and the sum of the three generations' tokens and durations.

## Evidence it publishes

- The local and cloud batches with their transcripts, the suite snapshot, and the coverage entry.
- One MoE and one tiny dense roster entry run over the same items at one suite version and published side by side, each citing its roster entry; or, for an entry the tool-calling spike finds unable to emit parseable tool calls, a recorded refusal naming the entry and the finding.

## Cancellation

n/a: not cancelled.
