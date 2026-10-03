---
type: story
status: proposed
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md
  - aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md
order: 9
---

# Story: The threshold review is written from the first publication run

**As** an academic or technical reviewer judging whether the suite sizes are fit for the claims made on them
**I want** a written review of the size and per-language thresholds that cites the observed interval widths, cell counts and detection limits at both suite levels
**So that** an `indicative` mark is removed, kept or moved on evidence rather than disappearing as a side effect of a suite growing

Maps to: PRD Open Question "Whether the Methodology's initial thresholds ... survive the first full-roster run"; Methodology 4 ("removing an indicative mark from a cell is itself a claim, to be argued against observed interval widths"); epic Boundaries "the threshold review the PRD promises"; epic Dependencies "Whether the publication size target is set against the suite or the language cell"; epic success check 13.

Needs: an operator: the owner decides whether Methodology 4 is amended or left, and the review records that decision. No new model run, API key or hardware beyond the published batches of orders 7 and 8.

Blocked: through `depends_on` on `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md` (`proposed`; blocked by Q105, the owner's choice of source) and `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md` (`proposed`; blocked by Q106, Q118 and Q119), whose published batches are this review's input. Also by one acceptance doubt of its own: the first bullet's n=20 side "from the published rows" does not exist for translation (the committed `quality-reference.jsonl` holds no translation row) and exists for classification only as the `aidd_docs/results/README.md` analysis over interval-less schema `"7"` rows; no `depends_on` story publishes a development-level translation batch carrying `score_interval`. Raised as owner question Q120.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- `suite_gate.py` holds the constants under review: `MIN_SUITE_ITEMS` 20, `MIN_LANGUAGE_SHARE` 0.25, `MIN_PER_LANGUAGE_CELL_ITEMS` 10, `MIN_PUBLICATION_SUITE_ITEMS` 100, `PUBLICATION_SIZE_TARGETS` (100, 300). A row carries the gate's `indicative` and `indicative_reasons` (`quality_cli`), which is where a fired cell floor is counted.
- From schema `"21"` a quality row carries `score_interval`: a suite cell and one cell per language, each with its interval and `minimum_detectable_effect` (`score_interval.interval_block`). The export flattens it to `score_interval_*` columns, and `scripts/recompute_from_export.py` recomputes every interval block from the tables alone.
- No committed row carries `score_interval`: `quality-reference.jsonl` is 80 `classification-support-routing` rows at schema `"7"`. The n=20 classification widths and minimum detectable effects (for example Qwen3.6-35B-A3B 0.80 [0.600, 0.950], 0.175) are an analysis recorded in `aidd_docs/results/README.md`, "Each batch's interval and what it could resolve", not row fields.

## Acceptance

- The review cites, from the published rows: the interval widths at n=100 (or the publication suite's actual size) against those at n=20 for the same use case; the observed per-language cell counts; the number of times the 10-item cell floor fired on the publication run; and the observed minimum detectable effect at both sizes.
- It is checkable: every figure it cites matches the published rows, and a test or a recorded recomputation over the bundle shows it.
- On that evidence it states: whether the 10-item per-language floor ever fires again once cells hold 25 items or more; whether 20 remains the right development floor; whether the publication size looks sufficient or thin; and whether the size target belongs against the suite or against the language cell.
- It says rather than implies that at the 25% minimum share a 100-item suite yields about 25 items per cell, resolving nothing under roughly a 25-point gap, so a cell that stops firing the floor has not thereby become readable.
- The outcome is recorded as an amendment to Methodology 4 or as an explicit decision to leave it, by the owner, never as silence. The constants in `suite_gate.py` are not moved before that decision.

## Code it changes

- None by necessity. A threshold change, if the owner decides one, is a follow-up change to `suite_gate.py` with its own tests.

## Tests it needs

- A recomputation over the bundle that reproduces every figure the review cites.

## Evidence it publishes

- The review itself under `aidd_docs/`, linked from `aidd_docs/results/README.md`, and the owner's recorded decision on Methodology 4.

## Cancellation

n/a: not cancelled.
