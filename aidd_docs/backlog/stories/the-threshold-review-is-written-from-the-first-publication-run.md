---
type: story
status: ready
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

Blocked: through `depends_on` on `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md` and `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md`, both `ready` since the 2026-10-03 arbitration (Q105, Q106, Q118, Q119 and Q130 to Q135 answered), not yet built, whose published batches are this review's input; both wait in turn on `aidd_docs/backlog/stories/the-laptop-proves-both-modes-and-republishes-the-bundle-once.md` (`ready`) to move the bundle's schema (owner answer Q134 (a), 2026-10-03).

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- `suite_gate.py` holds the constants under review: `MIN_SUITE_ITEMS` 20, `MIN_LANGUAGE_SHARE` 0.25, `MIN_PER_LANGUAGE_CELL_ITEMS` 10, `MIN_PUBLICATION_SUITE_ITEMS` 100, `PUBLICATION_SIZE_TARGETS` (100, 300). A row carries the gate's `indicative` and `indicative_reasons` (`quality_cli`), which hold only the 20-item count and the 25% share reasons, never the cell floor. The 10-item cell floor fires per language, on `language_breakdown[<lang>].indicative` for an exact-match row and on `score_breakdown[<lang>].indicative` for a graded one (`scoring.score_suite_by_language` and `score_graded_suite_by_language`, both `n < MIN_PER_LANGUAGE_CELL_ITEMS`), a batch field every row of the batch repeats.
- From schema `"21"` a quality row carries `score_interval`: a suite cell and one cell per language, each with its interval and `minimum_detectable_effect` (`score_interval.interval_block`). The export flattens it to `score_interval_*` columns, and `scripts/recompute_from_export.py` recomputes every interval block from the tables alone.
- The development side of the comparison is `classification-support-routing` at 20 items (10 EN, 5 FR, 5 DE) and `translation-business-short-form` at 21 (7 per language), so every development language cell but classification's 10-item EN cell fires the floor (`n < 10`).
- No committed row carries `score_interval`: `quality-reference.jsonl` is 80 `classification-support-routing` rows at schema `"7"`. The n=20 classification widths and minimum detectable effects (for example Qwen3.6-35B-A3B 0.80 [0.600, 0.950], 0.175) are an analysis recorded in `aidd_docs/results/README.md`, "Each batch's interval and what it could resolve", not row fields.

## Acceptance

- The review cites, from the published rows: the interval widths at n=100 (or the publication suite's actual size) against those at the development size for the same use case (n=20 for classification, n=21 for translation), compared in pairs of the same subject and scoring kind: the suite cell of the publication batch against the suite cell of its development batch, and each language cell against the same language's cell, the development side read from the development-level batches of `classification-support-routing` and `translation-business-short-form` that orders 7 and 8 publish beside their publication batches, on the same subject in the same bench session (owner answer Q120 (a), 2026-10-03); the observed per-language cell counts; the number of (batch, language) cells in which the 10-item cell floor fired on the publication run, counted once per cell and not once per row; and the observed minimum detectable effect at both sizes.
- It is checkable: every observed figure it cites matches the published rows, and a test or a recorded recomputation over the bundle shows it. The derived figure for a 25-item cell (below) is exempt and states its derivation instead.
- On that evidence it states: whether the 10-item per-language floor ever fires again once cells hold 25 items or more; whether 20 remains the right development floor; whether the publication size looks sufficient or thin; and whether the size target belongs against the suite or against the language cell.
- It says rather than implies that at the 25% minimum share a 100-item suite yields about 25 items per language cell, and that such a cell resolves little, so a cell that stops firing the floor has not thereby become readable. It gives the figure as derived, not observed, with its derivation: for a binary cell of 25 items at an accuracy near 0.5, the cell's `minimum_detectable_effect` (half its 95% interval width, `score_interval.bootstrap_cell`) is about 1.96 x sqrt(0.25 / 25), roughly 0.20 or 20 points; a difference between two models' independent cells of that size needs about sqrt(2) times that, roughly 28 points, and is labelled a two-model difference wherever it is cited.
- The outcome is recorded as an amendment to Methodology 4 or as an explicit decision to leave it, by the owner, never as silence. The constants in `suite_gate.py` are not moved before that decision.

## Code it changes

- None by necessity. A threshold change, if the owner decides one, is a follow-up change to `suite_gate.py` with its own tests.

## Tests it needs

- A recomputation over the bundle that reproduces every observed figure the review cites, counting fired floors per (batch, language) cell.

## Evidence it publishes

- The review itself under `aidd_docs/`, linked from `aidd_docs/results/README.md`, and the owner's recorded decision on Methodology 4.

## Cancellation

n/a: not cancelled.
