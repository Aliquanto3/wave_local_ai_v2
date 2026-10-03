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
**I want** the full two-engine by four-variant campaign run on the declared reference machine (the laptop, in its `gpu` mode) across the roster and the suites that exist, every declared cell run, and a dated statement per variant and task family of whether it helped, hurt or was indistinguishable
**So that** the benchmark's own research question is answered with a test or an honest observation behind every claim, and the founding llama.cpp decision is evidenced rather than asserted

Maps to: PRD AC "Given a campaign, every row records its engine ... and its prompt variant, and the campaign declares at most two engines and at most four variants"; PRD AC "Given a published quality score, it is shown with a bootstrap confidence interval; given a claim that two models, engines or prompt variants differ, it is shown with a paired ... test..."; PRD Open Question on prompt compression; PRD User Story "As a consultant, I want the inference engine, the agentic harness and the prompt variant compared as dimensions..."; Methodology 6, 19, 22, 24; epic decisions "Campaign shape", "A negative result is a result"; epic Success Evidence (the campaign completes, and the statement).

Needs: real local model runs on the reference machine with both engines and the compressor installed, and an operator for the quiet thermal window. No API key.

Blocked: only through `depends_on`; nothing blocks this story of its own. Not `done` among them: `aidd_docs/backlog/stories/the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md` (order 8, `proposed`), blocked by the live generations of spike `which-constrained-decoding-mechanism-does-ollama-expose.md` and, through order 7, by the live session of spike `does-ollama-expose-the-prompt-it-finally-rendered.md`, owner question Q117 on order 7's thinking-switch bullet, and through order 6 the live session of spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`; and `aidd_docs/backlog/stories/the-input-compression-variant-records-its-compressor-as-a-step-of-its-own.md` (order 9, `proposed`), blocked by the live CPU measurement of spike `which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement.md` and by Q115. Its three other `depends_on` are `done`. The `ready` stories it reaches through them (`a-campaign-is-declared-as-data-and-an-empty-cell-fails-it.md` through orders 6 and 9, `the-terse-output-variant-runs-every-item-and-meets-baseline-in-a-paired-test.md` through order 9, `the-constrained-output-variant-runs-under-a-llama-cpp-grammar-and-names-its-mechanism.md` through order 8) block no refinement, but must be `done` before the campaign runs.

Current state (verified on `main` at `c68b23e`, 2026-10-03):

- No campaign declaration exists: `quality_cli.PROMPT_VARIANT_ID` and `wave_local_ai_v2.PROMPT_VARIANT_ID` are fixed to `baseline`, each comment naming the declaration as a later story; `prompt_variants.REGISTERED_VARIANTS` holds `baseline` only; `aidd_docs/roster/engines.json` holds `llama.cpp` only.
- The suites that exist are `suite_data/classification-support-routing.json` and `suite_data/translation-business-short-form.json`, both declaring `thinking_policy: disabled`.
- `comparison.py` produces paired tests, observations and refusals inside Holm-adjusted comparison families, along `model` and `prompt_variant` only (`comparison.DIMENSIONS`).
- The published bundle's rows are schema `"7"` (`tests/test_reference_bundle.py` `PUBLISHED_BUNDLE_SCHEMA_VERSION`) against code `"22"`; earlier files are kept as `runtime-reference.schema-1.jsonl` and `quality-reference.schema-1.jsonl` in `aidd_docs/results/`.
- Spike desk finding (`can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`, launch arguments read in source): Ollama passes `-ngl` from `num_gpu` and no `--n-cpu-moe`, so the flagship's declared offload (`server_flags.n_cpu_moe` 37 in `aidd_docs/roster/models.json`) has no Ollama option; its Ollama cells are run, refused or dropped under acceptance bullet 3 with that recorded.

## Acceptance

- The reference machine is the laptop (RTX 3060 Laptop, 6 GB VRAM, about 5.1 GB allocatable, per `context_input/hardware.md`) in its `gpu` mode, as Q22 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles.
- The campaign declaration is committed: llama.cpp and Ollama, the four variants, the roster entries runnable on the reference machine, the suites that exist, and the reference machine with its mode. A roster entry the machine refuses is listed as refused under the machine epic's discipline, not dropped silently.
- Every declared cell is run, refused with its reason, or dropped with its reason; order 3's completeness command passes and its listing is published.
- For each non-baseline variant against `baseline`, per task family, per engine: the quality difference arrives as a comparison record with its interval, inside a comparison family with Holm-adjusted p-values; the token and TTFT differences arrive as paired tests over order 10's per-item values, the TTFT labelled as a per-item measurement distinct from the Methodology 6 figure; the energy difference, from per-batch energy, is published as a labelled observation and never as a paired test (Q24 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`). Each is a test result or an explicitly labelled observation.
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
