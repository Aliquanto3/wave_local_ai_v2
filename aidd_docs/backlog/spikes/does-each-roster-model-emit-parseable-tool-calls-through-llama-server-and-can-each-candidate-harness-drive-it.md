---
type: spike
status: open
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parents:
  - aidd_docs/backlog/stories/a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md
  - aidd_docs/backlog/stories/the-same-tool-calling-items-run-under-each-compared-harness.md
  - aidd_docs/backlog/stories/an-agentic-plan-is-scored-against-its-authored-step-set.md
---

# Spike: Does each roster model emit parseable tool calls through llama-server, and can each candidate harness drive it?

## Question

For each roster GGUF, does its chat template, served by the pinned llama-server build through `/v1/chat/completions` with `--jinja` and a `tools` array, return tool calls the server parses into structured `tool_calls`, and when it does not, is the failure attributable to the model or to its template? And for each of `smolagents`, `langgraph`, `pydantic-ai` and `llamaindex`: does it drive a local llama-server endpoint at all, does it surrender its call sequence in a transcript shape comparable to `direct`'s, and is its per-call prompt overhead readable rather than inferred?

## Decision

Whether agentic tool calling and agentic planning are built as suites or marked `out-of-scope-this-release` with this spike's finding published as the reason (the epic's first conditional trigger); per roster model, whether its rows are evidence of the model or of its template; and which candidate frameworks are comparable, which are recorded as unmeasurable, and whether the harness comparison is out of scope with `direct` published as the lone reference (the epic's third conditional trigger).

## Bounds

- Evidence needed: per roster entry in `aidd_docs/roster/models.json`, a small fixed set of tool-calling probes (single call, call with typed arguments, no call expected, two sequential calls) run against the pinned build, recording the raw response, whether `tool_calls` was populated, and the template in force (`local_client.chat_template`); for a failure, the same probe under a known-good template or against the model's documented tool format, to separate model from template; per framework, its pinned version, whether it accepts an OpenAI-compatible base URL pointed at llama-server, the call sequence it exposes after one probe, and whether the prompt the engine received can be read (server-side prompt logging or the framework's own trace) to compute overhead.
- Stop when: every roster model has a parseable, failing-model or failing-template verdict on the probe set, and every candidate framework has a verdict on the three questions, or a dependency (an unpinned build, a framework that cannot be installed under the lockfile) stops the next check.
