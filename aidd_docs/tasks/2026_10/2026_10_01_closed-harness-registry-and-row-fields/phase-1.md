---
status: done
---

# Instruction: Registry, overhead rule and the schema "20" writer gate

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/
│   ├── harness.py          ✅ the closed registry, version read, overhead rule
│   └── row_contract.py     ✏️ "20": three required quality fields and their refusals
└── tests/
    ├── test_harness.py     ✅ registry, version read, overhead rule
    ├── test_row_contract.py ✏️ the three fields, the refusals, a `direct` fixture row
    └── store_fixtures.py   ✏️ named values for the three fields
```

## User Journey

```mermaid
flowchart TD
  A[Writer builds a quality row] --> B[harness.row_fields reads the version now]
  B --> C[harness.prompt_overhead applies the rule]
  C --> D{validate_row}
  D -->|id in the five, version a string, overhead well formed| E[row appended]
  D -->|otherwise| F[RowContractError naming the field]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    A complete schema 20 direct quality row => fixture ready: 5: system
  section Happy path
    Validate the direct row => accepted with id, version, overhead tokens: 5: system
  section Edge case - harness outside the five
    harness_id crewai => validate => refused naming harness_id: 1: system
  section Edge case - overhead absent
    row without harness_prompt_overhead => validate => refused by name: 1: system
  section Edge case - unmeasurable fixture harness
    a harness that rewrites the prompt => overhead rule => null with unmeasurable, never 0: 1: system
  section Edge case - earlier row
    schema 19 row without the three fields => validate => accepted: 1: system
```

## Tasks to do

### `1)` The registry and the rule

> One module owns the five ids, their packages and the overhead subtraction.

1. `harness.py`: ids, `HARNESS_DISTRIBUTIONS`, `HARNESS_IDS`, `harness_version(id)` via `importlib.metadata` refusing an unknown id or an uninstalled package.
2. `PromptOverhead` (`tokens`, `null_reason`), its closed reasons, `prompt_overhead(...)` and `row_fields(id, overhead)`.

### `2)` The gate

> `validate_row` owes and checks the three fields from "20".

1. Bump `SCHEMA_VERSION` to "20", add `HARNESS_FIELDS`, `HARNESS_SCHEMA_VERSION`, required on quality rows; exempt rows below "20".
2. `_validate_harness`: id in the five, version a non-empty string, overhead a two-key object, tokens a non-negative int with null reason, or null with a known reason.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | `direct`'s version equals the installed `requests` version at call time; an unknown id or a missing package is refused; tools counted in the item leave a zero overhead; a rewriting harness yields `unmeasurable` |
| 2 | A row naming a harness outside the five, or lacking the overhead, is refused by name; a schema "19" row without the fields validates; a `direct` fixture row carrying all three validates |
