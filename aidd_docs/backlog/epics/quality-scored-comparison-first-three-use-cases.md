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

- Includes: task suites for classification, translation, and text/email rewriting; deterministic scoring where possible; LLM-as-judge scoring by the judge pair, Z.ai's GLM and DeepSeek, each called through its own direct API (PRD Methodology 11), with inter-judge agreement for judged outputs; Mistral and Google are cloud subjects here and never judges; a quality-scores table kept separate from the existing runtime table; the model roster spanning both MoE and tiny dense candidates for these three use cases.
- Excludes: document comparison, code generation, agentic planning, agentic tool calling, web research, RAG answer generation, and multilingual coverage as its own use case — all deferred to later epics.
- Excludes: CI/CD hardening (dependency/security scanning, SBOM, release automation), the API-key-gated cross-machine demo, and Docker packaging. These are explicitly **not** part of this epic — they are engineering-credibility infrastructure, not a product outcome about model comparison. They are scoped into a separate, parallel epic (see Dependencies below) that can run alongside this one since neither blocks the other's build, but this epic's "credible artifact" success evidence (PRD AC) is not fully achievable until that epic also ships.

## Success Evidence

A client's engineer can rerun the classification/translation/rewriting suites against the shipped model roster, get the same quality scores back, and see inter-judge agreement reported for every judged result — closing the "quality" half of the PRD's defensibility bet (runtime half already shipped). Once `done`, record here whether reproduction actually held and whether any specific model's score was challenged in a real client session.

## Progress (2026-09-06)

Three of this epic's four stories are `done`: deterministic classification scoring, translation scoring, and the dense-vs-MoE comparison (the roster now holds the MoE flagship plus a Qwen3 0.6B/1.7B/4B dense ladder, and `aidd_docs/results/README.md` publishes a side-by-side table per use case).

The epic stays open, and deliberately: its only remaining scope is `judge-scoring-with-inter-judge-agreement-proves-judged-machinery`, which carries **both** the rewriting task suite (the third of the three use cases named above) and the two-independent-judge machinery. Until it lands, the rewriting use case has no suite and no rows — the divergence every story delivered so far has recorded as its D1, and the reason the published comparison covers two use cases rather than three. No fabricated rewriting row stands in for it anywhere.

One finding to carry into that story: the dense rows published so far measure instruction-following on a raw `/completion` endpoint, because the local quality path applies no chat template. It is filed in `aidd_docs/backlog/tech-debt.md`, and it is a decision the judged path will have to take a position on before it scores open-ended output.

## Progress (2026-10-01)

The owner answered Q50 to Q58 of `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`, all with the recommended option (a). Order 2 (`judge-scoring-with-inter-judge-agreement-proves-judged-machinery`) is rewritten in place under the amended judge pair (Q50) and is `proposed` with `depends_on` on the judge epic's per-call-fields and pair-retirement stories (Q51); it keeps the PRD's two branches, two judges with agreement or one judge flagged single-judge (Q52); the per-judge-call fields and judge cost come through the row contract rather than its own bullets (Q53); its rewriting batch is published under the pair alone and does not wait for a calibration figure (Q54); it owns its versioned 1-5 rubric, its contested threshold and judge prompts in the item's language (Q55); and it is born compliant with Methodology 2 to 5 as a data-defined suite (Q57). Under Q56, order 2's outcome is restated: it no longer proves the judged machinery, which is the judged probe's job in the judge epic and on which order 2 now depends; its value is the third use case's quality score, a consultant comparing local and cloud rewriting quality under two independent judges. Its file name is kept. Under Q58, this epic's Boundaries and Dependencies rows no longer name Mistral and Google as judges or assume free-tier judge access. The chat-template finding in the 2026-09-06 note is closed by the `done` defect `local-subject-prompts-are-never-chat-templated`.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| Engineering-credibility infrastructure (CI/CD scanning, Docker, API-key demo auth) | dependency | Separate, parallel epic, not this one; PRD's full "credible artifact" success needs both epics done, but neither blocks the other's start. |
| Paid direct API access to the judge pair (Z.ai for GLM, DeepSeek) and to the calibration judge's provider | dependency | PRD Dependencies: a small judging budget, on the order of ten dollars per campaign at catalogue rates, is accepted. Access is settled by the judge epic's spikes (`any-open-ended-output-carries-two-judges-or-an-honest-flag`) and unverified until the first live call. Mistral and Google keep their keys as cloud subjects only. |
| Exact dense/MoE model roster per use case | decision | Deferred to implementation planning, not fixed at epic level — this epic's job is to produce that comparison, not pre-select the winner. |
| Whether deterministic scoring is sufficient for classification/translation, or judge-scoring is also needed there | assumption | Assumed deterministic-first per task-suite definition in project-brief.md:20; revisit if deterministic metrics prove too coarse during build. |
| Remaining 7 use cases' sequencing across future epics | decision | Decided in `aidd_docs/backlog/epics/no-use-case-is-silently-absent.md`, which takes all seven and orders them by dependency and value; this epic still commits only to the three named above. |

## Cancellation

n/a — not cancelled.
