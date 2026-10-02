---
status: done
---

# Instruction: Sides, pairing, refusal list, differing-field set and the family-of-one record

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/comparison.py     ✏️ select_side, compare_sides, build_family_record
└── tests/test_comparison.py               ✏️ routing, refusals, unpaired items, confound
```

## User Journey

```mermaid
flowchart TD
  A[rows + reference side + candidate side] --> B[select each side by run_id and selector fields]
  B --> C{refusal fields}
  C -->|differ or absent| R[refusal record, verdict not comparable]
  C -->|all match| D[pair on item_id, count one-sided items per side]
  D --> E[test by scoring kind]
  E --> F{differing fields vs dimension}
  F -->|inside dimension| T[test record]
  F -->|confound| O[observation record]
  T --> G[family of one, adjusted p = raw p]
  O --> G
  R --> G
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    constructed schema-15 rows for two models => two sides: 5: system
  section Happy path
    classification sides => compare => McNemar record without the caller choosing: 5: system
    translation sides => compare => Wilcoxon record without the caller choosing: 5: system
  section Edge case - refusals
    bumped suite_version => compare => refusal naming suite_version: 1: system
    differing max_output_tokens => compare => refusal naming max_output_tokens: 1: system
    differing thinking_policy => compare => refusal naming thinking_policy: 1: system
    differing metric_version on graded rows => compare => refusal naming metric_version: 1: system
    graded against binary => compare => refusal naming scoring_kind: 1: system
    thinking_policy missing on both => compare => refusal naming it absent: 1: system
  section Edge case - partial and confounded
    item missing on the candidate => compare => paired n shrinks, item named to candidate: 1: system
    gpu against cpu_only of one model => compare => observation naming compute_mode: 1: system
```

## Tasks to do

### `1)` Sides and pairing

1. A side is a run id plus selector fields; rows matching both are the side.
2. Pair on `item_id`; a null compared value counts as missing from that side.

### `2)` Refusals and differing fields

1. Refusal list per the plan's Decisions, each entry naming field, reason (`differs`/`absent`) and both values.
2. Differing set over non-excluded fields; comparison kind from the declared dimension.

### `3)` Record

1. Member record with every field the acceptance names; family of one with `family_id`.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | A side missing an item reduces paired n and names the item with `missing_from` |
| 2 | Each refusal case names its own field; a gpu/cpu_only pair is an observation whose differing set holds `compute_mode` |
| 3 | A family of one states adjusted p equal to raw p; the same inputs give a byte-identical record |
