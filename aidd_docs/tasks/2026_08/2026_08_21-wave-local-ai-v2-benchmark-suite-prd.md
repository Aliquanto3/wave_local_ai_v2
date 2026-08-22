# wave_local_ai_v2 Benchmark Suite

A reproducible benchmark that compares small language models running locally against cloud LLM APIs, across a shared set of task types, so a consultant can present clients with defensible on-prem-vs-cloud evidence instead of anecdote.

## Overview

Consultants advising clients on on-prem vs cloud LLM deployment currently argue from anecdote: public leaderboards score full-precision weights on cloud hardware and don't cover the quantized, CPU-offloaded MoE models now viable on consumer machines. This leaves both the consultant and the client without a credible basis for an infrastructure decision that carries real cost. The product closes that gap by producing hardware-bound runtime numbers and reproducible quality scores across identical tasks, run against both local and cloud models, presentable to a client during a pitch and defensible under a client engineer's scrutiny of the repo itself. It succeeds a working v1 (Streamlit + Ollama) and carries forward its validated carbon-accounting and model-registry patterns while extending scope to CI/CD rigor, security, and a wider task/model surface.

## Problem Statement

- Consultants need to compare local SLMs against cloud LLMs on the client's actual use cases, not generic leaderboard tasks, and be able to defend the numbers when challenged.
- No existing benchmark corpus covers the model class this project targets (quantized MoE, ≤4B active parameters, consumer hardware) — nor tiny dense alternatives that may outperform MoE on specific use cases.
- Results must survive two different audiences at once: a client-side engineer auditing methodology and reproducibility, and a client decision-maker judging the comparison at a glance — the latter through a presentable results surface, not the repo.
- Because this evidence is meant to run on a client's own machine or be handed to a client for their own reproduction, it must work unmodified when the project is duplicated on another machine, must not expose that machine or its data when accessed from a second machine during a demo, and must not send the client's own material to a third party as a side effect of being run.
- Choice of web-search tool and dense-vs-MoE model is itself use-case-dependent and unresolved industry-wide — the benchmark needs to answer "which tool/model for which use case," not assume one upfront.

## Goals

- A client or their engineer can independently reproduce the quality scores and verify the runtime numbers against the disclosed hardware fiche, with an explicit verdict of reproduced or not reproduced rather than an eyeball comparison.
- Coverage spans the full set of use cases: classification, translation, document comparison, email/text rewriting, code generation, agentic planning, agentic tool calling, web research, and RAG answer generation — with multilingual handling (at minimum English, French, German) carried as a language dimension of the classification, translation and rewriting suites rather than as a separate use case.
- For each use case, the benchmark surfaces whichever model family performs best — MoE or dense — including tiny dense candidates (e.g. Granite 4 350M/1B, Qwen3 0.6B/1.7B/4B, Phi-4-mini, SmolLM3, Llama 3.2) alongside the MoE flagships, not a single architecture assumed up front.
- For the agentic web-research use case, multiple web-search tools (e.g. a self-hosted option and at least one hosted API) are implemented and compared, so the benchmark also identifies which search tool performs best per model/use case rather than committing to one tool by assumption.
- Runtime metrics (TTFT, tokens/s, RAM/VRAM, energy, carbon, cost) and quality scores are both captured, kept separable, and each is defensible on its own terms.
- Judged (open-ended) scores carry inter-judge agreement between two cloud LLM judges of different model families, and no judge ever scores output produced by its own family.
- Energy/carbon figures are reported at a high, strategy-level headline (a single defensible number per run) always carrying the label that says whether it is an estimate or a measurement, while the detailed calculation and methodology remain available in the repo so a specific figure can be justified if challenged.
- Results are readable during a client pitch from a browser rather than a terminal: a read-only service exposes the runs and their tables, and a dashboard presents them at the resolution a decision-maker reads.
- The project runs and reproduces its results after being cloned onto a new machine, following only the setup documented in the repo, including via a provided container image.
- The repo itself demonstrates engineering quality (tests, measured coverage, reproducibility, pinned dependencies, automated security/dependency checks) as part of the evidence a client-side developer evaluates.
- A demo can be run from one of the consultant's machines and queried from a second machine, with access restricted via an API key.
- Changes to the benchmark are validated automatically before being considered shippable, and released versions are identified by a tag and an accompanying changelog entry.

## Benchmark Methodology

