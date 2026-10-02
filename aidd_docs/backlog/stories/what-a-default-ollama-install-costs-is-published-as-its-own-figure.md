---
type: story
status: proposed
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/ollama-runtime-rows-stand-beside-llama-cpp-rows-on-the-same-artifact.md
order: 11
---

# Story: What a default Ollama install costs is published as its own figure

**As** the consultant whose client will run Ollama as installed
**I want** one named roster model, `qwen3-0.6b-q8`, measured under a default Ollama install, under the full runtime protocol, with the quant and context Ollama actually chose recorded beside the roster's, and published as its own figure
**So that** the difference between "the engine" and "the engine as installed" is readable rather than argued, without ever confounding the engine comparison

Maps to: Methodology 6, 15, 20, 22; epic Boundaries "the defaults side-run, on one named model, published as its own figure"; epic decision "Ollama's own defaults"; epic success check 4.

Needs: a real local model run on the reference machine with Ollama installed (operator), and a network download of the model from the Ollama library. No API key.

Blocked: spike `aidd_docs/backlog/spikes/can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md` (what a default install chooses and reports), through order 6.

## Acceptance

- The side-run's model is `qwen3-0.6b-q8` (roster quant `Q8_0`), the machine epic's proving model, as Q21 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles. It is pulled from the Ollama library under its default tag and run with no model definition overrides, under the full runtime protocol, and its rows record `artifact_parity: engine_supplied` with the file, quant and effective context Ollama chose, beside the roster entry's quant, checksum and declared context. A quant Ollama chose other than `Q8_0` is stated on the figure as a difference, not hidden.
- The figure states that it says nothing about Ollama's MoE offload defaults, since its model is a small dense entry.
- The side-run's rows are marked as the defaults side-run. They belong to no campaign cell, do not count toward the two-engine cap, and the completeness check ignores them.
- The analysis command refuses to use a side-run row as either side of a paired engine comparison, naming the side-run marker; the figure sets it beside the reference engine's row for the same roster entry as an observation.
- The figure is published as its own dated section and table, "what the defaults cost", naming the machine and the reference row it is set beside.

## Code it changes

- A side-run marker on the runtime path and in the row contract; the comparison command's refusal; the figure's table in the results README.

## Tests it needs

- A side-run row is refused as a comparison side; the completeness check ignores it; `engine_supplied` details are required on it.

## Evidence it publishes

- The "what the defaults cost" section in `aidd_docs/results/README.md` (epic success check 4).

## Cancellation

n/a: not cancelled.
