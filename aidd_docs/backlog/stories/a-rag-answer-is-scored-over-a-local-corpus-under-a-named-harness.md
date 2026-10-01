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

Maps to: PRD AC "Given the full use-case list, each of the nine task use cases ... has at least one task suite exercising it"; PRD AC "Given an agentic planning or tool-calling item, ... the row names the harness used and its version, reports that harness's per-call prompt overhead separately from the task's own tokens ...; a RAG answer-generation campaign includes `llamaindex` among them"; PRD AC "Given no client-provided document or prompt in a suite, no request leaving the machine ever contains one, and every row records whether its prompt left the machine"; Methodology 3, 4, 5, 9, 10, 11, 23; epic Boundaries "six suites" (RAG), "the agentic harness as a recorded row dimension", "a small repo-owned retrieval corpus and a retriever", "egress recorded"; epic Sequence step 4.

Needs: a real local model run (including a one-time download of the pinned embedding model), and paid API keys for Z.ai (GLM judge) and DeepSeek (DeepSeek judge).

Blocked: owner question Q33 (how per-call harness prompt overhead is measured), through the harness task it depends on, and, through `depends_on` on `glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md`, owner question Q6 and the two open judge-provider spikes. The corpus, retriever and harness fields can be built before the judges land; no judged score is published until they do.

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

## Cancellation

n/a: not cancelled.
