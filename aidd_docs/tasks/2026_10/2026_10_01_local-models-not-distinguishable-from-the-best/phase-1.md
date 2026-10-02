---
status: done
---

# Instruction: The leader-set derivation and its record

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/leader_set.py   ✅ subjects, machine class, groups, reference + tie rule, needed comparisons, record build, id, heads
└── tests/test_leader_set.py             ✅ constructed groups
```

## User Journey

```mermaid
flowchart TD
  A[published quality rows + fiches] --> B[local subjects grouped by suite and machine class]
  B --> C[best subject by suite score, tie rule]
  C --> D[comparisons reference vs every other subject]
  D --> E[family record verdicts => member / excluded / not compared]
  E --> F[one leader-set record per group]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    constructed rows and fiches in tmp dirs => three local subjects, one cloud subject: 5: system
  section Happy path
    derive over the group => two members, one excluded, cloud never listed: 5: system
  section Edge case - refused comparison
    one subject refused on a constraint => derive => not compared naming the field, record incomplete: 1: system
  section Edge case - tie at the top
    two subjects share the top score => derive => the stated rule names the reference: 1: system
  section Edge case - one local subject
    a group of one => derive => a set of one, no comparison ran: 1: system
  section Edge case - gpu and cpu_only
    one model, two fiches differing on compute_mode => derive => two groups: 1: system
```

## Tasks to do

### `1)` Module

> Pure derivation, no I/O beyond reading fiches through `fiche_registry.read_fiche`.

1. Subjects (`run_id`, `model_id`) from local rows; suite score per subject.
2. Machine class from the fiche; groups keyed by suite id, version and class.
3. Reference and tie rule; the leader comparisons a group needs.
4. Record from a group and its family record; id, supersedes, heads, same-content.

### `2)` Tests

> Every constructed group of the story.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | A group's record names suite, level, grouping fields and values, reference, tie rule, family id, and each subject's run id and status. |
| 2 | The six constructed cases of the story pass. |
