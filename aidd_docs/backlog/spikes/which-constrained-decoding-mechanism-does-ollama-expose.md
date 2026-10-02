---
type: spike
status: open
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parents:
  - aidd_docs/backlog/stories/the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md
---

# Spike: Which constrained-decoding mechanism does Ollama expose

## Question

Does Ollama accept a GBNF grammar per request, a JSON-schema-shaped output constraint as a substitute, or no output constraint at all, and does the mechanism it does accept actually restrict generated tokens on the `constrained_output` variant's declared output formats?

## Decision

Which of the epic's three pre-handled outcomes applies to the `constrained_output` x Ollama cell (order 8): the same mechanism as llama.cpp (a real comparison), a different mechanism (recorded per row and published as a comparison of two mechanisms), or none (the cell is dropped with its reason recorded).

## Bounds

- Evidence needed: against a running pinned Ollama instance (the one spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol` installs), for `qwen3-0.6b-q8`: the request parameter tried for each candidate mechanism and the captured response; whether a GBNF grammar is accepted, ignored or rejected; whether a schema-shaped constraint is accepted and how it is expressed; for each accepted mechanism, ten generations on the classification suite's output format with the constraint set and ten without, showing whether any constrained output falls outside the declared format. The variant's declared format per task family comes from order 5's registry entry; if order 5 has not landed, the classification label set is used and that substitution is recorded.
- Stop when: one mechanism is shown to restrict output to the declared format on every constrained generation, with its spelling recorded, or every candidate is shown to be absent or not enforcing, which is recorded as "none" with the attempts.
