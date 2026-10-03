---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Per-item cloud verdict, verdict fields (schema "29"), CLI wiring, export docs

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/
│   ├── verdict.py         ✏️ provider/tolerance/rerun_blocker, the four new block keys
│   ├── row_contract.py    ✏️ SCHEMA_VERSION "29", verdict block check on quality rows
│   ├── quality_cli.py     ✏️ pass provider, tolerance, no_seed blocker; model_not_served stderr mark
│   └── bundle_export.py   ✏️ FieldDocs for the new verdict columns
├── aidd_docs/memory/cli.md   ✏️ verdict block description
└── tests/
    ├── test_verdict.py       ✏️ cloud within/beyond, single-run indicative, local, all-null
    ├── test_row_contract.py  ✏️ missing fields refused, local row validates
    └── test_quality_cli.py   ✏️ verdict wiring
```

## User Journey

```mermaid
flowchart TD
  A[batch rows + reference rows] --> B{rerun_blocker?}
  B -->|yes| C[not_comparable + single_run_indicative]
  B -->|no| D{matching reference, same items, comparable field?}
  D -->|no| E[not_comparable, existing triggers]
  D -->|yes| F{provider local?}
  F -->|yes| G[identical or not_reproduced]
  F -->|no| H[divergence <= tolerance: reproduced else not_reproduced, items named]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    constructed candidate and reference rows => batches ready: 5: system
  section Happy path
    cloud batch with 1 of 20 diverging under 0.10 => quality_verdict => reproduced naming the item and the tolerance: 5: system
  section Edge case - beyond tolerance
    cloud batch with 3 of 20 diverging => quality_verdict => not_reproduced naming the items: 1: system
  section Edge case - model not served
    rerun_blocker model_not_served => quality_verdict => not_comparable, single_run_indicative named: 1: system
  section Edge case - local
    local batch with 1 diverging item => quality_verdict => not_reproduced, tolerance null: 1: system
  section Edge case - all null cloud
    cloud batch with null labels and scores => quality_verdict => not_comparable: 1: system
  section Edge case - row contract
    schema 29 quality row without the new verdict keys => validate => refused: 1: system
```

## Tasks to do

### `1)` Verdict rule

1. `quality_verdict(candidate, reference, *, provider, tolerance, rerun_blocker=None)`; new keys on every returned block; local + blocker refused.

### `2)` Row contract

1. `SCHEMA_VERSION = "29"` with its comment; `VERDICT_TOLERANCE_SCHEMA_VERSION`; quality rows from "29" carry the four keys, shapes checked, cloud tolerance names the row's suite, single-run indicative never `not_reproduced`.

### `3)` CLI and export

1. `_score_and_write` passes `provider`, `spec.divergence_tolerance` + suite identity, and `no_seed` when the sampling carries no seed; `_try_run_cloud_provider` prints the `model_not_served` mark on a `ModelUnavailableError` pre-flight.
2. `bundle_export.py` FieldDocs; `cli.md` memory line.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Each story test case returns the stated verdict and names items, rule, tolerance and suite version |
| 2 | A "29" quality row missing a verdict key is refused; a deterministic local row validates; "28" rows still validate |
| 3 | A CLI run writes rows whose verdict block names the provider's rule and the suite's tolerance |
