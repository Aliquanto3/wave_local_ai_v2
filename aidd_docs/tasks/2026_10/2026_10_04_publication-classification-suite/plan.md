---
objective: "A 300-item publication-level classification suite drawn from MInDS-14 by the recorded sampler rule stands beside the hand-written 20-item suite, scored against its own label set, licensed and attributed on the permissive rung, and published in the reference bundle with one development-level batch of the hand-written suite on the same subject in the same session."
status: implemented
---

# Plan: A publication-level classification suite stands beside the hand-written one

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | The MInDS-14 loader (locked `loaders` group), the drawn suite definition with its source-table hash, the exact-label scorer taking its label set from the suite, the licence/NOTICE/coverage/export edits, then two published batches on one subject |
| **Source** | `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md` (owner answers Q105 (a), Q120 (a), Q130 (a), Q131 (a), Q132 (a), Q134 (a), Q135 (a)) |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The scorer takes its label set from the suite and matches multi-word labels | [`phase-1.md`](./phase-1.md) |
| 2   | The loader, the drawn suite, its snapshot, the export columns and the dependency group | [`phase-2.md`](./phase-2.md) |
| 3   | Licence, NOTICE, coverage record and README statement of the rung | [`phase-3.md`](./phase-3.md) |
| 4   | Stage B: the two published batches, promotion, merge and evidence | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| https://huggingface.co/api/datasets/PolyAI/minds14/tree/40ce77cb32a384e4d50a568e1ec39ac804019d33?recursive=true | The pinned revision holds `.gitattributes`, `README.md` and one parquet per locale (`<locale>/train-00000-of-00001.parquet`, LFS SHA-256 listed); no licence file at the root |

## Decisions

| Decision | Why |
| -------- | --- |
| The label set is derived from all of the suite's items' `expected_label` values (`SuiteDefinition.labels`) and passed to every scoring rule as the keyword `labels`; no `labels` key is declared in any definition. | The acceptance allows "declared, or derived from all of the suite's items"; deriving needs no new definition key, so the hand-written suite's definition and snapshot stay byte-identical (its 20 items hold all four labels, so the derived set equals `classification_suite.LABELS`). A resumed batch scores through the same property, never its subset. |
| `normalize_label` matches a label as its run of `_`-separated words over the existing `[a-z]+` tokens, longest label first at each position, first position wins. | A one-word label set behaves exactly as before (same first-matching-token rule), so the hand-written suite and the judge's categorical parse do not move; `app_error`, `app error` and `App-Error` all name `app_error`. |
| One script, `scripts/minds14_suite.py`, with `fetch` (download the three parquet files at the pinned revision, verify each against its LFS SHA-256, write the JSONL source table, report its SHA-256 and whether a licence file ships), `draw` (sampler draw into the suite definition) and `verify` (operator replay: re-fetch, check the hash, replay). pyarrow sits in a new locked `loaders` group, run with `uv run --group loaders`. | Q135 (a): the loader is a script under `scripts/`, never a runtime dependency. The audit already exports `--all-groups`, so the new group is audited with no audit change; a test pins that. |
| Source table rows are written sorted by `path`, compact sorted-key JSON, UTF-8, `\n` line ends. | The table's SHA-256 is recorded in the definition (Q132 (a)) and must be reproducible by an operator on any OS. |
| The definition's `extra` gains `source_table` {`sha256`, `row_count`, `loader_script`, `licence_file_at_revision`, `licence_of_record`}; `bundle_export.SUITE_DEFINITION_FIELDS` documents it with `size_target`, `size_target_reason` and every `selection_rule` leaf. | The export refuses an undocumented key; one block keeps the source facts together. |
