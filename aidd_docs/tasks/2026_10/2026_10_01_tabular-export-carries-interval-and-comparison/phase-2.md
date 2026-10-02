---
status: done
---

# Instruction: Interval columns: empty cells, owner, agreement with the block

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/bundle_export.py  ✏️ interval empty-cell meaning; owned-elsewhere entry and mechanism removed; score_interval owner
└── tests/test_bundle_export.py            ✏️ pre-21 row exports empty cells listed not carried; dictionary agrees with score_interval
```

## User Journey

```mermaid
flowchart TD
  A[Bundle: a schema-21 row, a partial row, a pre-21 row] --> B[Export]
  B --> C[Interval columns: values / empty null / empty not carried]
  C --> D[Dictionary states each empty meaning, owner the statistics epic]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    Committed rows, one given an interval block, one a null block, one left without => constructed bundle: 5: system
  section Happy path
    Export => every interval column present and documented: 5: system
    The row without the block => empty interval cells, all listed in fields_not_carried, never 0: 5: system
  section Edge case - no row carries the block
    Committed bundle => export => score_interval named not carried, owner the statistics epic, no interval block entry: 5: system
  section Edge case - definition drift
    Dictionary interval entries => compared with score_interval constants and keys => each key described, each reason named: 5: system
```

## Tasks to do

### `1)` Empty-cell meaning

1. `_INTERVAL_EMPTY` and the `null_reason` empty text: a row written before schema 21 does not carry the block (listed in `fields_not_carried`); a partial or judge-probe row records null; never zero, never back-filled.

### `2)` Owner and stale entry

1. Remove `OwnedElsewhere`, `NOT_CARRIED_ELSEWHERE` and their loop.
2. `_not_carried_by_contract` names the statistics epic as owner of `score_interval`.

### `3)` Agreement with the block

1. Interval texts read the constants (`CONFIDENCE_LEVEL`, `RESAMPLES`, `METHOD_PERCENTILE`, null reasons).
2. Test: every key of `score_interval`'s header, generator and cell sets has a dictionary entry; each null reason is named.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1    | A pre-21 row's interval cells are empty and listed not carried; its dictionary meaning says so |
| 2    | No dictionary entry says the interval block is absent when a row carries it; when none does, `score_interval` is named with the statistics epic |
| 3    | A key added to the block without a dictionary entry fails a test |
