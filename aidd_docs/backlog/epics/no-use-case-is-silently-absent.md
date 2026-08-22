---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
depends_on:
  - aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
related_to:
  - aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
  - aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
---

# Epic: No use case is silently absent

Given the PRD's full use-case list, a reader of the published results finds every entry in one of three declared states — exercised by a suite whose rows meet the methodology criteria, covered as a dimension of another suite, or marked out of scope for this release — and every web-research row names the search tool that produced it.

## Context and Value

The audience is both of the ones the PRD says a result must survive at once: the client-side engineer auditing methodology, and the decision-maker judging the comparison at a glance. Completeness is the one claim in the PRD that either of them can falsify by reading a list rather than by reading a row, which makes a missing use case the cheapest challenge a sceptic makes and the most expensive one to answer mid-pitch.

The PRD's acceptance criterion states the obligation directly: each of the nine task use cases "has at least one task suite exercising it, or is marked out of scope for this release as a labelled empty row in the published results table", with multilingual EN/FR/DE coverage satisfied as a language dimension of the classification, translation and rewriting suites per Methodology 4. Nine task use cases plus that multilingual dimension are the ten entries this epic's coverage record must account for.

Three of the nine are owned elsewhere. `quality-scored-comparison-first-three-use-cases` takes classification, translation and rewriting, and defers the rest: its Boundaries exclude "document comparison, code generation, agentic planning, agentic tool calling, web research, RAG answer generation, and multilingual coverage as its own use case — all deferred to later epics", and its unknowns table records "Remaining 7 use cases' sequencing across future epics" as a decision explicitly not taken there. This epic is that sequencing pass, and it takes all seven rather than splitting them across several.

Verified current state, at `a2ffe37`:

- **One suite exists, and it is not a suite the harness knows about.** `classification_suite.py` is a module-level list of ten items, imported directly by the CLI (`quality_cli.py:19`), with the suite's identity written as a string literal at the row-writing site (`quality_cli.py:206`). There is no suite definition shape, no registry, and no second suite to register. Six new suites cannot each be another import.
- **The scoring path holds one string per item.** `_run_local_suite` returns `list[str]`, one completion per item (`quality_cli.py:139-170`), and `scoring.py` compares it to an expected label by normalized exact match. A transcript, a tool-call sequence, a retrieved source set and an execution result are all shapes the harness has nowhere to put.
- **The local call is the raw completion endpoint.** `POST /completion` (`quality_cli.py:146`), not `/v1/chat/completions`. Tool calling needs the OAI-compatible endpoint with a `tools` array; `--jinja` is already set on the server (`server.py:70`), so the chat template is available but the endpoint that would use it is not called. `mistral_client.complete_prompt` has the same gap on the cloud side — one prompt in, one string out, no tools parameter (`mistral_client.py:47`).
- **None of the four new capabilities exists in any form.** Five runtime dependencies (`codecarbon`, `nvidia-ml-py`, `psutil`, `python-dotenv`, `requests`) and twelve benchmark-side modules: no retrieval, no embedding model, no corpus, no search client, no sandbox.
- **Judging does not exist yet.** The judge epic records this against the same commit. Four of the six buildable suites here are judged, so they can be authored before that epic lands but cannot publish a score until it does. Code generation is the exception and is judge-free by design.

The value has two halves. The first is the completeness claim itself: a coverage record where every entry carries a state is what converts "we didn't get to it" from an omission into a disclosure, and the PRD already chose disclosure as the answer. The second is where the consultant's argument actually lives. Classification, translation and rewriting are the use cases where the on-prem case is easiest and least contested. Code generation, RAG answer generation and agentic tool calling are where a client is currently paying a cloud vendor and where the on-prem answer is genuinely unknown — leaving them out would make the benchmark strongest exactly where the decision is easiest and silent where it is hard.

Confirmed this session: the release is paced by the work, not by a dated engagement. Nothing is cut for time, and the sequence below is ordered by dependency and value rather than by a deadline.

## Boundaries

