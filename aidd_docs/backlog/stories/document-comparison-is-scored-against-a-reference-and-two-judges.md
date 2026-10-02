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

Blocked: through `depends_on` on `glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md` (`proposed`), which waits on the two open judge-provider spikes (`is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`). The items, caps and reference metric can be authored before then; no judged score is published until the pair lands.

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
