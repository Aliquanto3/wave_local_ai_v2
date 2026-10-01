---
type: story
status: proposed
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md
  - aidd_docs/backlog/stories/the-input-compression-variant-records-its-compressor-as-a-step-of-its-own.md
  - aidd_docs/backlog/stories/each-quality-item-records-the-tokens-and-the-first-token-time-its-generation-took.md
  - aidd_docs/backlog/stories/every-quality-batch-publishes-its-interval-and-what-it-could-resolve.md
  - aidd_docs/backlog/stories/a-comparison-family-carries-its-adjusted-p-values-and-is-superseded-not-edited.md
order: 12
---

# Story: The campaign answers whether each variant helps or hurts a small model

**As** the consultant recommending a stack, and the reviewer of the write-up
**I want** the full two-engine by four-variant campaign run on the declared reference machine across the roster and the suites that exist, every declared cell run, and a dated statement per variant and task family of whether it helped, hurt or was indistinguishable
**So that** the benchmark's own research question is answered with a test or an honest observation behind every claim, and the founding llama.cpp decision is evidenced rather than asserted

Maps to: PRD AC "Given a campaign, every row records its engine ... and its prompt variant, and the campaign declares at most two engines and at most four variants"; PRD AC "Given a published quality score, it is shown with a bootstrap confidence interval; given a claim that two models, engines or prompt variants differ, it is shown with a paired ... test..."; PRD Open Question on prompt compression; PRD User Story "As a consultant, I want the inference engine, the agentic harness and the prompt variant compared as dimensions..."; Methodology 6, 19, 22, 24; epic decisions "Campaign shape", "A negative result is a result"; epic Success Evidence (the campaign completes, and the statement).

Needs: real local model runs on the reference machine with both engines and the compressor installed, and an operator for the quiet thermal window. No API key.

Blocked: Q22 (which machine is the reference machine); and, through orders 8, 9 and 10, the three Ollama spikes, the compressor spike, Q23 and Q24.

## Acceptance

- The campaign declaration is committed: llama.cpp and Ollama, the four variants, the roster entries runnable on the reference machine, the suites that exist, and the reference machine with its mode. A roster entry the machine refuses is listed as refused under the machine epic's discipline, not dropped silently.
- Every declared cell is run, refused with its reason, or dropped with its reason; order 3's completeness command passes and its listing is published.
- For each non-baseline variant against `baseline`, per task family, per engine: the quality difference arrives as a comparison record with its interval, inside a comparison family with Holm-adjusted p-values; the token and TTFT differences arrive as order 10 measures them; the energy difference is stated as order 10 says it may be. Each is a test result or an explicitly labelled observation.
- The engine comparison per variant is published under the same rules, each cross-engine quality cell gated by order 7's parity record and order 6's `artifact_parity`.
- A dated statement in `aidd_docs/results/README.md` says, for each variant and each task family reached, whether it helped, hurt or was indistinguishable on quality, TTFT, tokens and energy, citing the record behind each claim; names the machine every claim holds for; names the task families it could not reach (the agentic and RAG families); states whether the roughly 8.5% token figure from the coding-agent report transferred; states whether Ollama exposed enough rendering and constraint machinery for a fair comparison or forced cells to be dropped; and states whether the founding llama.cpp decision held on the numbers. A finding of no distinguishable difference is published as the answer.
- The campaign's rows enter the reference bundle under this epic's final schema; superseded bundle files are renamed with the schema version that produced them and kept, never edited or back-filled.

## Code it changes

- None expected beyond fixes the run uncovers; the campaign declaration, the bundle and the results README.

## Tests it needs

- None new beyond what the regenerated bundle makes `tests/test_reference_bundle.py` assert; a regression the run uncovers gets its test.

## Evidence it publishes

- The campaign declaration, the completeness listing, the comparison and family records, and the dated statement.

## What the operator runs by hand

- The quiet thermal window on the reference machine, confirmed before the counted runs start; the agent does not decide the machine is idle.

## Cancellation

n/a: not cancelled.
