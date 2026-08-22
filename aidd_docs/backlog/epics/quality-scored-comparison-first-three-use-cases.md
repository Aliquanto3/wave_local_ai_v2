---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
---

# Epic: Quality-scored local-vs-cloud comparison for the first three use cases

Given identical classification, translation, and text-rewriting task suites, a consultant gets separated, reproducible quality scores and hardware-bound runtime metrics for local SLMs (MoE and tiny dense) against cloud LLMs, with LLM-as-judge agreement reported for the judged tasks.

## Context and Value

Runtime instrumentation (TTFT, tokens/s, RAM/VRAM, energy/carbon, hardware fiche) is already implemented (`git log`: "CLI wiring for end-to-end runtime measurement", "runtime measurement harness plan implemented"). What's missing is the other half of the product's core bet: **quality** scores on real task suites, kept in a separate table from runtime, so a client can't dismiss a good quality score for a hardware reason or vice versa (PRD Acceptance Criteria, `2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`).

The product brief's own Open Decisions (`aidd_docs/product/wave-local-ai-v2.md:56`) flags nine-plus task suites as too wide for the earliest increment and leans toward narrowing to classification, translation, and rewriting first. This epic makes that lean an explicit decision: **increment 1 ships those three use cases only.** The remaining seven (document comparison, code generation, agentic planning, agentic tool calling, web research, RAG answer generation, multilingual EN/FR/DE as a standalone axis) are excluded from this epic and sequenced into later epics — chosen because these three are the ones with the most direct deterministic-scoring path (classification: label match; translation: reference-based metrics; rewriting: judged), letting the LLM-as-judge and inter-judge-agreement machinery get proven on the cheapest-to-validate tasks before extending to agentic/tool-calling/RAG use cases that also need new harness capability (tool-call transcripts, retrieval corpora) this epic does not build.

Model roster for this epic includes both MoE candidates and tiny dense candidates (Granite 4 350M/1B, Qwen3 0.6B/1.7B/4B, Phi-4-mini, SmolLM3, Llama 3.2) per the PRD's side-by-side goal — dense-vs-MoE selection is not decided here, it's produced as this epic's output.

## Boundaries

- Includes: task suites for classification, translation, and text/email rewriting; deterministic scoring where possible; LLM-as-judge scoring (two independent cloud judges, e.g. Mistral + Google AI) with inter-judge agreement for judged outputs; a quality-scores table kept separate from the existing runtime table; the model roster spanning both MoE and tiny dense candidates for these three use cases.
- Excludes: document comparison, code generation, agentic planning, agentic tool calling, web research, RAG answer generation, and multilingual coverage as its own use case — all deferred to later epics.
- Excludes: CI/CD hardening (dependency/security scanning, SBOM, release automation), the API-key-gated cross-machine demo, and Docker packaging. These are explicitly **not** part of this epic — they are engineering-credibility infrastructure, not a product outcome about model comparison. They are scoped into a separate, parallel epic (see Dependencies below) that can run alongside this one since neither blocks the other's build, but this epic's "credible artifact" success evidence (PRD AC) is not fully achievable until that epic also ships.

## Success Evidence

A client's engineer can rerun the classification/translation/rewriting suites against the shipped model roster, get the same quality scores back, and see inter-judge agreement reported for every judged result — closing the "quality" half of the PRD's defensibility bet (runtime half already shipped). Once `done`, record here whether reproduction actually held and whether any specific model's score was challenged in a real client session.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| Engineering-credibility infrastructure (CI/CD scanning, Docker, API-key demo auth) | dependency | Separate, parallel epic, not this one; PRD's full "credible artifact" success needs both epics done, but neither blocks the other's start. |
| Free-tier access to ≥2 independent cloud LLM judges (Mistral, Google AI Studio) | dependency | Already assumed available per project-brief; no new risk introduced by this epic. |
| Exact dense/MoE model roster per use case | decision | Deferred to implementation planning, not fixed at epic level — this epic's job is to produce that comparison, not pre-select the winner. |
| Whether deterministic scoring is sufficient for classification/translation, or judge-scoring is also needed there | assumption | Assumed deterministic-first per task-suite definition in project-brief.md:20; revisit if deterministic metrics prove too coarse during build. |
| Remaining 7 use cases' sequencing across future epics | decision | Decided in `aidd_docs/backlog/epics/no-use-case-is-silently-absent.md`, which takes all seven and orders them by dependency and value; this epic still commits only to the three named above. |

## Cancellation

n/a — not cancelled.