The rules below are what makes a published number defensible; each is stated so it can be checked and failed. The thresholds they carry — 20 items per suite, N≥5 runtime repetitions, a 10% runtime tolerance, a 25% minimum share per language, 80% line coverage — are initial values, revisable by a later decision; they exist so each rule is falsifiable, not because the values are themselves evidence.

1. **Sampling determinism.** Every generated row records the seed, temperature, top_p, top_k and the exact model id used; re-running with those values reproduces the same score.
2. **Prompt parity and versioning.** Every row stores the final prompt string as rendered for that provider (after llama.cpp jinja templating or the cloud provider's chat templating), the prompt-template version id, the suite id, and a content hash of the suite's prompt set. Editing any prompt bumps the suite version.
3. **Generation caps.** Maximum output tokens, stop sequences and context length belong to the suite definition, are identical across every model compared on an item, and are recorded per row.
4. **Suite size and language mix.** A suite holds at least 20 items; a suite below that publishes its score marked indicative. Each item in the classification, translation and rewriting suites is tagged with its language, and each of EN, FR and DE covers at least 25% of that suite's items.
5. **Item provenance.** Each item declares its provenance (hand-written, licensed, or public), and any public-origin item is marked contamination-risk in the published table.
6. **Runtime repetition and spread.** A published runtime metric is the median of at least 5 repetitions; the row records N, the mean, the standard deviation, and keeps the raw repetitions retrievable.
7. **Machine state.** Every runtime run records CPU package temperature and system load at start; a metric whose repetition spread exceeds 10% is flagged unreliable.
8. **Reproduction verdict.** Quality is reproduced when two runs of the same model, prompt version and seed produce identical per-item predicted labels or scores. Runtime is reproduced when the re-run's median falls within 10% of the reference row's median on the same hardware fiche. Otherwise the row is flagged not reproduced, with the thermal and load hint of both runs recorded.
9. **Failed generation.** An item whose generation is empty, truncated at the context limit, or unparseable scores 0, stays in the denominator, and records its failure reason; failures are never silently dropped from a comparison.
10. **Judge protocol.** A judged row records each judge's dated model id, the judge prompt id and its content hash, and the rubric version. The judge prompt is issued in the item's own language. The agreement statistic is named per suite: Cohen's kappa for a categorical rubric, absolute score delta for a numeric one.
11. **Judge independence.** A judge never scores output from its own model family. A local SLM's output is scored by both judges and carries an agreement figure. A cloud subject's output is scored by the other-family judge only, carries no agreement figure, and is flagged single-judge.
12. **Cloud model pinning.** A cloud row records the provider's dated model id — never a floating alias — and the API version; a run refuses to start when that id is absent from the provider's live model list.
13. **Model roster.** Every roster model has an entry in a versioned roster file pinning its repo revision, file name, quant, checksum and its own server flag set (a dense model takes no MoE-offload flags), and every row's fiche cites that entry.
14. **Hardware fiche integrity.** A fiche carries CPU, RAM, GPU, driver, llama.cpp build, quant and flags, and is identified by a SHA-256 content hash; editing a fiche invalidates the rows that reference it.
15. **Energy and carbon.** Every row carries energy_kwh, emissions_kg, the emission factor and region used to convert between them, and energy_method stating whether the figure is an estimate or a measurement. A cloud row carries a Scope-3 estimate with the id of the formula that produced it.
16. **Cost.** A cloud row carries tokens in and out plus an estimated cost from the provider's list price at run time; a local row carries an energy cost derived from a configurable kWh price. Cost is reported, never optimised.
17. **Web-research archival.** Every search response is archived with its row so the score can be recomputed offline; a live re-run is labelled non-reproducible and is never compared against a published number.
18. **Web-research suite shape.** The web-research suite holds at least 20 queries with dated reference answers, scored by the judges against the retrieved sources, with the search tool used recorded per row.
19. **Run provenance.** Every row records its run id, capture timestamp, and the release version and commit sha of the code that produced it.

## Non-Goals

- Fine-tuning or training models.
- Multi-GPU or datacenter-scale model serving.
- Production multi-tenant hosting or public internet exposure.
- Mobile deployment.
- Tracking deal outcomes or business KPIs.
- Authentication/authorization beyond the API-key-gated two-machine demo scenario (no multi-tenant user accounts, no public-internet threat model).
- Sending client-provided documents or prompts to a cloud provider, as benchmark subject or as judge. Only the repo's own suite items ever leave the machine in this release; any future opt-in must be explicit per run.
- Optimising or minimising cost, energy or carbon. The benchmark reports them; acting on them is the client's decision.
- Selecting one "winning" web-search tool or dense model up front — the comparison itself is the deliverable, not a pre-committed choice.

## User Stories

- As a consultant, I want to run the same task suite against local SLMs and cloud LLMs, so that I can show a client an apples-to-apples comparison.
- As a consultant, I want each run tagged with a signed hardware fiche, so that runtime numbers can't be challenged as machine-dependent noise without disclosure.
- As a consultant, I want quality scores kept separate from runtime scores, so that a client can't dismiss a good quality score because of hardware, or vice versa.
- As a consultant, I want open-ended task scores backed by two independent LLM judges with agreement reported, so that a client's engineer can't dismiss a score as one model's opinion.
- As a consultant, I want tiny dense models compared alongside MoE models on each use case, so that I can recommend the actually-best model per client need instead of a single architecture by default.
- As a consultant, I want several web-search tools compared for the web-research use case, so that I can recommend the best-performing one instead of picking one arbitrarily.
- As a consultant, I want to present the results from a browser rather than a terminal, so that a pitch doesn't depend on me running commands in front of a client.
- As a client decision-maker, I want to see the comparison as tables and a single headline energy figure, so that I can judge the on-prem-vs-cloud question at a glance without reading the repo.
- As a client-side developer, I want to read the repo and its test suite, so that I can independently judge the engineering quality behind the numbers.
- As a client-side developer, I want to clone the repo (or pull its container image) and reproduce the published results on my own machine, so that I can verify the claims rather than take them on trust.
- As a client-side developer, I want to reproduce the local half of a run without holding cloud provider credentials, so that verification doesn't require me to buy API access first.
- As a consultant, I want to query the benchmark running on one of my machines from another of my machines during a live demo, using an API key, so that I can show a realistic remote-access scenario without exposing it to the wider network.
- As a consultant, I want a high-level carbon/energy number I can show a client, with the full calculation available if they push back on it, so that I don't have to over-explain methodology in the pitch itself but can defend it if asked.
- As a consultant, I want to know what a client's own material costs me in exposure, so that running the benchmark on their premises never becomes a data-transfer question mid-engagement.
- As a consultant, I want every code change to pass automated checks, including dependency and security scans, before I rely on it, so that a broken or vulnerable benchmark never reaches a client demo.
- As a consultant, I want releases tagged with a changelog, so that I can tell a client exactly which version produced the numbers they're looking at.

## Acceptance Criteria

- Given a supported task suite, running it against a local model and a cloud model produces one quality score and one runtime record per model, from the same suite items rendered per provider under Methodology 2 and 3.
- Given a runtime record, it always references a hardware fiche (CPU, RAM, GPU, driver, build, quant, flags) for that run, identified by the fiche's content hash.
- Given an open-ended task result from a local model, it is never presented without both judges' scores and their agreement level; given one from a cloud model, it carries the other-family judge's score only and is visibly flagged single-judge.
- Given a judged item whose two judges disagree beyond the suite's stated threshold, the item is published as contested and excluded from that suite's headline score.
- Given no client-provided document or prompt in a suite, no request leaving the machine ever contains one, and every row records whether its prompt left the machine.
- Given the full use-case list, each of the nine task use cases (classification, translation, document comparison, text rewriting, code generation, agentic planning, agentic tool calling, web research, RAG answer generation) has at least one task suite exercising it, or is marked out of scope for this release as a labelled empty row in the published results table; multilingual EN/FR/DE coverage is satisfied as a language dimension of the classification, translation and rewriting suites per Methodology 4.
- Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side, and each of them cites its entry in the versioned roster file.
- Given the web-research use case, at least two distinct web-search tools are benchmarked against the same query set, with results attributable to which tool was used and every search response archived with its row.
- Given a web-search call that returns no results, an error, or a rate limit, the row records that tool outcome, and the item is excluded from the model's score while remaining visible in the tool comparison.
- Given a carbon/energy figure shown to a client, a single headline number in kg CO2e is displayed together with its energy_method label, and the underlying calculation (method, inputs, region and emission factor, formula/tool version) is retrievable from the same run's record.
- Given a cloud model row, it carries a Scope-3 energy and carbon estimate with its formula id and an estimated cost from the provider's list price at run time; given a local model row, it carries an energy cost derived from the configured kWh price.
- Given a published run, a re-run of it returns an explicit verdict of reproduced or not reproduced per Methodology 8, rather than two numbers left for the reader to compare.
- Given the repo cloned fresh onto a different machine, or its container image pulled, the documented setup steps produce a working benchmark run without undocumented manual fixes.
- Given a machine below the declared minimum for a roster model, setup fails and names the missing resource, and no runtime row is produced rather than a silently degraded one.
- Given the published container image, it ships no model weights, and its documented first run downloads the pinned GGUF by revision with a checksum verification.
- Given a reproduction attempt without cloud provider credentials, the local half of every suite runs to completion and the cloud rows are reported as skipped, not failed.
- Given a cloud provider failure mid-suite (quota, rate limit, or retired model), every row already produced is persisted and the run is marked partial, naming the failing provider and item.
- Given a code change, an automated check suite (tests with line coverage, lint, type-check, dependency/security scan) runs on the head commit and the platform blocks the merge until it reports success; the suite fails when line coverage is below 80%.
- Given a demo session, the service binds only to a configured address over TLS, a request carrying a valid API key from a second machine is answered, a request without a valid key is rejected, and no request from outside loopback is served without a key; the key is read from the environment, never written to the repo or logs, and the service refuses to start without one.
- Given a demo or a pitch, a read-only results service exposes the list of runs, the quality table, the runtime table with its fiche, and the per-run energy detail, and a dashboard presents those four views without the viewer touching a terminal.
- Given a release, it is marked by a version tag and has a corresponding changelog entry describing what changed, and every result row records the release version and commit sha that produced it.
- Given a benchmark result shown to a client or their engineer, the consultant logs in a tracked file whether it was challenged, dismissed, or accepted, with the challenger's role, the evidence offered, and the acceptance criterion disputed; a challenge counts as sustained when it is not resolved by evidence within that session. After at least 3 such logged sessions with no sustained challenge to fiche disclosure, table separation, or judge agreement, the artifact is considered validated as credible for that release; elapsed time alone never validates it, and any sustained challenge is logged as a follow-up item rather than silently accepted.

## Dependencies

- Continued free-tier access to at least two independent cloud LLM providers for judging and cloud-model comparison.
- Continued free or low-cost access to at least two web-search tools/APIs for the web-research use case comparison.
- Availability of local hardware representative of the target consumer-hardware class (CPU offload, ≤20GB@Q4).
- Obtainability of the roster's model weights and of the local inference runtime: each GGUF named by its source repository and revision with a checksum, and the llama.cpp build named by tag with its download source. Without both, no run starts and no reproduction is possible.
- Licence terms of each roster model permitting the client-side use the reproduction story asks for; a roster entry records the licence and whether client-side commercial use is permitted.
- GitHub (or equivalent) as the hosting and distribution point clients and their engineers use to access the repo, and as the CI/CD execution environment.
- CodeCarbon's offline-mode measurement approach (physical, Scope 2) for local runs, requiring a declared region and emission factor, paired with a calibrated formula-based estimate (Scope 3, covering datacenter overhead and hardware amortization) for cloud/API models — both patterns already validated in the v1 predecessor and carried forward.
- A container registry (or equivalent) to distribute the release image referenced in the reproducibility acceptance criteria.

## Open Questions

- Whether the Windows/NVML energy-estimate caveat needs specific client-facing disclosure wording beyond the mandatory energy_method label, or the high-level/detailed-calc split above is sufficient disclosure on its own.
- Whether a third cloud provider family is added so that cloud subjects regain a two-judge agreement figure instead of the single-judge flag.
- Which specific web-search tools are selected as the initial comparison set (candidates identified: a self-hosted option and one or more hosted APIs) — a technical decision deferred out of this PRD, but the number and identity of tools affects how "web research" acceptance criteria get validated.
- Which specific dense and MoE models make the initial roster per use case — deferred as a technical/model-selection decision, not fixed here.
- Exact scope and enforcement level of the automated security/dependency scanning (which findings block a merge vs. only get logged) — v1 ran these as non-blocking; whether v2 makes any of them blocking is undecided.
- Whether the Methodology's initial thresholds (20 items, N≥5, 10%, 25% per language, 80% coverage) survive the first full-roster run, or need to move once real spread and real suite sizes are known.
- Whether "credible artifact" validation (per the acceptance criterion above) needs a firmer, product-wide check-in cadence beyond the per-session log.
