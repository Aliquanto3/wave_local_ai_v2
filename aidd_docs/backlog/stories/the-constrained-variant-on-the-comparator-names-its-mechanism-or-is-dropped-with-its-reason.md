---
type: story
status: proposed
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/the-constrained-output-variant-runs-under-a-llama-cpp-grammar-and-names-its-mechanism.md
  - aidd_docs/backlog/stories/ollama-quality-rows-pass-a-prompt-parity-gate-or-publish-as-observations.md
order: 8
---

# Story: The constrained variant on the comparator names its mechanism or is dropped with its reason

**As** an academic or technical reviewer reading a cross-engine constrained-output result
**I want** the `constrained_output` x Ollama cell to run under the mechanism Ollama actually supports and name it, or to be dropped with its reason recorded
**So that** a cross-engine constrained comparison is read as a comparison of two mechanisms where that is what it is, and a missing cell is an explained absence rather than an empty one

Maps to: Methodology 22 ("every declared cell is actually run rather than left empty"); epic Boundaries "the constrained variant's mechanism recorded per engine"; epic Unknowns "Whether Ollama exposes grammar-constrained decoding, a schema-shaped substitute, or nothing" (three outcomes, all handled).

Needs: a real local model run on the reference machine with the pinned Ollama build installed. No API key.

Blocked: spike `aidd_docs/backlog/spikes/which-constrained-decoding-mechanism-does-ollama-expose.md`.

## Acceptance

- The Ollama engine entry declares the constraint mechanisms it supports, as the spike found them: the same grammar mechanism as llama.cpp, a different one, or none.
- Same mechanism: the cell runs under order 5's per-family grammar, each row recording the mechanism and the grammar hash, and a cross-engine comparison of the variant is published under the usual paired-test rules.
- Different mechanism: the variant's definition gains, per family, the equivalent constraint in that mechanism, versioned under order 2's rule; each row records the mechanism applied; a cross-engine comparison of the variant names both mechanisms on its record and is published as a comparison of mechanisms, never as an engine-only difference.
- None: the campaign declares the cell dropped, with the reason and the spike as its evidence, and order 3's completeness check lists it as dropped rather than empty.

## Code it changes

- The Ollama registry entry's supported mechanisms; the variant definition's per-mechanism constraint if needed; the Ollama request path.

## Tests it needs

- For the outcome the spike selects: the mechanism recorded per row, or the dropped cell listed with its reason and not failing completeness.
- A cross-engine constrained comparison with two different mechanisms names both.

## Evidence it publishes

- The constrained cell's Ollama result for the same roster entry and suite as order 5, or its recorded drop, in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
