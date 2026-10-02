---
objective: "The export writes a fifth flat table, comparison_records.csv, holding every comparison-family record, each comparison it holds, and every leader-set record with its subjects, as values the records already carry, every column in the column dictionary, and the record kinds a bundle does not hold named as not carried."
status: implemented
---

# Plan: Comparison, family and leader-set records read as a fifth table

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `wave-local-ai-v2-export` reads `comparisons/` and `leader-sets/` beside the five bundle parts and writes `comparison_records.csv`, documented in `column_dictionary.csv` and counted in `bundle_manifest.csv` |
| **Source** | `aidd_docs/backlog/stories/comparison-family-and-leader-set-records-read-as-a-fifth-table.md` (on branch `docs/slice-remaining-epics`); owner answers Q2 and Q42 (a) |

## Phases

| #   | Phase                                                         | File                         |
| --- | ------------------------------------------------------------- | ---------------------------- |
| 1   | Fifth table, its registries, its reading and its tests        | [`phase-1.md`](./phase-1.md) |
| 2   | Run over the committed bundle, README and memory              | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| One table, `comparison_records`, with four row kinds named in its first column `record_kind`: `comparison_family` (one per family record), `comparison` (one per member of a family record), `leader_set` (one per leader-set record) and `leader_set_subject` (one per subject a leader-set record lists). `record_file` names the record's file. | The acceptance asks for one row per comparison with its family, plus the family and leader-set records, and a column telling the kind. A leader set's subjects are rows for the same reason a family's members are: their status, verdict and not-compared reason are what a reader checks, and a JSON cell would need parsing. |
| Every row has the same five sources: the row's key (`record_kind`, `record_file`), the family record without `members` (`family_*`), the comparison (`comparison_*`), the leader-set record without `subjects` (`leader_set_*`), the subject (`subject_*`). A comparison row carries its family's columns; a subject row carries its leader set's columns. A source that is not that row's kind is "not carried" and listed in `fields_not_carried`. | Reuses `build_table` unchanged: one fixed source layout per table, prefixes keep the four record kinds' same-named fields (`suite_id`, `alpha`, `verdict`, `adjusted_p_value`) in separate columns, and "with the family it belongs to" holds on the comparison row itself, the way the quality table carries its fiche. |
| Lists (`supersedes`, `refusal`, `differing_fields`, `confounds`, `paired_values`, `paired_item_ids`, `unpaired_items`, `grouping_fields`, `tied_at_top`, `refused_fields`) are compact JSON cells, verbatim; dicts (`family_definition`, `multiplicity_correction`, `result`, `batch_values`, selectors, `grouping_values`, `reference`) are named sub-columns. | The order-3 rule for lists and dicts. `supersedes` stays as the record wrote it: the superseding family row's `family_supersedes` cell names the old `family_id`, and the old record stays its own row, so the link is read, not computed. |
| No `superseded_by` column. | Inverting the supersede link is a derivation; the acceptance asks the link to be readable, and it is, from the superseding row. |
| Record pointers are checked, not joined: every `reference_run_id`, `candidate_run_id` and subject `run_id` must be a `run_id` of the quality rows read; a leader set's `family_id` and every `supersedes` id must name a record of its kind the bundle holds. Otherwise the export refuses, naming the record. | Order 3 refuses an unresolved pointer; a record citing a run or record the download does not ship would publish a dangling claim. |
| `comparisons_dir` and `leader_sets_dir` are bundle parts (`BundlePaths`, `--comparisons-dir`, `--leader-sets-dir`, defaults the committed directories). A missing directory, like an empty one, is a bundle holding none of that kind (header-only table, kinds named not carried, manifest path with 0 entries); a path that is not a directory, a `.json` file that is not a JSON object of that directory's `record_type`, or a malformed `members` / `subjects` / `supersedes` / id refuses, naming the record. (Review round 1, blocking 1: a missing directory first refused.) | The acceptance treats the record kinds as optional parts of a bundle; nothing present is silently dropped. |
| Record kinds the bundle read does not hold are `carried=false` dictionary entries of `comparison_records`, owner the statistics epic; the old "comparison and family records" owned-elsewhere entry is removed, since the table now exists. The table with no records is written as its header (`fields_not_carried` alone, as the four tables do when empty). | Acceptance 5; same empty-table convention as order 3. |
| Columns read from the records name, in the dictionary's `owner` cell, the statistics epic as the owner of their definition; meanings here are short descriptions of what the record field holds, not definitions. | Q2 (a): the meaning, unit and null reasons of the statistical columns are supplied by `the-tabular-export-carries-the-interval-and-the-comparison-record` and not redefined here; the owner cell makes the hand-off readable until it lands. |
| The manifest gains `comparison_families` and `leader_sets` parts with their `record_version` values. | The manifest states what was read, per part. |
| The task's evidence summarises the table with 12-character id prefixes, not the CSV itself. | 64-hex ids inside quoted JSON cells are flagged by detect-secrets; the README and evidence name the command that regenerates the table. |
