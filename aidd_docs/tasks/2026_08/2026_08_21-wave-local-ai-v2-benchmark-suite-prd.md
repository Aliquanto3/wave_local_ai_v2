# wave_local_ai_v2 Benchmark Suite

A reproducible benchmark that compares small language models running locally against cloud LLM APIs, across a shared set of task types, so a consultant can present clients with defensible on-prem-vs-cloud evidence instead of anecdote.

## Overview

Consultants advising clients on on-prem vs cloud LLM deployment currently argue from anecdote: public leaderboards score full-precision weights on cloud hardware and don't cover the quantized, CPU-offloaded MoE models now viable on consumer machines. This leaves both the consultant and the client without a credible basis for an infrastructure decision that carries real cost. The product closes that gap by producing hardware-bound runtime numbers and reproducible quality scores across identical tasks, run against both local and cloud models, presentable to a client during a pitch and defensible under a client engineer's scrutiny of the repo itself. It succeeds a working v1 (Streamlit + Ollama) and carries forward its validated carbon-accounting and model-registry patterns while extending scope to CI/CD rigor, security, and a wider task/model surface.

## Problem Statement

- Consultants need to compare local SLMs against cloud LLMs on the client's actual use cases, not generic leaderboard tasks, and be able to defend the numbers when challenged.
- No existing benchmark corpus covers the model class this project targets (quantized MoE, ≤4B active parameters, consumer hardware) — nor tiny dense alternatives that may outperform MoE on specific use cases.
- Results must survive two different audiences at once: a client-side engineer auditing methodology and reproducibility, and a client decision-maker judging the comparison at a glance.
- Because this evidence is meant to run on a client's own machine or be handed to a client for their own reproduction, it must work unmodified when the project is duplicated on another machine, and must not expose that machine or its data when accessed from a second machine during a demo.
- Choice of web-search tool and dense-vs-MoE model is itself use-case-dependent and unresolved industry-wide — the benchmark needs to answer "which tool/model for which use case," not assume one upfront.

## Goals

- A client or their engineer can independently reproduce the quality scores and verify the runtime numbers against the disclosed hardware fiche.
- Coverage spans the full set of use cases: classification, translation, document comparison, email/text rewriting, code generation, agentic planning, agentic tool calling, web research, RAG answer generation, and multilingual handling (at minimum English, French, German).
- For each use case, the benchmark surfaces whichever model family performs best — MoE or dense — including tiny dense candidates (e.g. Granite 4 350M/1B, Qwen3 0.6B/1.7B/4B, Phi-4-mini, SmolLM3, Llama 3.2) alongside the MoE flagships, not a single architecture assumed up front.
- For the agentic web-research use case, multiple web-search tools (e.g. a self-hosted option and at least one hosted API) are implemented and compared, so the benchmark also identifies which search tool performs best per model/use case rather than committing to one tool by assumption.
- Runtime metrics (TTFT, tokens/s, RAM/VRAM, energy, carbon) and quality scores are both captured, kept separable, and each is defensible on its own terms.
- Judged (open-ended) scores carry inter-judge agreement between two independent cloud LLM judges.
- Energy/carbon figures are reported at a high, strategy-level headline (a single defensible number per run), while the detailed calculation and methodology remain available in the repo so a specific figure can be justified if challenged.
- The project runs and reproduces its results after being cloned onto a new machine, following only the setup documented in the repo, including via a provided container image.
- The repo itself demonstrates engineering quality (tests, reproducibility, pinned dependencies, automated security/dependency checks) as part of the evidence a client-side developer evaluates.
- A demo can be run from one of the consultant's machines and queried from a second machine, with access restricted via an API key.
- Changes to the benchmark are validated automatically before being considered shippable, and released versions are identified by a tag and an accompanying changelog entry.

## Non-Goals

- Fine-tuning or training models.
- Multi-GPU or datacenter-scale model serving.
- Production multi-tenant hosting or public internet exposure.
- Mobile deployment.
- Tracking deal outcomes or business KPIs.
- Authentication/authorization beyond the API-key-gated two-machine demo scenario (no multi-tenant user accounts, no public-internet threat model).
- Selecting one "winning" web-search tool or dense model up front — the comparison itself is the deliverable, not a pre-committed choice.

## User Stories

