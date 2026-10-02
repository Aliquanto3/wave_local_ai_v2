---
status: done
---

# Instruction: The analysis command, one family per invocation, supersede by id

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/comparison.py   ✏️ --comparisons, --records-dir, head lookup, re-emit identical record
└── tests/test_comparison.py             ✏️ eleven grown to twelve, re-run identical, refusals of the invocation
```

## User Journey

```mermaid
flowchart TD
  A[wave-local-ai-v2-compare --comparisons decl.json] --> B[compare every declared pair]
  B --> C[read family records in records dir]
  C --> D{same definition, same content?}
  D -->|yes| E[re-emit that record unchanged]
  D -->|no| F[supersedes = heads of the definition]
  F --> G[write new record; old files untouched]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    constructed rows of twelve candidates against one reference => rows file: 5: system
  section Happy path
    run with eleven comparisons then twelve => second record supersedes the first by id, first file byte-identical: 5: cli
  section Edge case - re-run
    same bundle and definition run again => identical record, nothing new written: 1: cli
  section Edge case - two suites
    declared comparisons span two suites => exit 1, nothing written: 1: cli
  section Edge case - malformed declaration
    duplicate, wrong shape, or both flag forms => exit 1 naming the problem: 1: cli
```

## Tasks to do

### `1)` Declared comparisons

> Many pairs in one invocation.

1. `--comparisons <json>` parsed into `Side` pairs; mutually exclusive with the single-pair flags.

### `2)` Supersede by id

> The current head of the definition is superseded, never edited.

1. `--records-dir` (default `COMPARISONS_DIR`) read for family records; content match re-emits; else `supersedes` = heads.
2. Default output under the records dir.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | Twelve declared comparisons produce one record of twelve members; a malformed declaration exits 1 with nothing written. |
| 2 | Growing eleven to twelve writes a second file naming the first id in `supersedes`, the first file byte-identical; a re-run writes nothing new and returns the same bytes. |