- Includes: **the suite seam** — a suite definition shape and a registry, so a suite is data plus a named scoring rule rather than an import in the CLI and a string literal at the write site. The shape carries the fields the methodology already demands of every suite: generation caps, stop sequences and context length (criterion 3), per-item language tags (criterion 4) and per-item provenance with contamination-risk marking (criterion 5). It consumes the gate `every-published-row-explains-and-reproduces-itself` ships; it does not reimplement it.
- Includes: **six suites, one per remaining buildable use case**, each with its items, its caps, its provenance and language tags, and a named scoring rule — document comparison (reference-based metric plus judge), code generation (test execution in a sandbox, deterministic), RAG answer generation (reference-based metric plus judge, over a repo-owned corpus), agentic tool calling (transcript checked against the item's expected tool calls), agentic planning (plan transcript checked against an expected step and tool set, plus judge), web research (judged against the archived retrieved sources, with the tool recorded per row).
- Includes: **the multilingual entry marked covered-by-dimension**, visibly, in the same record and with the same weight as an out-of-scope entry, naming the three suites that carry the languages. Nothing is built for it: the decision that multilingual is a dimension of the classification, translation and rewriting suites under criterion 4 is taken and is not reopened here.
- Includes: **the coverage record as data** — one entry per use case, each declaring `exercised` with its suite id, `covered-by-dimension` with the suites carrying it, or `out-of-scope-this-release` with the reason. A use case absent from the record, or present with no state, is not a shape the harness can publish.
- Includes: **tool-call transcript capture**, over llama-server's `/v1/chat/completions` with `--jinja` locally and the cloud providers' chat APIs, with the transcript stored on the row so an expected-call mismatch is legible as a mismatch rather than as an unexplained low score.
- Includes: **a small repo-owned retrieval corpus and a retriever**, with an embedding model pinned like a roster entry but never run as a benchmark subject.
- Includes: **a search-tool adapter interface with at least two implementations**, one self-hosted and one hosted API, and **per-row archival of every search response** so a score recomputes offline; a live re-run is labelled non-reproducible and is never compared against a published number (criterion 17). Criterion 18 in full: at least 20 dated queries with dated reference answers, judged against the retrieved sources, with the tool recorded per row.
- Includes: **the tool-outcome rule** the PRD states as acceptance — a search call returning no results, an error or a rate limit records that outcome, excludes the item from the model's score, and keeps it visible in the tool comparison.
- Includes: **a sandboxed runner for model-generated code**, with a refusal posture rather than a degraded one: where the sandbox is unavailable, the code-generation suite refuses to run instead of executing generated code on the host.
- Includes: **criteria 3, 4, 5 and 9 as acceptance on every suite this epic adds** — caps recorded per row and identical across the models compared on an item, at least 20 items with each of EN, FR and DE at 25% or more where the suite is language-tagged, provenance declared per item, and a generation that is empty, truncated or unparseable scoring 0, staying in the denominator, and recording its failure reason.
- Includes: **egress recorded on the surfaces this epic introduces** — a web-research row records that its query left the machine and to which tool; a RAG row records that retrieval was local.
- Includes: **per-suite rubric text and per-suite contested threshold** for the four judged suites, by the symmetry the judge epic already set when it excluded the rewriting suite's rubric text as belonging to the suite that consumes the protocol.
- Excludes: **the judge protocol, judge independence, the agreement statistic and the contested rule** — `any-open-ended-output-carries-two-judges-or-an-honest-flag` owns them. The four judged suites here are consumers of that machinery, and none of them rebuilds any part of it.
- Excludes: **the row schema, the versioned roster file, the fiche hash, run provenance, and the size, language and provenance gate itself** — `every-published-row-explains-and-reproduces-itself` owns them. The suites here are born compliant against that gate; the gate, not this epic's authorship, is what makes them so.
- Excludes: **showing any of this to a human.** The pitch epic renders the coverage record, the tool attribution on a web-research row, and the drill-down to an archived source set. This epic makes those exist and be correct.
- Excludes: **classification, translation and rewriting**, their items and their multilingual dimension. `quality-scored-comparison-first-three-use-cases` owns them; this epic records their coverage state and never touches their content.
- Excludes: **CI, the container image and release tagging.** One seam: the code sandbox needs a container runtime that `clean-machine-runs-it-and-nothing-reaches-main-unchecked` also introduces for the benchmark image, agreed with that epic rather than built twice.
- Excludes: **selecting a winning search tool or a winning model.** The comparison is the deliverable (PRD Non-Goals).
- Excludes: **any client-provided material.** Every suite item, every corpus document and every search query is the repo's own, per the PRD's egress non-goal; no opt-in path is built here.
- Excludes: **fine-tuning an embedding model, and any production retrieval stack.** The corpus is small and exists to score answers, not to serve them.

Criterion ledger, so the scope is checkable rather than described:

| Criterion | Here |
| --- | --- |
| 17 web-research archival | in scope, in full |
| 18 web-research suite shape | in scope, in full |
| 3, 4, 5, 9 | consumed as acceptance on every suite added here; the gate is the row epic's |
| 10, 11 judge protocol and independence | consumed; only per-suite rubric text and contested threshold are set here |
| 1, 2, 6, 7, 8, 12-16, 19 | out — row epic |

## Sequence

Ordered by dependency first and value second. Steps 3 and 4 may run in parallel once the seam in step 2 has proven itself.

| # | Use case | Why here | Gate before a story |
| --- | --- | --- | --- |
| 1 | Multilingual (EN/FR/DE) | Free: marked covered-by-dimension. Ships with the coverage record itself and proves the record can carry a non-suite state. | none |
| 2 | Document comparison | The cheapest real suite: it needs the seam and the judge, and no new harness capability at all. Proving the seam on it costs least. | judge epic |
| 3 | Code generation | The only new suite that is judge-free, so it can publish before the judge epic lands. Deterministic scoring by test execution gives the highest evidence density per unit of dependency. | sandbox posture decided |
| 4 | RAG answer generation | The use case a client's on-prem question most often turns on, and the one where local retrieval is the argument. Needs the corpus, the retriever and a pinned embedding model. | judge epic |
| 5 | Agentic tool calling | Introduces transcript capture, which step 6 rides. Placed after the deterministic and retrieval work because its evidence is only as good as the spike below allows. | **spike: llama.cpp tool-calling maturity per roster model** |
| 6 | Agentic planning | Rides step 5's transcript capture; adds only the expected step set and its rubric. | step 5, and the same spike |
| 7 | Web research | The heaviest: two adapters, archival, 20 dated queries, judged against retrieved sources, plus the PRD's own unresolved Open Question on which tools. Last because it depends on the judge, on the archival rule, and on a tool choice nobody has made. | **spike: search-tool selection** |

Two spikes are required before their stories, both named by the PRD itself:

- **Search-tool selection.** Which two tools, on what free or low-cost terms, and whether each returns a response that can be archived in a form which recomputes a score offline (criterion 17). It also settles one thing the PRD does not ask but the egress non-goal makes fair game: a self-hosted metasearch instance still forwards the query to third-party engines, so "self-hosted" must be checked as an egress claim rather than assumed as one.
- **llama.cpp tool-calling maturity, per roster model.** Whether each roster GGUF's chat template emits parseable tool calls through `/v1/chat/completions` with `--jinja`, and whether a failure is attributable to the model or to its template. This is the one gate that can send a use case out of scope: if a transcript measures the chat template rather than the model, the row is not evidence, and steps 5 and 6 are marked out-of-scope-this-release with the spike's finding published as the reason.

**Recommended out of scope for the first release: nothing.** All seven are covered — six built, one marked covered-by-dimension. Two conditional triggers stand, and each publishes a reason rather than a silence: the tool-calling spike failing sends agentic tool calling and agentic planning out of scope; two search tools proving unobtainable on free or low-cost terms sends the web-research tool comparison out of scope rather than presenting a one-tool comparison as if it satisfied the acceptance criterion.

## Success Evidence

The coverage read. Hand someone the published results and the PRD's use-case list, and nothing else. For all ten entries they find a state — exercised, naming the suite; covered-by-dimension, naming the suites carrying the languages; or out-of-scope-this-release, naming why. Nothing is absent, and nothing is present without one of the three.

Seven checks, each able to fail:

- The coverage record cannot be published with a use case missing, or present with no state — verified by removing one and watching the publication refuse, not by reading the writer.
- A suite added here that falls below the size gate, or whose EN/FR/DE mix falls under 25%, publishes marked indicative — verified by deliberately shrinking one against the row epic's gate.
- A code-generation item whose generated code fails its tests scores 0, stays in the denominator, and records its failure reason — verified by planting a deliberately wrong generation, not by unit-testing the scorer.
- A web-research row's archived search responses recompute the same score with the network off, and the same query run live is labelled non-reproducible and refused against the published number — verified by pulling the plug.
- Two web-research rows for the same query differ only by the tool that produced them, and each names its tool.
- A search call that errors or rate-limits produces a row that stays visible in the tool comparison and out of the model's score — verified by forcing a 429, not by reading the handler.
- A tool-calling transcript names the calls the model actually made, and a mismatch against the expected calls reads as a mismatch rather than as a low score — read off the row.

Once `done`, record here which two search tools were actually obtainable and on what terms, what the tool-calling spike found per model, whether the RAG corpus survived a contamination challenge from a client engineer, and whether any use case ended the release marked out of scope after all.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| The judge machinery, for four of the six suites | dependency | `any-open-ended-output-carries-two-judges-or-an-honest-flag`. The suites can be authored before it lands but publish no judged score until it does. Code generation is judge-free and is sequenced third for that reason, so this epic is not fully blocked in the meantime. |
| The row epic's gate, roster file and provenance fields | dependency | `every-published-row-explains-and-reproduces-itself`. Criteria 3, 4, 5 and 9 are consumed as acceptance on every suite added here, never reimplemented. |
| Which two web-search tools | spike | Pre-story, per the PRD's own Open Question. Settles the free or low-cost terms, the archivability of a response under criterion 17, and what a self-hosted instance actually forwards upstream. |
| llama.cpp tool-calling maturity, per roster model | spike | Pre-story. The only gate that can send a use case out of scope in this epic; its finding is published as the reason if it does. |
| Free or low-cost access to at least two search tools | dependency | PRD Dependencies, unverified in this repo. If only one proves obtainable, the tool comparison is published out of scope with that reason rather than presented as satisfied by one tool. |
| Sandbox posture for executing model-generated code | decision | Taken during delivery, not deferred silently. Recommendation: container-based, no network, no host mount, wall-clock and memory caps, and a refusal to run where no container runtime is present rather than a fallback to a host subprocess. Shares the container runtime the CI epic introduces. |
| Web research as agentic tool use, or as a retrieve-then-answer pipeline | decision | Recommended pipeline-first, so that web research does not inherit the tool-calling spike's risk and step 7 stays independent of steps 5 and 6. An agentic variant is deferred until that spike reports. Stated as a recommendation open to contradiction, not as a settled design. |
| The embedding model behind RAG retrieval | decision | Pinned with the same fields as a roster entry — revision, file, checksum, licence — but never run as a benchmark subject. `context_input/model_candidates.md` is explicit that it is not a generative model and must not be benchmarked on generative suites. |
| RAG corpus and document-comparison item provenance | assumption | Accepted: repo-owned or licensed, each document declaring its provenance under criterion 5, and any public-origin document marked contamination-risk like any other item. A corpus assembled from public text is a contamination claim a client engineer will make, and the marking is the answer to it. |
| Document-comparison items are long, and caps must be identical across the models compared on an item | assumption | Accepted: the suite's cap is set by the smallest context length in the roster for that suite and recorded per row, so no model is ever compared against another at a different cap (criterion 3). |
| The expected step and tool set for an agentic-planning item is itself a judgment | assumption | Accepted: it is authored with the item and versioned with the suite, so a disagreement about it is a suite-version question rather than an argument about a score. |
| Per-suite rubric text and contested threshold | decision | Owned here, per suite, by the symmetry the judge epic set when it left the rewriting suite's rubric to the suite that consumes the protocol. The protocol, the statistic and the independence rule stay there. |
| Where the coverage record is rendered | decision | Data here, rendering in the pitch epic. That epic's declared-absent contract already refuses to render a state it does not have, so an unpublished coverage entry surfaces as absence rather than as completeness. |
| Six new suites multiply cloud judge calls and free-tier exposure | assumption | Accepted: the judge epic's backoff and resumable partial runs are the mitigation and are not rebuilt here. Cost is reported, never optimised (PRD Non-Goals). |
| This is the largest epic in the backlog — six suites and four new harness capabilities | assumption | Accepted deliberately. It stays one epic because the outcome is one claim, that no use case is silently absent; splitting it by use case would leave the coverage guarantee itself owned by nobody, which is the failure the PRD's acceptance criterion exists to prevent. |

## Cancellation

n/a — not cancelled.
