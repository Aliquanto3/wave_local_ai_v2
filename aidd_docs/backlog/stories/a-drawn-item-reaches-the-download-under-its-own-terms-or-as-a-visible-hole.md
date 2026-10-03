---
type: story
status: proposed
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
depends_on:
  - aidd_docs/backlog/stories/the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives.md
  - aidd_docs/backlog/stories/the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary.md
  - aidd_docs/backlog/stories/each-release-attaches-one-archive-that-needs-no-clone.md
  - aidd_docs/backlog/stories/a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source.md
  - aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md
  - aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md
order: 7
---

# Story: A drawn item reaches the download under its own terms, or as a visible hole

**As** a third-party researcher holding a download that mixes hand-written and public-benchmark items
**I want** every drawn item to name its source and that source's licence, and every item whose text may not be redistributed to show as a marked absence telling me where to obtain it
**So that** I know what I may republish item by item, and a missing prompt reads as a stated licence constraint rather than as a bug

Maps to: PRD AC "Given a published release, its suite items and reference result bundle carry CC-BY 4.0 while the code stays MIT, and the published results are also available as a tabular export readable outside the repo without running it"; PRD Open Question on public benchmarks ("permissive", "share-alike", "no redistribution", each with its consequence); PRD Dependencies "Licence and redistribution terms of the public benchmarks whose subsets seed the publication-level suites"; Methodology 4, 5; epic Boundaries "mixed terms inside one download, stated part by part rather than averaged"; epic decision "An unredistributable item is a visible hole"; epic success checks 3 and 5; owner answer to Q41 (option a, 2026-10-01).

Needs: none for the behaviour, which constructed bundles prove. Its published evidence waits on publication-suite rows, which the interval epic's suite stories produce with a real local model run.

Blocked: by Q106 in `aidd_docs/tasks/2026_10/2026_10_02_backlog-refinement/owner-questions.md`, which alone decides whether any drawn source is not permissive: the classification spike puts both of its candidates on the permissive rung (CC BY 4.0), so Q105 changes no rung here, and the translation spike is `blocked` on Q106 alone (WMT24++ permissive under Apache-2.0, or no-redistribution, or NTREX-128 share-alike). If Q106 is answered (a), every source is permissive and the share-alike and no-redistribution halves have no live case; they are then proven on constructed bundles only, as `Needs:` already allows. Through `depends_on` also by `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md` (`proposed`; blocked by Q105), `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md` (`proposed`; blocked by Q106, Q118 and Q119) and `aidd_docs/backlog/stories/each-release-attaches-one-archive-that-needs-no-clone.md` (`ready`, not yet built: it owns the archive assembly this story extends). The other three `depends_on` stories are `done`.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- `bundle_export.py` writes five tables. `quality_items.csv` carries `item_licence`, `item_source` and `item_source_revision` straight from the rows (`quality_rows.suite_item_fields`), documented as declared, not verified. A row carries no item `content_hash` or stable source key, and the export joins each row's suite definition without its `items` (`_suite_source`), so no content-hash, stable-key or redaction column exists. The `provenance` dictionary entry reads "(hand_written)".
- No archive assembly exists: `.github/workflows/ci.yml` creates no Release and attaches no asset (order 4 is `ready`, not built).
- `LICENSE-DATA` section 2 states that the bundle holds no drawn item, excludes drawn items from the CC-BY 4.0 grant, makes their licence per item and names no source; section 3 holds two declarations. Neither the export nor `aidd_docs/results/README.md` states the hand-written-only coverage; only `LICENSE-DATA` does.
- The committed suite-definition snapshots (`aidd_docs/results/suite-definitions/*.json`) carry each item's text, and `suite_registry` refuses an item with an empty `prompt`, so on the no-redistribution rung the redaction has to reach the snapshots as well as the rows.

## Acceptance

- Every drawn item in the quality table carries its licence, its source, that source's revision and its content hash as columns, as the rows and suite definitions record them; a hand-written item reads CC-BY 4.0 in the same column. The export reads these fields and decides none of them.
- `LICENSE-DATA`'s drawn-items section lists each source the bundle draws from, its licence, which rung applies (permissive, share-alike or no redistribution), and the notices that licence requires on redistribution (CC BY 4.0: creator, copyright notice, licence link, source link and revision, and that each item was wrapped in a prompt template; Apache-2.0: a copy of the licence text beside the items and a statement of the change made), and the archive README repeats it.
- Share-alike: the drawn items and their derived rows travel in the archive under their own licence file, as the interval epic segregates them in the bundle, and the tables mark which rows that file governs.
- No redistribution: where the rows carry the item text redacted to its content hash, the exported row says so in a column of its own and names, per item, the source, its revision and the stable source key. The archive README carries one written instruction per such source for obtaining the text and joining it to the rows by that key; the content hash lets the reader prove a fetched item is the one that was scored. The archive ships no fetch script or other code that downloads a third party's corpus (owner answer to Q41), and the reader performs the join to the source by hand. A redacted field is never an empty cell indistinguishable from missing data, and the dictionary states that such a row's score cannot be recomputed from the download alone.
- Until a drawn item exists in the bundle, the export and `LICENSE-DATA` say the download covers only hand-written items (`LICENSE-DATA` section 2 already does from order 1; the export of order 3 does not yet state it).

## Code it changes

- The export module of order 3: the licence, source and redaction columns and their dictionary entries.
- The archive assembly of order 4: the share-alike licence file and the drawn-items README section, including the per-source instruction for each no-redistribution source.
- `LICENSE-DATA`: the drawn-items section filled.

## Tests it needs

- Over constructed bundles, one per rung: a permissive drawn item exports its source licence; a share-alike set ships under its own licence file and its rows are marked; a redacted item exports the absence column, source, revision, key and hash, never an empty prompt alone, and the archive README holds one instruction for its source; the archive contains no fetch script.

## Evidence it publishes

- The first release archive holding a drawn subset, with its drawn-items section and, if a rung requires it, one redacted row shown as it reads in the table.

## Cancellation

n/a: not cancelled.
