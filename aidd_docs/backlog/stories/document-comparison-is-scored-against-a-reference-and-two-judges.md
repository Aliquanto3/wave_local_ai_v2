---
type: story
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish.md
  - aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md
order: 3
---

# Story: Document comparison is scored against a reference and two judges

**As** a consultant whose client compares contract or policy versions today with a cloud model
**I want** a document-comparison suite scored by a reference-based metric and by the GLM and DeepSeek judge pair, local and cloud models side by side on the same items
**So that** the first use case beyond the three shipped ones has published rows, and the suite seam is proven on a new suite at the lowest cost

Maps to: PRD AC "Given the full use-case list, each of the nine task use cases ... has at least one task suite exercising it"; PRD AC "Given an open-ended task result from a subject independent of both judge families, it is never presented without both judges' scores and their agreement level"; PRD AC "Given a judged item whose two judges disagree beyond the suite's stated threshold, the item is published as contested and excluded from that suite's headline score"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side"; Methodology 3, 4, 5, 9, 10, 11; epic Boundaries "six suites" (document comparison), "per-suite rubric text and per-suite contested threshold"; epic Sequence step 2; epic success check 2.

Needs: a real local model run, and paid API keys for Z.ai (GLM judge) and DeepSeek (DeepSeek judge); a cloud subject key already configured (Mistral or Google AI Studio) for the cloud rows.

Blocked: only through `depends_on` on `aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md` (`proposed`), which waits on its orders 8 and 9 (`a-glm-judge-answers-through-z-ai-under-the-pinning-discipline.md`, `a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline.md`, both `proposed`), each blocked by its spike (`aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`, both `blocked`: desk research done, the live calls with a paid key listed in each Follow-up not yet run). The items, caps and reference metric can be authored before then; no judged score is published until the pair lands.

Current state (verified on `main` at `c68b23e`, 2026-10-03): no document-comparison suite exists; `src/wave_local_ai_v2/suite_data/` holds only `classification-support-routing.json` and `translation-business-short-form.json`, and `use_case_coverage.json` has `document-comparison` at state `null`. The seam is shipped: `suite_registry.resolve` loads a definition through `suite_gate.gate_suite` (`MIN_SUITE_ITEMS = 20`, `MIN_LANGUAGE_SHARE = 0.25`, indicative below either). `scoring_rules.SCORING_RULES` holds `exact_label_match` and `chrf_against_reference` only; chrF is pure and in-repo (`chrf.METRIC_ID = "chrf"`, `METRIC_VERSION = "1"`). No registered rule calls a judge: judged scoring runs only in `judge_probe.py`, under one global contested threshold (`settings.contested_ordinal_max_delta`, default `DEFAULT_CONTESTED_ORDINAL_MAX_DELTA = 1`), and `suite_registry._CORE_KEYS` has no rubric or threshold key (an added key lands in `SuiteDefinition.extra`). `judge_backends.py` binds only Mistral and Google; no GLM or DeepSeek client exists.

## Acceptance

- A document-comparison suite is registered through the seam (order 1) with at least 20 items, each of EN, FR and DE at 25% or more, every item tagged with its language and its provenance, and any public-origin text marked contamination-risk. Below either threshold it publishes marked indicative through the shipped gate.
- Each item asks for the differences between two versions of one document and carries a hand-written reference. The reference-based metric is pure, in-repo, and named and versioned on every row, the way chrF is on the translation suite.
- The suite's caps are set from the smallest context length among the roster models it is run on, recorded per row, and identical across every model compared on an item; no item is shortened per model (Methodology 3).
- Every row carries the GLM and DeepSeek scores and their agreement figure, or the single-judge flag where the subject shares a family with one judge, through the judge machinery as shipped. The suite owns its rubric text and its contested threshold; the threshold is the shipped default (more than 1 point) unless the suite records a different value and why.
- An empty, truncated or unparseable generation scores 0, stays in the denominator, and records which of the Methodology 9 reasons applies.
- At least one local and one cloud batch are published as rows in the reference bundle, and the coverage record's document-comparison entry moves to `exercised` naming this suite.

## Code it changes

- The suite's data file and its scoring rule, registered through order 1.
- The reference metric module, if no existing metric fits.
- The coverage record entry.

## Tests it needs

- The suite passes the gate; a fixture shrunk below 20 items publishes indicative (epic success check 2).
- The metric against hand-computed values on a fixed pair; a planted empty generation scores 0 and names its reason.
- With HTTP stubbed, a judged row carries both judge blocks and the agreement figure, and a planted 2-point disagreement is published contested and excluded from the headline.

## Evidence it publishes

- The local and cloud batches, the suite snapshot, and the coverage entry.
- One MoE and one tiny dense roster entry run over the same items at one suite version and published side by side, each citing its roster entry; or, for an entry that cannot run this suite, a recorded refusal naming the entry and why.

## Cancellation

n/a: not cancelled.
