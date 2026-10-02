---
status: done
---

# Instruction: Holm over a closed set and the multi-member family record

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/comparison.py   ✏️ holm_adjust, build_family_record over members, counts, verdict on adjusted p, record_version 2
└── tests/test_comparison.py             ✏️ Holm published example, hand fixture, family of one, refused member
```

## User Journey

```mermaid
flowchart TD
  A[members from compare_sides] --> B[raw p per member]
  B --> C[Holm over non-null raw p]
  C --> D[adjusted p and verdict per member]
  D --> E[family record: definition, size, tested, refused, adjustment size, supersedes]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Happy path
    Holm over 0.01 0.04 0.03 0.005 => 0.03 0.06 0.06 0.02: 5: system
    three constructed members => adjusted p and verdicts from Holm, raw p beside: 5: system
  section Edge case - family of one
    one member => adjusted p equals raw p, field present: 1: system
  section Edge case - refused member
    one refused member among three => listed as refused, refused_count 1, adjustment_size 2: 1: system
```

## Tasks to do

### `1)` Holm

> An exact Holm adjustment in input order.

1. `holm_adjust(p_values)` in `Fraction`, ascending order, running max, capped at 1.

### `2)` The family record

> One record over many members.

1. `build_family_record(members, *, alpha, rows_source, supersedes=())`: canonical member order, one family definition (refuse two suites), Holm over members with a raw p, `raw_p_value`, `adjusted_p_value`, null reason `comparison_refused` for refusals, verdict re-read on the adjusted p, counts, `supersedes`, `family_id`.
2. `record_version` `"2"`.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | The published example and a hand fixture with a tie and a cap at 1 reproduce exactly. |
| 2 | A family of three has each verdict read against its adjusted p; a family of one states adjusted equal to raw; a refused member is listed, carries no p and is excluded from `adjustment_size`; two suites in one family raise. |
