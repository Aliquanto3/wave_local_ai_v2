---
type: story
status: ready
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

Needs: none for the behaviour, which constructed bundles prove. Every drawn source is permissive (MInDS-14 under CC BY 4.0, owner answer Q105 (a), 2026-10-03; WMT24++ under Apache-2.0, owner answer Q106 (a), 2026-10-03), so the share-alike and no-redistribution halves have no live case and are proven on constructed bundles only. Its published evidence waits on publication-suite rows, which the interval epic's suite stories produce with a real local model run.

Blocked: through `depends_on` by `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md` and `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md`, both `ready` since the 2026-10-03 arbitration, not yet built. `aidd_docs/backlog/stories/each-release-attaches-one-archive-that-needs-no-clone.md` is `ready`, not yet built: it owns the archive assembly this story extends. The other three `depends_on` stories are `done`.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- `bundle_export.py` writes five tables. `quality_items.csv` carries `item_licence`, `item_source` and `item_source_revision` straight from the rows (`quality_rows.suite_item_fields`), documented as declared, not verified. A row carries no item `content_hash` or stable source key, and the export joins each row's suite definition without its `items` (`_suite_source`), so no content-hash, stable-key or redaction column exists. The `provenance` dictionary entry reads "(hand_written)".
- No archive assembly exists: `.github/workflows/ci.yml` creates no Release and attaches no asset (order 4 is `ready`, not built).
- `LICENSE-DATA` section 2 states that the bundle holds no drawn item, excludes drawn items from the CC-BY 4.0 grant, makes their licence per item and names no source; section 3 holds two declarations. Besides `LICENSE-DATA` section 2, `aidd_docs/results/suite-definitions/NOTICE.md` ("No item here is drawn today") and the "Suite levels" section of `aidd_docs/results/README.md` ("nothing was drawn") state the hand-written-only coverage; the export does not. Orders 7 and 8 of the interval epic land on the permissive rung, write section 2's drawn-source structure and replace those statements; no interval story segregates or redacts.
- The committed suite-definition snapshots (`aidd_docs/results/suite-definitions/*.json`) carry each item's text, and `suite_registry` refuses an item with an empty `prompt`, so on the no-redistribution rung the redaction has to reach the snapshots as well as the rows.
- A drawn item carries a `content_hash` (`subset_sampler._drawn_item`); a hand-written item carries none. `subset_sampler.content_hash` is the SHA-256 hex digest of the UTF-8 bytes of the JSON object with keys `licence`, `source`, `source_revision` and `text`, serialised with sorted keys, separators `,` and `:` and non-ASCII characters written as themselves (`ensure_ascii=False`). `licence`, `source` and `source_revision` are the benchmark's as the selection rule records them; `text` lists, in the rule's `content_fields` order, each of those fields of the source row, NFC-normalised with every whitespace run collapsed to one space and leading and trailing whitespace dropped. It hashes the source row as the loader wrote it, not the prompt the subject was sent.

## Acceptance

- Every drawn item in the quality table carries its licence, its source, that source's revision and its content hash as columns, as the rows and suite definitions record them; a hand-written item reads CC-BY 4.0 in the same column, and its content-hash cell is empty with the reason the dictionary names for it: a hand-written item carries no content hash, its text being published whole in the row and the suite definition and covered by `prompt_set_hash`. The export reads these fields and decides none of them.
- `LICENSE-DATA`'s drawn-items section lists each source the bundle draws from, its licence, which rung applies (permissive, share-alike or no redistribution), and the notices that licence requires on redistribution (CC BY 4.0: creator, copyright notice, licence link, source link and revision, and that each item was wrapped in a prompt template; Apache-2.0: a copy of the licence text beside the items and a statement of the change made), and the archive README repeats it. This section extends what orders 7 and 8 of the interval epic wrote. On the permissive rung the archive holds the Apache-2.0 text beside the drawn WMT24++ items and the CC BY 4.0 attribution elements for MInDS-14.
- Share-alike: the drawn items and their derived rows travel in the archive under their own licence file, and the tables mark which rows that file governs. Since no interval story segregates, this story fixes the layout its constructed bundles prove: the share-alike suite's definition snapshots sit at `share-alike/<licence id>/suite-definitions/`, its rows at `share-alike/<licence id>/quality-reference.jsonl`, and that licence's full text at `share-alike/<licence id>/LICENSE`, none of them in the CC-BY 4.0 `suite-definitions/` or `quality-reference.jsonl`. In the exported quality table each row derived from such an item carries the archive path of that licence file in a column of its own, `item_licence_file`; on every other row the cell is empty with its reason named in the dictionary.
- No redistribution: where the rows carry the item text redacted to its content hash, the exported row says so in a column of its own and names, per item, the source, its revision and the stable source key. Since no interval story redacts, this story fixes the redacted row's shape: its `prompt`, `expected_label` and `reference_output` (whichever the row carries) are null, and it carries `item_redaction` `no_redistribution`, `item_content_hash`, `item_source`, `item_source_revision` and `item_source_key`; every other row carries `item_redaction` `not_redacted`. In the archive's suite-definition snapshot a redacted item keeps its `item_id`, `language`, `licence`, `source`, `source_revision`, `content_hash` and stable source key and loses its text fields. No file in the archive carries a redacted item's text, the `suite-definitions/` snapshots included. The archive README states the content-hash recipe (Current state), so a reader can recompute it over the source row they fetched. The archive README carries one written instruction per such source for obtaining the text and joining it to the rows by that key; the content hash lets the reader prove a fetched item is the one that was scored. The archive ships no fetch script or other code that downloads a third party's corpus (owner answer to Q41), and the reader performs the join to the source by hand. A redacted field is never an empty cell indistinguishable from missing data, and the dictionary states that such a row's score cannot be recomputed from the download alone.
- The export dictionary's `provenance` entry names every value the exported rows carry (`hand_written`, `public`), and once a drawn item is in the bundle neither the export nor `LICENSE-DATA` states hand-written-only coverage.

## Code it changes

- The export module of order 3 (`bundle_export.py`): the licence, source, content-hash, licence-file and redaction columns and their dictionary entries, the `provenance` entry's values, and reading the share-alike paths.
- The archive assembly of order 4: the share-alike licence file and the drawn-items README section, including the per-source instruction for each no-redistribution source.
- `LICENSE-DATA`: the drawn-items section, extending what orders 7 and 8 wrote.

## Tests it needs

- Over constructed bundles, one per rung: a permissive drawn item exports its source licence, and the archive holds the Apache-2.0 text, the CC BY 4.0 attribution elements and a README repeating `LICENSE-DATA`'s drawn-items section; a share-alike set ships at its `share-alike/<licence id>/` paths under its own licence file and its rows carry `item_licence_file`; a redacted item exports the absence column, source, revision, key and hash, never an empty prompt alone, no file in the archive (the `suite-definitions/` snapshots included) carries its text, and the archive README holds one instruction for its source and the content-hash recipe, which recomputes the recorded hash from a fixture source row; the archive contains no fetch script.
- A hand-written item exports an empty content-hash cell with its named reason; every `provenance` value in the exported rows is named in the dictionary entry.

## Evidence it publishes

- The first release archive holding a drawn subset, with its drawn-items section and, if a rung requires it, one redacted row shown as it reads in the table.

## Cancellation

n/a: not cancelled.