- As a consultant, I want to run the same task suite against local SLMs and cloud LLMs, so that I can show a client an apples-to-apples comparison.
- As a consultant, I want each run tagged with a signed hardware fiche, so that runtime numbers can't be challenged as machine-dependent noise without disclosure.
- As a consultant, I want quality scores kept separate from runtime scores, so that a client can't dismiss a good quality score because of hardware, or vice versa.
- As a consultant, I want open-ended task scores backed by two independent LLM judges with agreement reported, so that a client's engineer can't dismiss a score as one model's opinion.
- As a consultant, I want tiny dense models compared alongside MoE models on each use case, so that I can recommend the actually-best model per client need instead of a single architecture by default.
- As a consultant, I want several web-search tools compared for the web-research use case, so that I can recommend the best-performing one instead of picking one arbitrarily.
- As a client-side developer, I want to read the repo and its test suite, so that I can independently judge the engineering quality behind the numbers.
- As a client-side developer, I want to clone the repo (or pull its container image) and reproduce the published results on my own machine, so that I can verify the claims rather than take them on trust.
- As a consultant, I want to query the benchmark running on one of my machines from another of my machines during a live demo, using an API key, so that I can show a realistic remote-access scenario without exposing it to the wider network.
- As a consultant, I want a high-level carbon/energy number I can show a client, with the full calculation available if they push back on it, so that I don't have to over-explain methodology in the pitch itself but can defend it if asked.
- As a consultant, I want every code change to pass automated checks, including dependency and security scans, before I rely on it, so that a broken or vulnerable benchmark never reaches a client demo.
- As a consultant, I want releases tagged with a changelog, so that I can tell a client exactly which version produced the numbers they're looking at.

## Acceptance Criteria

- Given a supported task suite, running it against a local model and a cloud model produces one quality score and one runtime record per model, using the same prompts.
- Given a runtime record, it always references a hardware fiche (CPU, RAM, GPU, driver, build, quant, flags) for that run.
- Given an open-ended task result, it is never presented without both judges' scores and their agreement level.
- Given the full use-case list, each of the ten use cases (classification, translation, document comparison, text rewriting, code generation, agentic planning, agentic tool calling, web research, RAG answer generation, multilingual EN/FR/DE) has at least one task suite exercising it, or is explicitly and visibly marked out of scope for this release.
- Given the model roster, it includes at least one MoE candidate and at least one tiny dense candidate for a given use case, with results shown side by side.
- Given the web-research use case, at least two distinct web-search tools are benchmarked against the same query set, with results attributable to which tool was used.
- Given a carbon/energy figure shown to a client, a single headline number is displayed, and the underlying calculation (method, inputs, formula/tool version) is retrievable from the same run's record.
- Given the repo cloned fresh onto a different machine, or its container image pulled, the documented setup steps produce a working benchmark run without undocumented manual fixes.
- Given a code change, an automated check suite (tests, lint, type-check, dependency/security scan) runs and must pass before the change is considered mergeable.
- Given a demo session, a request carrying a valid API key from a second machine reaches the benchmark running on the host machine and is answered; a request without a valid key is rejected.
- Given a release, it is marked by a version tag and has a corresponding changelog entry describing what changed.
- Given a benchmark result shown to a client or their engineer, the consultant can log whether it was challenged, dismissed, or accepted; after 3 such sessions or 90 days (whichever comes first) with no sustained challenge to fiche disclosure, table separation, or judge agreement, the artifact is considered validated as credible for that release; any sustained challenge is logged as a follow-up item rather than silently accepted.

## Dependencies

- Continued free-tier access to at least two independent cloud LLM providers for judging and cloud-model comparison.
- Continued free or low-cost access to at least two web-search tools/APIs for the web-research use case comparison.
- Availability of local hardware representative of the target consumer-hardware class (CPU offload, ≤20GB@Q4).
- GitHub (or equivalent) as the hosting and distribution point clients and their engineers use to access the repo, and as the CI/CD execution environment.
- CodeCarbon's offline-mode measurement approach (physical, Scope 2) for local runs, paired with a calibrated formula-based estimate (Scope 3, covering datacenter overhead and hardware amortization) for cloud/API models — both patterns already validated in the v1 predecessor and carried forward.
- A container registry (or equivalent) to distribute the release image referenced in the reproducibility acceptance criteria.

## Open Questions

- Whether the Windows/NVML energy-estimate caveat needs specific client-facing disclosure wording, or the high-level/detailed-calc split above is sufficient disclosure on its own.
- Which specific web-search tools are selected as the initial comparison set (candidates identified: a self-hosted option and one or more hosted APIs) — a technical decision deferred out of this PRD, but the number and identity of tools affects how "web research" acceptance criteria get validated.
- Which specific dense and MoE models make the initial roster per use case — deferred as a technical/model-selection decision, not fixed here.
- Exact scope and enforcement level of the automated security/dependency scanning (which findings block a merge vs. only get logged) — v1 ran these as non-blocking; whether v2 makes any of them blocking is undecided.
- Whether "credible artifact" validation (per the acceptance criterion above) needs a firmer, product-wide check-in cadence beyond the per-session log.
