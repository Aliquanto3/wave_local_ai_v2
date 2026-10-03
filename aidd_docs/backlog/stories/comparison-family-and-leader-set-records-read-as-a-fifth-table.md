---
type: story
status: done
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
depends_on:
  - aidd_docs/backlog/stories/the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary.md
  - aidd_docs/backlog/stories/a-comparison-family-carries-its-adjusted-p-values-and-is-superseded-not-edited.md
order: 8
---

# Story: Comparison, family and leader-set records read as a fifth table

**As** a third-party researcher checking which published differences are real
**I want** every comparison, comparison-family and leader-set record in the bundle as one more flat table, with its columns in the same dictionary as the other four
**So that** I can read every paired test, every adjusted p-value and every leader set without parsing the bundle, and check them against the per-item rows they came from

Maps to: PRD User Story "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself"; PRD AC "the published results are also available as a tabular export readable outside the repo without running it"; PRD Non-goals (the leader set "is a published derived output ... recomputable by anyone holding that bundle"); Methodology 24; epic Boundaries "a tabular export command over the published bundle" and "a documented, versioned table schema"; epic decision "The export is derived, never authoritative"; owner answers to Q2 and Q42 (option a each, 2026-10-01).

Needs: none. The export runs over the committed bundle and constructed bundles; no model run, API key, hardware or operator is required.

Split, per the owner's answer to Q2 (`aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`): this table, its place in the command and its dictionary entries' presence are this epic's; the meaning, unit and null reasons of each statistical column are supplied by `a-score-is-published-with-its-interval-a-difference-with-its-test` (order 6 there) and are not redefined here. Per Q42, the leader set is computed into the bundle by that epic as its own records, and this table flattens them like any other record.

## Acceptance

- The export command of order 3 writes a fifth CSV table holding one row per comparison record, with the family it belongs to, and the family and leader-set records the bundle holds, in a shape the column dictionary states: every field each record carries becomes a named column, and a reader can tell from a column which record kind a row is.
- A refused comparison, a member listed as refused in a family, and a named null reason are visible rows and cells, never a missing row and never a number in place of a reason.
- A superseded family record stays a row, with the id of the record that supersedes it readable from the table, so a reader can tell the current family from an older one.
- The export computes nothing: every value in the table is a value a record in the bundle already carries, and no p-value, adjustment or leader set is derived during the export.
- Every column is in the dictionary and every dictionary column is in a table, as order 3 already enforces for the other four tables. Record kinds a bundle read does not hold (all three when this story was written; the committed bundle now holds all three) are named in the dictionary as not carried by that bundle, with the epic that owns them, and the table is written with its header and no rows rather than omitted.
- The CSV format pinning, the standard-library-only rule and the byte-identical rerun of order 3 hold for this table too.

## Code it changes

- The export module of order 3: the fifth table and its dictionary entries, reading the comparison, family and leader-set record files the analysis command writes under `aidd_docs/results/`.
- `aidd_docs/results/README.md`: the fifth table named beside the other four.

## Tests it needs

- Over a constructed bundle holding a tested comparison, a refused comparison, a family of two superseded by a family of three, and a leader-set record: every field appears as a column, the refused member and the null reason are visible, the supersede link is readable, and no value is absent from the source records.
- Over the committed bundle: the table is written with its header, the dictionary names the record kinds not carried, and the dictionary and tables agree both ways.

## Evidence it publishes

- The fifth table produced over the committed bundle, named in `aidd_docs/results/README.md` beside the other four.

## Cancellation

n/a: not cancelled.
