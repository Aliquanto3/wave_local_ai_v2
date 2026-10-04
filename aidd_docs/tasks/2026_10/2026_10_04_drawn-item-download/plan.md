---
objective: "Every drawn item reaches the export and the release archive under its own terms: permissive items with their source, licence, revision and content hash; share-alike items and rows under share-alike/<licence id>/ with their licence file named per row; no-redistribution items as a marked, hash-keyed absence the README tells a reader how to fill by hand; and LICENSE-DATA section 2, repeated in the archive README, names every drawn source and its rung."
status: implemented
---

# Plan: A drawn item reaches the download under its own terms, or as a visible hole

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Item-terms columns and checks in `bundle_export.py`, the share-alike area read as bundle parts, the rung rules in `LICENSE-DATA` section 2, and an archive that repeats that section, lays out share-alike sets, states the content-hash recipe and per-source join instructions, and refuses a drawn source LICENSE-DATA does not name at the rung its layout shows |
| **Source** | `aidd_docs/backlog/stories/a-drawn-item-reaches-the-download-under-its-own-terms-or-as-a-visible-hole.md` |

## Phases

| #   | Phase                                                                 | File                         |
| --- | --------------------------------------------------------------------- | ---------------------------- |
| 1   | The export: item-terms columns, the share-alike area, redaction checks | [`phase-1.md`](./phase-1.md) |
| 2   | LICENSE-DATA's rung rules and the archive: layout, README, gates, evidence | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The share-alike area sits at `aidd_docs/results/share-alike/<licence id>/` in the repository and the archive, beside `suite-definitions/` and `quality-reference.jsonl`. | The acceptance places `share-alike/<licence id>/...` against the CC-BY 4.0 `suite-definitions/` and `quality-reference.jsonl`, which live in the results directory; the archive ships bundle parts at their repository paths, so `bundle_manifest.csv` and `item_licence_file` resolve inside it unchanged. |
| The four new quality-table columns (`item_content_hash`, `item_source_key`, `item_redaction`, `item_licence_file`) come from one export-side "item terms" source read from the row, then the item its suite definition holds (joined by `item_id`); the row's own copies of those three fields are excluded from the row source. | A redacted row carries `item_content_hash`, `item_source_key` and `item_redaction` itself while permissive rows do not; one source avoids a duplicate column, and a row and its definition disagreeing is refused rather than one chosen. |
| A row with no `item_redaction` field exports `not_redacted`. | Every published row predates the field and carries its item text; the acceptance asks that every non-redacted row read `not_redacted`, and an empty cell there would be the indistinguishable absence the story forbids. |
| A row's item text fields are `prompt`, `prompt_before_template`, `expected_label` and `reference_output`; a redacted row records each it carries as null. A redacted snapshot item keeps only `item_id`, `language`, `licence`, `source`, `source_revision`, `content_hash`, `source_key`, `redaction` and the non-text `provenance`, `contamination_risk`, `target_language`, `domain`. | The acceptance names three fields, but `prompt_before_template` carries the same text and "no file carries a redacted item's text" would fail without it. An allow-list on the snapshot item refuses any text field not foreseen. |
| The stable source key is stored as `source_key` on a redacted item and `item_source_key` on its row; the selection rule's `stable_source_key` names which source field it is. | Today's items carry the key only inside `item_id` (`<source>:<key>`); the acceptance asks the redacted item to keep it as its own value. |
| The rung of each drawn source is read from the bundle layout (a share-alike set, or redacted items) and checked against the `- Rung:` line of the LICENSE-DATA section 2 subsection naming it in `- Source:`; the archive refuses a source with no subsection or a disagreeing rung, and a source with redacted and unredacted items. | "Lists each source the bundle draws from ... which rung applies" then holds by construction for every release, not only today's two sources. |
| The archive README repeats LICENSE-DATA section 2 verbatim (its body below the heading), then lists each share-alike set and one join instruction per no-redistribution source, built from the suite's selection rule. The three clone-only paths section 2 names gain `README.md` in their reviewed `named_by`. | A verbatim copy cannot drift; the README already links each of those paths at the commit. |
| The archive refuses any entry with a code suffix (`.py`, `.sh`, `.ps1`, `.bat`, `.cmd`, `.js`, `.ipynb`, `.exe`). | Owner answer to Q41: the archive ships no fetch script; a gate keeps it true. |
| The constructed bundles are built in a temporary repository root from a handful of committed rows (one hand-written, MInDS-14 and WMT24++ rows relabelled to fictional `example/...` sources for share-alike and no-redistribution), with `head_commit` stubbed. | Both live sources are permissive (Q105, Q106); a tiny bundle keeps three archive builds fast while running the real build and verify path. |

## Evidence

| What | Where |
| ---- | ----- |
| Local archive build of the working tree at `HEAD` for `v0.2.0` into a temp dir: listing, verify output, the drawn-items section and the four new columns on drawn rows | [`evidence/local-build.txt`](./evidence/local-build.txt), [`evidence/archive-README-drawn-items.md`](./evidence/archive-README-drawn-items.md) |
| One redacted row as it reads in the quality table, from the constructed no-redistribution bundle | [`evidence/redacted-row.txt`](./evidence/redacted-row.txt) |
| Pending (owner): the first `v*` tag and its Release asset | story "Evidence it publishes" |
