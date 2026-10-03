---
status: done
---

# Instruction: The record format, its check, its refusals and its command

## Architecture projection

```txt
.
├── pyproject.toml                               ✏️ wave-local-ai-v2-client-sessions script
├── src/wave_local_ai_v2/client_sessions.py      ✏️ format, check_records, render, main
└── tests/test_client_sessions.py                ✏️ one planted file per refusal
```

## User Journey

```mermaid
flowchart TD
  A[client-sessions.jsonl] --> B[parse each line]
  B --> C{identity field absent / bad enum / bad id / bad release / dates / duplicates / corrects}
  C -->|any| D[refusal: line N field reason, exit 1]
  C -->|none| E{content field absent or empty}
  E -->|yes| F[reported incomplete, exit 0]
  E -->|no| G[read back complete, exit 0]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    write a planted record file and a changelog => files ready: 5: system
  section Happy path
    well-formed file => check => no refusal, records read back with markings: 5: cli
  section Edge case - refusals
    each planted defect => check => refusal naming line and field, exit 1: 1: cli
  section Edge case - incomplete
    content field left out => check => reported incomplete, exit 0: 1: cli
  section Edge case - secrets
    well-formed dated and unreleased records => secrets scan => nothing found: 1: system
```

## Tasks to do

### `1)` Format and check

1. Field tables (required, content, optional, enums, id patterns).
2. `check_records(text, changelog_text, commit_exists)` returns records, refusals, incomplete.
3. Refusals: unparsable line, absent required field, enum outside set, wrong type, unknown key, id pattern, duplicate session id, `corrects` naming no earlier record or a second correction, release neither dated heading nor unreleased with existing commit, session before release date, logged before session, outcome/challenge mismatch, empty claims.

### `2)` Command

1. `main(argv)`: `--sessions`, `--changelog`; renders records, incomplete, refusals; exit 0/1/2.
2. `[project.scripts]` entry.

### `3)` Committed-record and secrets tests

1. The committed file passes; a planted malformed committed file fails.
2. Secrets scan over well-formed dated and unreleased records finds nothing; positive control flagged.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | Every refusal in the story names line and field; incomplete records stay in the file and are reported, not refused. |
| 2 | The command exits 0 on the empty file, 1 on a refusal, 2 on an unreadable file. |
| 3 | The shipped empty file passes; scan of well-formed records finds nothing. |
