---
type: story
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish.md
  - aidd_docs/backlog/tasks/register-the-closed-harness-candidate-set-and-its-three-row-fields.md
  - aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md
order: 5
---

# Story: A RAG answer is scored over a local corpus, under a named harness

**As** a consultant whose client's on-prem question turns on answering over their own documents
**I want** a RAG answer-generation suite whose retrieval runs locally over a repo-owned corpus under `llamaindex`, with every row naming that harness, its version read at run time, and the prompt tokens it added before the task began
**So that** I can show what a local model writes over locally retrieved context, and the harness dimension exists on real rows before the agentic suites compare harnesses on it

Maps to: PRD AC "Given the full use-case list, each of the nine task use cases ... has at least one task suite exercising it"; PRD AC "Given an agentic planning or tool-calling item, ... the row names the harness used and its version, reports that harness's per-call prompt overhead separately from the task's own tokens ...; a RAG answer-generation campaign includes `llamaindex` among them"; PRD AC "Given no client-provided document or prompt in a suite, no request leaving the machine ever contains one, and every row records whether its prompt left the machine"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side"; Methodology 3, 4, 5, 9, 10, 11, 23; epic Boundaries "six suites" (RAG), "the agentic harness as a recorded row dimension", "a small repo-owned retrieval corpus and a retriever", "egress recorded"; epic Sequence step 4.

Needs: a real local model run (including a one-time download of the pinned embedding model), and paid API keys for Z.ai (GLM judge) and DeepSeek (DeepSeek judge).

Blocked: by Q110 (how a row names the client package a framework reaches the engine through: `llamaindex` reaches llama-server only through `llama-index-llms-openai-like`, while `harness.HARNESS_DISTRIBUTIONS` reads `llama-index-core`) and Q109 (whether an adapter keeps its framework's request defaults; LlamaIndex streams by default, and streamed Qwen3.6 output is llama.cpp #24807); and through `depends_on` on `aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md` (`proposed`), which waits on its orders 8 and 9, each blocked by its judge-provider spike (`is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`, both `blocked` on live calls with a paid key) and by Q102. The corpus, retriever and harness fields can be built before the judges land; no judged score is published until they do.

Current state (verified on `main` at `c68b23e`, 2026-10-03): `harness.py` closes the set at five (`HARNESS_IDS`) and implements only `direct`; `HARNESS_DISTRIBUTIONS["llamaindex"]` is `llama-index-core`, which `pyproject.toml` does not depend on, so `harness.harness_version("llamaindex")` raises `HarnessError` today. The only writer of the three harness fields is `quality_rows.direct_harness_fields`, and `row_contract._validate_harness` gates them on quality rows from schema "20" (`SCHEMA_VERSION` is "22"). `harness.prompt_overhead` already implements Q33 (a) with `unmeasurable` for a rewriting harness. No corpus, embedding entry or retriever exists; `aidd_docs/roster/models.json` holds subjects only. `subject_egress` (`row_contract.subject_egress_for`) records only where the subject prompt went (`none` or the provider id); nothing records retrieval locality. `use_case_coverage.json` has `rag-answer-generation` at `null`; judged scoring runs only in `judge_probe.py`, and `judge_backends.py` binds only Mistral and Google.

## Acceptance

- This story implements `llamaindex` against the closed harness registry the harness task ships, and every row this suite writes carries that task's three fields: harness id `llamaindex`, its version read from the installed package at run time, and its per-call prompt overhead apart from the task's own tokens, or the unmeasurable value where the rule cannot measure it.
- A small repo-owned corpus exists, every document declaring its provenance and any public-origin document marked contamination-risk; no client material is in it.
- An embedding model is pinned like a roster entry (revision, file, checksum, licence), covers EN, FR and DE, and is never run as a benchmark subject. Retrieval is a fixed part of each item: the same query retrieves the same passages for every model compared, and the retrieved passage ids are stored on the row.
- The suite holds at least 20 items with EN, FR and DE each at 25% or more, every item tagged and provenanced; below either threshold it publishes indicative.
- Each answer is scored by a pure, in-repo reference-based metric named and versioned on the row, and by the GLM and DeepSeek pair with this suite's own rubric text and contested threshold (the shipped default unless recorded otherwise).
- Every row records that retrieval was local and that no retrieved passage left the machine; a cloud-subject row records that its prompt, including the retrieved passages, left the machine for that provider.
- An empty, truncated or unparseable answer scores 0, stays in the denominator, and records its reason.
- At least one local and one cloud batch are published as rows in the reference bundle, and the coverage record's RAG entry moves to `exercised` naming this suite.

## Code it changes

- The `llamaindex` adapter against the harness registry.
- The corpus, the pinned embedding entry, the `llamaindex` retriever, the suite's data file and scoring rule.
- `pyproject.toml` and `uv.lock`: `llamaindex` and the embedding runtime, pinned.
- The coverage record entry.

## Tests it needs

- The harness version on a `llamaindex` row equals the installed package's version.
- The same query retrieves the same passage ids twice; the embedding entry's checksum is verified before use.
- With HTTP stubbed, a row carries the harness fields, the overhead apart from task tokens, the local-retrieval egress record, and both judge blocks.

## Evidence it publishes

- The local and cloud batches, the corpus and suite snapshots, the embedding entry, and the coverage entry.
- One MoE and one tiny dense roster entry run over the same items at one suite version and published side by side, each citing its roster entry; or, for an entry that cannot run this suite, a recorded refusal naming the entry and why.

## Cancellation

n/a: not cancelled.
