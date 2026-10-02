---
objective: "A suite declares its level and the gate certifies it there or refuses it naming the shortfall, every hand-written item names its CC-BY 4.0 licence in data without moving its prompt-set hash, and every quality row names its certified level and its item's licence, source and source revision."
status: implemented
---

# Plan: A suite is certified to its declared level, and every item names its licence and source

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A second, `publication`, level in the suite gate (100-item floor, declared 100/300 size target, per-item licence + source + revision), the certified level on every quality row (schema "15"), and the hand-written items' CC-BY 4.0 licence declared in the suite data |
| **Source** | `aidd_docs/backlog/stories/a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source.md` (owner answers Q1 (a), Q70 (a)) |

## Phases

| #   | Phase                                                                 | File                          |
| --- | --------------------------------------------------------------------- | ----------------------------- |
| 1   | The two-level gate, the declarations in the suite data, the version bump and write-once snapshots | [`phase-1.md`](./phase-1.md) |
| 2   | The level and the item licence/source on every quality row, the view partition, the export dictionary, docs and evidence | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The level and the per-item licence live in `suite_data/*.json`, not in `classification_suite.py`/`translation_suite.py` as the story's "Code it changes" says. Those modules keep only the rationale, which gains the reason for the new declarations. | The dependency story (Q1 (a), Q70 (a)) moved every item into data before this story; no acceptance line requires a Python literal. File-location drift only. |
| `level` becomes a core, required suite key (`development` or `publication`) held on `SuiteDefinition.level` and exported in the snapshot; `size_target` (100 or 300) and `size_target_reason` are optional top-level keys, validated by the gate and carried in `extra`. Item keys `licence`, `source`, `source_revision` are validated as non-empty strings wherever declared, and required on every item at `publication`. | "A suite declares its level": required, not defaulted. The orchestrator's note: unknown keys are carried unchecked, so every key this story adds is validated. |
| A publication suite that falls short is refused (`SuiteGateError` naming every shortfall: count, target, language share, items missing a licence/source/revision); a passing one returns `level: "publication"`. A development suite keeps today's indicative-not-refused behaviour and returns `level: "development"`. `gate_suite(items)` with no level keeps today's behaviour, so `judge_probe` is unchanged in kind. | "Fails loudly instead of passing quietly at the lower level": a refusal at load means no definition, hence no row, can exist; an `indicative` flag would be exactly the quiet pass the story forbids. |
| A `size_target` on a `development` suite is refused. The publication count check is `item_count >= max(100, size_target)`. | The PRD's target is a publication notion; a development suite declaring one is a confused declaration. The 100 floor holds whatever the target. |
| Both shipped suites bump their version: classification `"3"` -> `"4"`, translation `"2"` -> `"3"`, with new snapshot files beside the untouched `@3`/`@2` ones. Prompt-set hashes do not move. | The codebase's own rule (`test_every_committed_definition_equals_its_export_byte_for_byte`): a snapshot's content cannot change under an unchanged version, and the story forbids overwriting a published snapshot. Cost: rows a future run writes at `@4`/`@3` are `not_comparable` (verdict keys on `suite_version`) to the published `@3`/`@2` reference rows, although the subject is sent identical text. |
| `suite_snapshot.main` refuses to overwrite an existing snapshot whose bytes differ (exit 1, naming the file, writing nothing); an identical re-export is a no-op. | Makes "an already-published snapshot file is never overwritten" enforced rather than conventional. |
| Row fields: `suite_level`, `item_licence`, `item_source`, `item_source_revision`, required on every quality row; schema `"15"`. Hand-written rows carry `item_source`/`item_source_revision` as `null` (nothing was drawn). The contract refuses an unknown level and a `publication` row with any of the three item fields null. | The item key `source` would read as "source text" beside translation's `source_text` on a row; the `item_` prefix keeps it unambiguous. A null is a recorded fact (`null_in_row`), not an invented provenance. |
| One helper, `quality_rows.suite_item_fields(gate_result, item)`, builds the four fields for both writers (`quality_cli`, `judge_probe`). The judge probe's hand-written items declare `licence` CC-BY-4.0 too. | Same anti-parallel reason as the module's existing batch-field helpers. The probe's items are the repo's hand-written items under the same licence; its prompt-set hash covers prompts only. |
| `bundle_export` gains dictionary entries for the four fields and drops the `item licence and source` owned-elsewhere block; the README's dictionary paragraph follows. | The dictionary refuses an undescribed contract field; keeping the owned-elsewhere entry would declare the same thing twice under two owners. |
