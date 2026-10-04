---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: `--prompt-variant` on the quality CLI and the story's tests

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/
│   └── quality_cli.py        ✏️ --prompt-variant ID[@VERSION]
└── tests/
    ├── test_quality_cli.py   ✏️ flag, invariance across variants, no-op rows keep items
    ├── test_scoring_rules.py ✏️ unparseable terse answer scores 0 and stays counted
    └── test_comparison.py    ✏️ constructed pair differs only on the variant fields
```

## User Journey

```mermaid
flowchart TD
  A[--prompt-variant output_compressed] --> B[resolve in registry or refuse]
  B --> C[campaign check, run every item]
  C --> D[rows: same caps, scorer, items; prompt differs]
  D --> E[wave-local-ai-v2-compare --dimension prompt_variant]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    stub local client and server => a suite runs without a model: 5: system
  section Happy path
    run baseline then output_compressed => rows differ only in prompt and variant fields, item ids equal: 5: cli
  section Edge case - unknown variant
    unregistered id => run => refused naming it, exit 1: 1: cli
  section Edge case - unparseable terse answer
    terse output the parser cannot read => score => correct false, failure_reason unparseable, counted: 1: system
```

## Tasks to do

### `1)` Flag

1. Parse `--prompt-variant` (`ID` or `ID@VERSION`), resolve through the registry before settings; unknown refused through `main`'s error tuple.

### `2)` Tests

1. Invariance over every registered suite: every row field outside the prompt/variant/per-item outcome set is equal across the two variants, and item ids are equal.
2. Unparseable terse output scores 0 with its reason and stays in the denominator.
3. Constructed pair through `comparison`: differing fields exactly `{prompt_variant_id, prompt_variant_version}`, no observation.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | `--prompt-variant output_compressed` writes rows naming it; an unregistered id exits 1 before any process |
| 2 | The three story tests pass under `uv run pytest` |
