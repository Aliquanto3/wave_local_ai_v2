---
objective: "The tabular export carries every interval column and every comparison, family and leader-set record column under definitions the statistics epic supplies, shows a pre-interval row as documented empty cells, and a reader recomputes a published interval and a published McNemar comparison from the exported tables alone."
status: implemented
---

# Plan: The tabular export carries the interval and the comparison record

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Record column definitions move out of `bundle_export` into the modules that write the records, the interval columns' empty cells and owner are made true, and a standalone stdlib reader recomputes an interval and a McNemar comparison from the exported CSVs |
| **Source** | `aidd_docs/backlog/stories/the-tabular-export-carries-the-interval-and-the-comparison-record.md` (PR-head text on `docs/slice-remaining-epics`); owner answers Q2 (a) and Q42 (a) |

## Phases

| #   | Phase                                                         | File                         |
| --- | ------------------------------------------------------------- | ---------------------------- |
| 1   | Record column definitions supplied by the statistics modules  | [`phase-1.md`](./phase-1.md) |
| 2   | Interval columns: empty cells, owner, agreement with the block | [`phase-2.md`](./phase-2.md) |
| 3   | Recomputation from the exported tables alone, and its evidence | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| What the dependencies already met: the interval block columns and their dictionary entries (`1cfe5a7`), the fifth table and its four record kinds (`e3858a8`). What was left: the record definitions lived in `bundle_export` (redefined there, the owner cell only naming the epic), the dictionary still listed the interval block as "not in the bundle read" even when the rows carry it, a row predating schema 21 had no tested empty-cell meaning, and no recomputation from the exported tables existed. | The story is not fully met by the dependencies; this plan does only the remainder. |
| The field-description type moves to a small shared module (`field_doc.py`); `comparison.py` defines the family-record and comparison fields, `leader_set.py` the leader-set and subject fields; `bundle_export` reads those registries and defines none of them. | Q2 (a): the statistics epic supplies the definitions, the export never redefines them. A shared type avoids an import cycle (`bundle_export` imports both modules). Leader-set records (order 10) follow the same split under Q42 (a), so the owner cell is true for every record column. |
| A record field's definition states what a null means for that field; the export adds what an empty cell means for a row of another kind. The dictionary's `empty_cell` is the two joined. | The null reasons are the record's semantics; "not this row's kind" is the table's. One cell states both without either module knowing the other's half. |
| The stale `interval block` owned-elsewhere entry is removed, with the now-empty owned-elsewhere mechanism; `score_interval`, when no row read carries it, is named not carried like any contract field, with the statistics epic as its owner. | The block exists (schema 21); a dictionary saying it is not in the bundle while columns carry it would be false. |
| The recomputation reader is `scripts/recompute_from_export.py`: standard library only, imports nothing from the package, reads only the exported CSVs, reimplements the draw procedure from its published definition and McNemar's exact test and Holm from their formulas. | "From the exported tables alone": a reader that called `score_interval.replay` would prove the code agrees with itself, not that the published definition is enough. One file serves the test and the evidence. |
| The evidence runs over a bundle built from the committed rows by the writers' own code (the interval block from `score_interval.interval_block`, the family record from `comparison`), exported by the real command into a temp dir; the committed bundle is never edited. | The committed bundle publishes neither an interval (rows at schema 7) nor a tested comparison (all four family records are refusals on `thinking_policy`), so no published value there can be recomputed. Recorded as such in the results README. |
