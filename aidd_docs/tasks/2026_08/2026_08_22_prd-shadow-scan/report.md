---
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
generated_at: 2026-08-22
---

# Shadow Areas Report

Source: `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`
Generated: `2026-08-22`

Total gaps: 48 | Blocker: 13 | Major: 32 | Minor: 3

Path note: the skill's default naming rule would write this next to the source as
`2026_08_21-wave-local-ai-v2-benchmark-suite-prd-shadow-report.md`. The caller's explicit path
wins; the source file is unmodified either way.

Every gap below names the PRD section it belongs in and, where the fix is a testable condition,
a one-line proposed acceptance criterion. Proposed thresholds (20 items, N>=5, 10%, 80%) are
starting values drawn from `context_input/baseline_qwen36.md` and the v1 predecessor, not
findings; they exist so the AC is falsifiable, and the author should overwrite them deliberately.

---

## Suspect verdicts

| # | Suspect | Verdict | Gaps |
| --- | --- | --- | --- |
| 1 | No goal/story/AC for the API or front end | **Confirmed** | 1.1, 4.1, 6.13 |
| 2 | No measurable benchmark-rigor policy | **Confirmed**, and wider than listed: contamination, prompt templating, generation caps and machine state are also unpinned | 1.5, 1.6, 2.4, 3.4, 6.1, 6.2, 6.7, 6.8, 6.9, 6.10, 6.11 |
| 3 | Carbon conflated with energy | **Confirmed** | 2.3, 6.3, 6.5, 1.7 |
| 4 | Multilingual undefined | **Confirmed**; also no per-language scoring rule | 2.2, 6.16 |
| 5 | Web-search comparison underspecified | **Partly refuted**: tool identity is deferred openly in Open Questions, so it is a known-open decision, not a blind spot. The query set, the scoring rule and the reproducibility collision are genuine blind spots | 6.4, 1.4, 5.4 |
| 6 | Roster AC has no model-addition or per-model-flag statement | **Confirmed**, and the AC is weaker than the goal it implements | 2.6, 6.12, 7.1, 7.2 |
| 7 | Estimate-vs-measurement labelling | **Partly refuted**: named in Open Questions, so acknowledged. The blind spot is that no AC requires the label to travel with the headline number | 6.6 |

Beyond the suspects, the three findings with the largest blast radius are 1.2 (client prompt data
leaving the machine for cloud judging, with no stated rule, in a product sold on on-prem
credibility), 1.3 (Mistral and Google are both benchmark subjects and judges, so a judge can score
its own family's output), and 2.1 ("reproduce" is the product bet and has no tolerance, so no
re-run can be declared a pass or a fail).

---

## Gaps by Category

### unstated assumption

**[blocker]** Which component serves the request that arrives from the second machine, and is it in scope for this release?
> Given a demo session, a request carrying a valid API key from a second machine reaches the benchmark running on the host machine and is answered

