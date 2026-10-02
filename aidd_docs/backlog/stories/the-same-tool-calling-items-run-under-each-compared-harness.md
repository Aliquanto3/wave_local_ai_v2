---
type: story
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md
  - aidd_docs/backlog/stories/a-campaign-is-declared-as-data-and-an-empty-cell-fails-it.md
order: 7
---

# Story: The same tool-calling items run under each compared harness

**As** a consultant recommending a whole stack for an agentic use case, not only a model
**I want** the tool-calling items run under the frameworks a campaign declares beside `direct`, each row naming its harness, that harness's version and the prompt tokens it spent before the task began
**So that** I can say which combination of a small model and a harness does the job, and how much of the model's context each framework costs, rather than assume one framework

Maps to: PRD Goals "the benchmark answers which inference engine, which agentic harness and which prompt variant serve a given use case best"; PRD AC "Given an agentic planning or tool-calling item, ... the row names the harness used and its version, reports that harness's per-call prompt overhead separately from the task's own tokens ...; the campaign compares at most three harnesses"; PRD Non-Goals (multi-agent role-orchestration frameworks); Methodology 23; epic Boundaries "the agentic harness as a recorded row dimension", "tool-call transcript capture" (per harness); epic Sequence step 5 (comparative half); epic success check 9.

Needs: a real local model run.

Blocked: the open spike `aidd_docs/backlog/spikes/does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it.md`, whose harness half decides which frameworks are comparable; if none beyond `direct` is, this story is not built and the harness comparison is published out of scope with `direct` as the lone reference.

## Acceptance

- An adapter exists for each of `smolagents`, `langgraph` and `pydantic-ai` that the spike found able to drive a local llama-server endpoint; each pinned in the lockfile. A framework the spike found unable is recorded as unmeasurable with the finding published, and no adapter approximates it.
- Each adapter produces the same transcript shape as `direct`, so the order 6 scoring rule scores it unchanged; a framework that will not surrender its call sequence in that shape is recorded as unmeasurable rather than scored.
- A run takes its harness list from the campaign declaration (`a-campaign-is-declared-as-data-and-an-empty-cell-fails-it`, owned by `the-engine-and-the-prompt-variant-are-measured-not-assumed`), which as written declares engines and variants but no harness list; this story adds the harness list to that declaration's shape rather than forking a second declaration. The run refuses a list of more than three, naming the cap. Which three, and whether every agentic model or only those passing the `direct` suite is compared, is declared there, not chosen here.
- Two rows for the same item under two harnesses differ in harness id, harness version and per-call prompt overhead, each naming its own (epic success check 9, read off the two rows).
- Per-task aggregation and the generation count apply under every harness exactly as under `direct`.
- At least one batch under each comparable framework is published beside the `direct` batch over the same items and the same model.

## Code it changes

- One adapter module per comparable framework, against the harness registry.
- `pyproject.toml` and `uv.lock`: the comparable frameworks, pinned.

## Tests it needs

- With the engine stubbed, each adapter's transcript for a fixture item scores identically to the `direct` transcript of the same calls.
- A four-harness list is refused naming the cap.
- An adapter's recorded version equals its installed package's version.

## Evidence it publishes

- The per-harness batches, and per framework the per-call overhead on the smallest roster model, which the epic asks to record once done.

## Cancellation

n/a: not cancelled.
