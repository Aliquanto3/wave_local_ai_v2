---
type: story
status: done
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/every-row-names-its-prompt-variant-and-a-baseline-row-carries-the-authored-prompt.md
order: 10
---

# Story: Each quality item records the tokens and the first-token time its generation took

**As** an academic or technical reviewer reading a claim that a variant saves tokens or time
**I want** each quality item to carry its own input and output token counts and its engine-reported first-token time, labelled as a per-item measurement distinct from the runtime protocol's figure
**So that** a variant's effect on tokens and TTFT per task family can carry a paired test over the same items, rather than being a difference of two batch totals

Maps to: PRD Open Question "Whether prompt compression helps or hurts a small model, in quality and in TTFT..."; Methodology 6, 20, 22, 24; epic Boundaries "the research question answered in a published, dated statement: for each variant, per task family, ... on quality, TTFT, tokens and energy, each difference carrying the paired test E-G provides or published as an observation".

Needs: none for the code and tests (constructed responses); a real local model run only for the evidence.

Blocked: Q24 (how TTFT, tokens and energy are measured per variant and per task family). The acceptance below is written to Q24's recommended default.

Current state: quality rows are per item but carry `tokens_in_total`, `tokens_out_total` and every energy field as batch figures, and no TTFT; the runtime protocol measures TTFT and energy on one fixed prompt (`FIXED_PROMPT` in `__init__.py`), not on suite items.

## Acceptance

- Every local quality row carries the item's own input and output token counts and the engine-reported first-token time for that generation, with a source label on the `ttft_source` discipline and a label stating it is a single per-item generation, not a Methodology 6 aggregate. A value the engine did not report is null with its reason, never zero.
- The batch's first generation is marked as such, so a reader can exclude a cold first item.
- The paired-test analysis can take per-item tokens or per-item TTFT as the compared quantity over the same item ids, with the scoring-kind rule extended to name which test applies to a continuous per-item measurement.
- Energy stays per batch; a per-variant energy difference is published as an observation, and the record says why it carries no paired test.

## Code it changes

- `quality_cli.py` / `local_client`: per-item timings and token counts from the engine response; `row_contract.py`: the per-item fields and labels, `SCHEMA_VERSION` bumped.
- The comparison module: per-item continuous quantities as compared fields.

## Tests it needs

- Per-item fields populated from a constructed engine response; an unreported value is null with its reason.
- A constructed variant pair compared on per-item output tokens produces a Wilcoxon record over identical item ids.

## Evidence it publishes

- Per-item token and TTFT figures on order 4's cell pair, and the paired record on output tokens, in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