Section: Goals + Acceptance Criteria (an HTTP surface is assumed by this AC; the PRD never states one exists, and FastAPI/React appear only in the product brief's summary sentence).
Proposed AC: Given a running results API, `GET /runs` and `GET /runs/{run_id}` return the quality and runtime tables as JSON, and that API is the benchmark's only network surface.

**[blocker]** What client-supplied prompt content is allowed to leave the machine for cloud comparison and judging?
> Because this evidence is meant to run on a client's own machine or be handed to a client for their own reproduction

Section: Problem Statement + Non-Goals (a benchmark run on a client's use cases sends prompts to Mistral and Google; the PRD never states whether client content may leave the machine, in a product whose audience is buying on-prem).
Proposed AC: Given a suite containing client-supplied items, the run refuses to send them to any cloud provider unless the suite is explicitly flagged for cloud egress, and every row records whether its prompt left the machine.

**[blocker]** Which judge is excluded when the output being scored comes from that judge's own model family?
> Judged (open-ended) scores carry inter-judge agreement between two independent cloud LLM judges.

Section: Goals + Acceptance Criteria (Mistral and Google AI are named as both benchmark subjects and judges; "independent" is asserted, never enforced).
Proposed AC: Given a judged result whose subject model belongs to a judge's family, that judge's score is excluded from the reported agreement, or the row is marked family-conflicted and dropped from the headline score.

**[blocker]** How is a web-research score reproduced later when the live search results have changed?
> Given the web-research use case, at least two distinct web-search tools are benchmarked against the same query set

Section: Goals + Open Questions (this AC assumes a live-internet task is reproducible; it collides directly with the reproducibility goal and no reconciliation is written down).
Proposed AC: Given a web-research run, every search response is archived with its row so the score can be recomputed offline; a live re-run is labelled non-reproducible and never compared to a published number.

**[major]** Does "the same prompts" mean the same raw text, or the same text after each backend's chat template is applied?
> using the same prompts

Section: Acceptance Criteria (llama.cpp applies a jinja chat template, the cloud APIs apply their own; identical raw text is not identical model input).
Proposed AC: Given one item run against a local and a cloud model, each row records the raw prompt, the chat template id applied, and the fully rendered text sent to that backend.

**[major]** How does a task suite show that its items were not in any candidate model's training data?
> No existing benchmark corpus covers the model class this project targets

Section: Problem Statement (feeds a new Benchmark Methodology section; contamination is the first thing a client-side engineer attacks in a quality score).
Proposed AC: Given a task suite, each item declares its provenance (hand-written, licensed, public), and any public-origin item is marked contamination-risk in the published table.

**[major]** Which grid region and emission factor are used for the local run's carbon figure?
> CodeCarbon's offline-mode measurement approach (physical, Scope 2) for local runs

Section: Dependencies + Acceptance Criteria (offline mode requires a country/region input; a carbon number computed on the consultant's grid but presented for the client's is indefensible).
Proposed AC: Given a runtime row, it records the region code and gCO2e/kWh factor used, and a run in a different region recomputes the figure rather than reusing it.

### ambiguous term

**[blocker]** What difference between a re-run and the published numbers still counts as reproduced?
> A client or their engineer can independently reproduce the quality scores and verify the runtime numbers against the disclosed hardware fiche.

Section: Goals + Acceptance Criteria (this is the product bet; with no tolerance, no reproduction attempt can be declared a pass or a fail by either side).
Proposed AC: Given a re-run on the documented setup, quality scores match the published row exactly and runtime metrics fall within 10% of the published mean; anything else is reported as a mismatch with the diverging field named.

**[blocker]** Is multilingual handling one suite of its own, or a language dimension applied to every other suite?
> multilingual EN/FR/DE

Section: Goals + Acceptance Criteria (the two readings differ by roughly a factor of three in total suite work, so no epic or story for it can be sized).
Proposed AC: Given the multilingual use case, it is one suite whose items exist in EN, FR and DE, and every other suite declares its single item language explicitly.

**[major]** Is the single headline number kWh, kg CO2e, or both?
> Given a carbon/energy figure shown to a client, a single headline number is displayed

Section: Acceptance Criteria (the slash has already produced an implementation storing energy only).
Proposed AC: Given a run, the headline figure is kg CO2e for the whole run, with kWh and the emission factor shown in the drill-down.

**[major]** Which statistic expresses inter-judge agreement in a reported result?
> Given an open-ended task result, it is never presented without both judges' scores and their agreement level.

Section: Acceptance Criteria (Cohen's kappa, exact-match rate and mean absolute delta are all defensible and all different; the choice depends on whether the rubric is categorical or numeric).
Proposed AC: Given a judged item, the row carries both judges' raw scores plus Cohen's kappa for categorical rubrics or the absolute score delta for numeric ones, with the statistic named per suite.

**[major]** What does "signed" mean for a hardware fiche: a cryptographic signature, a content hash, or the consultant's attestation?
> I want each run tagged with a signed hardware fiche

Section: User Stories + Acceptance Criteria (the term appears in the story and in project memory; the AC that implements it says only "references a hardware fiche", so "signed" is unenforced).
Proposed AC: Given a runtime row, its fiche carries a SHA-256 content hash, and any later edit to the fiche invalidates the rows referencing it.

**[major]** Does the MoE-plus-dense pairing apply to every in-scope use case or to at least one?
> it includes at least one MoE candidate and at least one tiny dense candidate for a given use case

Section: Acceptance Criteria (the AC is literally satisfiable by one use case, while the goal it implements says "for each use case").
Proposed AC: Given every in-scope use case, its results table contains at least one MoE and one dense model row run over the same items.

**[major]** Which network path is in scope for the two-machine demo: same LAN, VPN, or the public internet?
> a request carrying a valid API key from a second machine

Section: Non-Goals + Acceptance Criteria (Non-Goals rules out public internet exposure; the AC does not say what it rules in, and the answer decides bind address, TLS and threat model).
Proposed AC: Given the demo, the service binds only to a configured LAN address over TLS, rejects every non-loopback request without a valid key, and refuses to start bound to a public interface.

**[major]** What distinguishes a sustained challenge from a question that was answered on the spot?
> with no sustained challenge to fiche disclosure, table separation, or judge agreement, the artifact is considered validated

Section: Acceptance Criteria (this is the pass condition of the validation AC and it turns on an undefined word).
Proposed AC: Given a challenge raised in a session, it counts as sustained when it is not resolved by evidence within that session, and it is logged against the specific AC it disputes.

**[major]** Which mechanism enforces that the check suite passed before a merge?
> must pass before the change is considered mergeable

Section: Acceptance Criteria ("considered" leaves it as a human convention; the repo currently has zero workflows and an unprotected `main`, which satisfies the AC as written).
Proposed AC: Given a pull request, the platform blocks the merge button until the required check suite reports success on the head commit.

**[minor]** Where is an out-of-scope use case marked so that a client sees it?
> or is explicitly and visibly marked out of scope for this release

Section: Acceptance Criteria (visible in the README, the results table, or the front end changes who actually sees it).
Proposed AC: Given a use case out of scope for a release, it appears in the published results table as an empty row labelled out of scope for that version.

### missing edge case

**[major]** What does the documented setup do on a machine with too little VRAM or RAM to load the model?
> the documented setup steps produce a working benchmark run without undocumented manual fixes

Section: Acceptance Criteria + Dependencies (the reproduction audience is a client engineer on unknown hardware; the AC assumes the model always fits).
Proposed AC: Given a machine below the declared minimum, setup fails fast naming the missing resource, and no runtime row is produced rather than a silently degraded one.

**[major]** Does the container image ship the model weights, or download them on first run?
> or its container image pulled

Section: Acceptance Criteria + Dependencies (a roughly 18GB GGUF plus GPU passthrough decides whether the image is distributable at all).
Proposed AC: Given the published image, it contains no model weights, and its documented first run downloads the pinned GGUF by revision hash and verifies the checksum.

**[major]** Which machine conditions must hold for a runtime record to be publishable?
> Runtime metrics (TTFT, tokens/s, RAM/VRAM, energy, carbon) and quality scores are both captured

Section: Goals, feeding a new Benchmark Methodology section (the validated baseline note records +/-1.4 tok/s spread and says nothing under 10% is reliable; a thermally throttled or loaded machine silently produces a different number).
Proposed AC: Given a runtime run, it records CPU package temperature and system load at start, and any metric whose repetition spread exceeds 10% is flagged unreliable.

**[major]** Is the artifact considered validated when 90 days pass with no client session at all?
> after 3 such sessions or 90 days (whichever comes first) with no sustained challenge

Section: Acceptance Criteria (as written, zero sessions in 90 days validates the release vacuously, which is the opposite of the intent).
Proposed AC: Given fewer than 3 logged sessions at the 90-day mark, the release is marked unvalidated rather than validated.

### missing actor

**[blocker]** Who does the client decision-maker read results from during a pitch, and what do they see?
> a client decision-maker judging the comparison at a glance

Section: User Stories (the Problem Statement names this audience as one of the two the results must survive; no user story, no AC and no surface exists for them, and the product brief says they see only the front end).
Proposed AC: Given a pitch session, the decision-maker views a results page showing the quality table, the runtime table with its fiche, and the energy headline, without touching a CLI.

**[major]** Who supplies the cloud provider API keys when a client-side developer reproduces a run?
> I want to clone the repo (or pull its container image) and reproduce the published results on my own machine

Section: Dependencies + Acceptance Criteria (the reproduction path silently requires the reproducer to hold Mistral and Google credentials and absorb their rate limits).
Proposed AC: Given a reproduction attempt without cloud keys, the local half of every suite still runs to completion and cloud rows are reported as skipped, not failed.

**[minor]** Who decides whether a logged challenge was sustained or resolved?
> the consultant can log whether it was challenged, dismissed, or accepted

Section: Acceptance Criteria (the consultant is both the challenged party and the scorer of the challenge, which is the weakest possible arbiter for a credibility claim).
Proposed AC: Given a logged challenge, the log records the client-side challenger's role and the evidence offered, so the judgement is auditable rather than self-reported.

### missing failure mode

**[blocker]** What quality score does an item receive when the model returns an empty, truncated, or unparseable answer?
> running it against a local model and a cloud model produces one quality score and one runtime record per model

Section: Acceptance Criteria, feeding Benchmark Methodology (scoring a failure as 0 versus excluding it changes the headline local-versus-cloud comparison, and small local models fail this way far more often than cloud ones).
Proposed AC: Given an item whose generation fails, truncates at the context limit, or cannot be parsed, it scores 0 and stays in the denominator, and the row records the failure reason.

**[major]** What is published when the two judges' agreement falls below the acceptable level?
> it is never presented without both judges' scores and their agreement level

Section: Acceptance Criteria (agreement is required to be reported but nothing says what a low value does to the score it accompanies).
Proposed AC: Given a judged item whose judges disagree beyond the suite's threshold, the item is published as contested and excluded from the suite's headline score.

**[major]** What happens to a partially completed suite when a cloud provider returns quota exhausted mid-run?
> Continued free-tier access to at least two independent cloud LLM providers

Section: Dependencies + Acceptance Criteria (free tiers are the stated basis, and a multi-minute local run discarded by a cloud 429 is the expensive failure).
Proposed AC: Given a cloud failure mid-suite, every row already produced is persisted and the run is marked partial with the failing provider and item recorded.

**[major]** What is recorded when a web-search tool returns no results or refuses the query?
> Continued free or low-cost access to at least two web-search tools/APIs

Section: Dependencies + Acceptance Criteria (an empty result set is a search-tool outcome that must be attributable to the tool, not scored as a model failure).
Proposed AC: Given a search call returning no results, an error, or a rate limit, the row records the tool's outcome and the item is excluded from the model's score while remaining visible in the tool comparison.

**[major]** How is the demo API key rotated or revoked after a client session?
> a request without a valid key is rejected

Section: Acceptance Criteria + Non-Goals (a key handed out for a live demo and never rotated outlives the demo).
Proposed AC: Given a demo session, the API key is read from the environment, never written to the repo or to logs, and the service refuses to start without one.

### missing acceptance criterion

**[blocker]** Which sampling parameters must every result row record for the score to count as reproducible?
> running it against a local model and a cloud model produces one quality score and one runtime record per model, using the same prompts

Section: Acceptance Criteria, feeding a new Benchmark Methodology section (project memory defines a quality score as reproducible given model, prompt and seed; the PRD never requires either to be recorded).
Proposed AC: Given any generated row, it records seed, temperature, top_p, top_k and the exact model id, and a re-run with those values reproduces the same score.

**[blocker]** How many repetitions back a published runtime number, and which spread statistic is shown with it?
> Runtime metrics ... and quality scores are both captured, kept separable, and each is defensible on its own terms.

Section: Goals + Acceptance Criteria, feeding Benchmark Methodology (the project's own validated baseline requires `-r 5` minimum; a single-shot number is not defensible on its own terms).
Proposed AC: Given a published runtime metric, it is the mean of at least 5 repetitions reported with its standard deviation, and the raw repetitions stay retrievable from the run record.

**[blocker]** Which field carries kg CO2e for each row alongside energy in kWh?
> the underlying calculation (method, inputs, formula/tool version) is retrievable from the same run's record

Section: Acceptance Criteria (carbon is named in Goals and in the domain language but no AC ties it to a stored value, and the implementation consequently discards it).
Proposed AC: Given any run row, it stores emissions in kg CO2e next to energy in kWh, with the emission factor and the CodeCarbon version that produced both.

**[blocker]** What is in the web-research query set, and how is an answer scored?
> at least two distinct web-search tools are benchmarked against the same query set, with results attributable to which tool was used

Section: Acceptance Criteria (the AC refers to "the same query set" as though it were defined; nothing defines its size, freshness, ground truth, or scoring rule, so the suite cannot be built or judged).
Proposed AC: Given the web-research suite, it holds at least 20 queries with dated reference answers, each scored by two judges against the retrieved sources, with the search tool recorded per row.

**[major]** Which energy and carbon figure does a cloud model row carry?
> a calibrated formula-based estimate (Scope 3, covering datacenter overhead and hardware amortization) for cloud/API models

Section: Dependencies + Acceptance Criteria (the Scope-3 estimate lives only in Dependencies; no AC requires a cloud row to carry one, so half of the on-prem-versus-cloud energy comparison has no pass condition).
Proposed AC: Given a cloud model row, it carries a formula-based Scope-3 estimate with its inputs and formula version, labelled as an estimate.

**[major]** How is an estimated energy figure distinguished from a measured one in the number shown to a client?
> Energy/carbon figures are reported at a high, strategy-level headline (a single defensible number per run)

Section: Goals + Acceptance Criteria (Open Questions acknowledges the Windows/NVML caveat, so the caveat is not hidden; what is missing is any AC forcing the label to travel with the headline number, while project memory already mandates an `energy_method` field).
Proposed AC: Given the headline energy figure, it is displayed with its `energy_method` label and the estimate's uncertainty range, never as a bare number.

**[major]** What is the minimum number of items a task suite must hold before its score is publishable?
> each of the ten use cases ... has at least one task suite exercising it

Section: Acceptance Criteria, feeding Benchmark Methodology (the one shipped suite holds 10 items, where a single item moves the score by 10 points).
Proposed AC: Given a task suite, it holds at least 20 items, and a suite below that publishes its score marked indicative.

**[major]** Which version identifier of the task suite and its prompts is recorded with each score?
> A client or their engineer can independently reproduce the quality scores

Section: Goals + Acceptance Criteria (without a suite version, two scores produced by different prompt revisions are silently comparable).
Proposed AC: Given a result row, it records the suite id and a content hash of the prompt set, and any prompt edit bumps the suite version.

**[major]** Which version of the judge prompt and rubric produced a judged score?
> open-ended task scores backed by two independent LLM judges with agreement reported

Section: User Stories + Acceptance Criteria (a judged score is only as reproducible as the judge prompt behind it).
Proposed AC: Given a judged row, it records the judge prompt id and content hash, the judge model's dated id, and the rubric version.

**[major]** Which exact cloud model identifier is recorded so that an alias rotation does not silently change published results?
> Continued free-tier access to at least two independent cloud LLM providers for judging and cloud-model comparison.

Section: Dependencies + Acceptance Criteria (the implementation already learned this and pinned a dated Mistral id; the PRD does not require it, so the next provider repeats the mistake).
Proposed AC: Given a cloud row, it records the provider's dated model id, never a floating alias, plus the API version, and a run refuses to start when that id is absent from the provider's model list.

**[major]** Which generation limits are held constant across models: context size, max output tokens, and stop sequences?
> Consultants need to compare local SLMs against cloud LLMs on the client's actual use cases

Section: Problem Statement + Acceptance Criteria, feeding Benchmark Methodology (these caps change both quality and tokens/s, and differ by default between llama.cpp and every cloud API).
Proposed AC: Given one item compared across models, all models receive the same context window cap, max output tokens and stop sequences, and each row records the three values used.

**[major]** How is a new model added to the roster, and where is its per-model flag set recorded?
> Given the model roster, it includes at least one MoE candidate and at least one tiny dense candidate

Section: Acceptance Criteria (dense models must not receive `--n-cpu-moe`, so the flag set is per model, not per run; the fiche records flags but nothing says where they come from or how a model joins the roster).
Proposed AC: Given a model in the roster, a registry entry pins its repo revision, file name, quant, checksum and exact server flags, and every row's fiche cites that entry.

**[major]** Which release version and commit produced a given result row?
> I want releases tagged with a changelog, so that I can tell a client exactly which version produced the numbers they're looking at.

Section: User Stories + Acceptance Criteria (the release AC only requires that a tag and changelog exist; nothing links a number a client is looking at back to a version).
Proposed AC: Given any result row, it records the release version and the commit sha of the code that produced it.

**[major]** What test-coverage threshold must the repo hold for the engineering-quality claim to be verifiable?
> The repo itself demonstrates engineering quality (tests, reproducibility, pinned dependencies, automated security/dependency checks)

Section: Goals + Acceptance Criteria (this goal is aimed at a client-side developer auditing the repo, and "tests" with no threshold is the one part of the evidence chain with no pass condition; v1 reported 86.5%).
Proposed AC: Given a change, the check suite reports line coverage and fails below 80%.

**[major]** Which cost figure does a row carry so an on-prem-versus-cloud comparison covers price as well as speed and quality?
> without a credible basis for an infrastructure decision that carries real cost

Section: Overview + Goals + Acceptance Criteria (cost is the decision variable the Overview names and the only major one the PRD neither measures nor lists in Non-Goals; a client comparing deployments will ask for it first).
Proposed AC: Given a cloud row, it records tokens in and out plus the provider's list price at run time; given a local row, it records wall-clock hours and kWh, so a cost per 1000 tasks is derivable on both sides.

**[major]** Which language does the judge rubric use when scoring a French or German output?
> multilingual handling (at minimum English, French, German)

Section: Goals + Acceptance Criteria (judging a French answer with an English rubric prompt is a known source of score drift, and the multilingual use case has no scoring rule of its own).
Proposed AC: Given a non-English item, the judge prompt is issued in that item's language and the row records the judging language.

### missing dependency

**[blocker]** Which model weight files and llama.cpp binary build must be obtainable for a reproduction, and from where?
> Availability of local hardware representative of the target consumer-hardware class

Section: Dependencies (Dependencies names hardware, cloud providers, search tools, GitHub, CodeCarbon and a container registry, but not the two artifacts without which no run starts: the GGUF weights and the llama-server binary, which is currently an undocumented external download).
Proposed AC: Given the setup documentation, it names each GGUF by Hugging Face repo and revision with its checksum, and the llama.cpp build by tag and download source.

**[major]** Which licence governs each roster model when a client runs it on their own machine?
> the benchmark surfaces whichever model family performs best — MoE or dense

Section: Dependencies (the reproduction story hands models to a client for commercial evaluation; roster licences vary and some restrict exactly that).
Proposed AC: Given a roster entry, it records the model's licence id and whether client-side commercial use is permitted.

**[minor]** Where is the per-session challenge log kept so that the three-session count can be audited?
> the consultant can log whether it was challenged, dismissed, or accepted

Section: Acceptance Criteria + Dependencies (the validation AC counts sessions from an artifact that is never named or located).
Proposed AC: Given a client session, its outcome is appended to a tracked file in the repo, recording the release version it judged.
