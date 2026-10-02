---
type: spike
status: open
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parents:
  - aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md
---

# Spike: Which public classification benchmark seeds the publication suite, and on what terms

## Question

Which named public classification benchmark can seed a publication-level suite of at least 100 items (300 where it supplies them) with EN, FR and DE each at 25% or more, and does its licence put a drawn subset on the permissive, share-alike or no-redistribution rung for a bundle published under CC-BY 4.0?

## Decision

Which source the classification publication suite draws from, and which of the epic's three pre-written licence consequences applies to its items and derived rows: permissive ships items and rows unchanged; share-alike segregates the drawn items and their rows under their own licence file; no-redistribution redacts `prompt` and `expected_label` on the rows to the per-item content hash.

## Bounds

- Evidence needed: for each lead (MASSIVE first, as the epic names it; others only if it fails), the licence text as published by the source at a named revision; whether that licence is share-alike, checked first because it is the likeliest branch; whether it permits redistributing a subset inside a CC-BY 4.0 bundle, evaluated against the row contract (`REQUIRED_FIELDS["quality"]` carries `prompt` and `expected_label` verbatim), not only against `suite-definitions/`; whether EN, FR and DE splits exist at the needed size with a label set usable for exact-match scoring; the stable source key and loader a canonical ordering would use.
- Stop when: one lead is shown to meet the size and language constraints with its licence rung stated from the licence text, or every named lead is shown to fail one of them.
