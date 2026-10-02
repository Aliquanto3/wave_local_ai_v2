---
status: done
---

# Instruction: The six record fields, the two backends, and the writer gate

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/
│   ├── judge.py            ✏️ JudgeResponse + JudgeCallRecord gain six fields; vocabulary constants
│   ├── judge_backends.py   ✏️ both backends fill the fields from what they send and receive
│   ├── google_client.py    ✏️ GoogleCompletion.reasoning_tokens: thoughtsTokenCount, else derived from the totals
│   └── row_contract.py     ✏️ SCHEMA_VERSION "13"; answering-provider, source, effort, reasoning-pair checks
└── tests/
    ├── test_judge.py        ✏️ backends record not_sent and null-with-reason; mismatched answering provider refused at write
    ├── test_google_client.py ✏️ reported count, derived count on the pinned shape, None without totals, contradiction refused
    └── test_row_contract.py ✏️ each new record field missing is refused by name; deterministic row unchanged
```

## User Journey

```mermaid
flowchart TD
  A[backend call] --> B[JudgeResponse: answering_provider, source, effort sent, reasoning tokens or null + reason]
  B --> C[run_judge_call copies into JudgeCallRecord]
  C --> D[judge_item block]
  D --> E{row_contract.validate_row}
  E -- answering != bound --> F[RowContractError naming both]
  E -- field missing --> G[RowContractError naming it]
  E -- ok --> H[row written]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    Stub requests.post with a Mistral or Google judge body => backend ready: 5: system
  section Happy path
    Call each backend => record names its bound provider via direct_endpoint, effort not_sent, reasoning null with reason: 5: system
  section Edge case - substituted provider
    Stub backend answers as another provider => judge_item then validate_row => refused naming both providers: 1: system
  section Edge case - missing field
    Judged row record lacks one new field => validate_row => refused naming that field: 1: system
```

## Tasks to do

### `1)` Record fields

> Additive TypedDict fields and their closed vocabularies.

1. Add the six keys to `JudgeResponse` and `JudgeCallRecord`; copy them in `run_judge_call`.
2. Declare `ANSWERING_PROVIDER_SOURCES`, `REASONING_EFFORT_NOT_SENT`, `REASONING_TOKENS_NULL_REASONS`.

### `2)` Backends

> Fill from what is actually sent and received.

1. Google client returns `reasoning_tokens` from `thoughtsTokenCount`, else `total - prompt - candidates` flagged as derived when all three are present, else None.
2. Both backends: bound provider + `direct_endpoint`, `not_sent`, reasoning count or null with its reason.

### `3)` Writer gate

> Refuse what the row cannot back.

1. Bump `SCHEMA_VERSION` to "13" with its reason.
2. Per judge record: answering provider equals bound provider (naming both), known source, non-empty effort string, reasoning count xor known null reason.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | `JUDGE_CALL_RECORD_FIELDS` includes the six keys and a record carries them |
| 2 | Mistral and Google judge records say `not_sent`; Mistral carries null reasoning tokens with a named reason; Google on the pinned usage shape carries a 0 tagged `derived_from_totals` and a reportable cost; a Google body with `thoughtsTokenCount` yields that count tagged `reported` |
| 3 | A row whose record names a different answering provider is refused naming both; a row missing any new field is refused naming it; a deterministic quality row validates unchanged |
