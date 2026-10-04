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

Blocked: by the spike `aidd_docs/backlog/spikes/does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it.md` (`blocked`): its harness half (Follow-up run 4: lockfile resolution, captured call sequence and overhead readability per framework, P1 and P4 on `qwen3-0.6b-q8` and the MoE) is not yet run; desk research gives no framework an "unable" verdict. And through `depends_on` on `a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md` (`proposed`), blocked by the same spike's runs 1-3. If no framework beyond `direct` proves comparable, this story is not built and the harness comparison is published out of scope with `direct` as the lone reference.

Current state (verified on `main` at `c68b23e`, 2026-10-03): `harness.py` closes the set at five and implements only `direct`; none of the four framework packages is a dependency in `pyproject.toml`. `HARNESS_DISTRIBUTIONS` reads `smolagents`, `langgraph`, `pydantic-ai` and `llama-index-core`; the spike's lockfile probe installs `pydantic-ai-slim[openai]`, under which a `pydantic-ai` version read raises `HarnessError`. `comparison.py` already excludes `harness_version` from the configuration difference only when every row is `direct`. No campaign declaration exists in code (`a-campaign-is-declared-as-data-and-an-empty-cell-fails-it.md` is `ready`, unbuilt), so there is no harness list and no three-harness cap refusal.

## Acceptance

- An adapter exists for each of `smolagents`, `langgraph` and `pydantic-ai` that the spike found able to drive a local llama-server endpoint; each pinned in the lockfile. A framework the spike found unable is recorded as unmeasurable with the finding published, and no adapter approximates it.
- Each adapter produces the same transcript shape as `direct`, so the order 6 scoring rule scores it unchanged; a framework that will not surrender its call sequence in that shape is recorded as unmeasurable rather than scored.
- A run takes its harness list from the campaign declaration (`a-campaign-is-declared-as-data-and-an-empty-cell-fails-it`, owned by `the-engine-and-the-prompt-variant-are-measured-not-assumed`), which as written declares engines and variants but no harness list; this story adds the harness list to that declaration's shape rather than forking a second declaration. The run refuses a list of more than three, naming the cap. Which three, and whether every agentic model or only those passing the `direct` suite is compared, is declared there, not chosen here.
- Each adapter keeps its framework's request defaults rather than aligning them with `direct` (owner answer Q109 (a), 2026-10-03). Every row records the `tool_choice`, `parallel_tool_calls` and `stream` its request actually sent, read from the captured request on the transcript, with a field the request did not carry recorded as not sent. A failure the spike traces to an engine defect met under a framework's default (llama.cpp #27767 under smolagents' `tool_choice: required`, #24807 under LlamaIndex's streaming) is published as a harness-by-engine finding naming the defect, the harness and the engine build.
- Every row carries a new field, `harness_client_version`: the installed version of the client package that built the engine request, `langchain-openai` for `langgraph` and `llama-index-llms-openai-like` for `llamaindex`, read at run time like `harness_version`, and null for `direct`, `smolagents` and `pydantic-ai` (owner answer Q110 (c), 2026-10-03). This story carries the field and its schema bump, together with the three request fields above; the done harness task is not reopened. If order 5 (`a-rag-answer-is-scored-over-a-local-corpus-under-a-named-harness.md`) lands first and has already added these fields, this story reuses them and its schema version with no second bump.
- Two rows for the same item under two harnesses differ in harness id, harness version and per-call prompt overhead, each naming its own (epic success check 9, read off the two rows).
- Per-task aggregation and the generation count apply under every harness exactly as under `direct`.
- At least one batch under each comparable framework is published beside the `direct` batch over the same items and the same model.

## Code it changes

- One adapter module per comparable framework, against the harness registry.
- `src/wave_local_ai_v2/harness.py` and `row_contract.py`: `harness_client_version` and the three request fields, with the schema bump (unless order 5 added them first); `HARNESS_DISTRIBUTIONS["pydantic-ai"]` reconciled with the distribution the adapter installs, since the spike's lockfile probe installs `pydantic-ai-slim`, under which a `pydantic-ai` version read raises `HarnessError`.
- `pyproject.toml` and `uv.lock`: the comparable frameworks, pinned.

## Tests it needs

- With the engine stubbed, each adapter's transcript for a fixture item scores identically to the `direct` transcript of the same calls.
- A four-harness list is refused naming the cap.
- An adapter's recorded version equals its installed package's version, and its `harness_client_version` equals the installed client package's version for `langgraph` and `llamaindex` and is null for the other three.
- A row's recorded `tool_choice`, `parallel_tool_calls` and `stream` equal those in its captured request.

## Evidence it publishes

- The per-harness batches, and per framework the per-call overhead on the smallest roster model, which the epic asks to record once done.

## Cancellation

n/a: not cancelled.
