---
status: done
---

# Instruction: Candidate gate runs, in gate order

## Architecture projection

```txt
.
├── aidd_docs/roster/candidate-records.jsonl                       ✅
└── aidd_docs/tasks/2026_10/2026_10_04_half-billion-class/evidence/
    ├── candidates/granite-4.0-h-350m-q8.json                       ✅
    ├── candidates/granite-4.0-350m-q8.json                         ✅ (only if reached)
    ├── candidates/lfm2.5-350m-q8.json                              ✅ (only if reached)
    └── gate-<entry_id>.log                                         ✅
```

## User Journey

```mermaid
flowchart TD
  A[GPU free, port 8080 free, D: >= 20 GB after download] --> B[gate Granite 4.0 H 350M]
  B -->|passed| C[phase 2: both suites]
  B -->|refused| D[gate Granite 4.0 350M]
  B -->|deferred| O[stop: owner build tradeoff]
  D -->|passed| C
  D -->|refused| E[gate LFM2.5-350M]
  E -->|passed| C
  E -->|refused| L[single-family ladder label]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    nvidia-smi 0 MiB, no llama-server, D free space read => preconditions logged: 5: system
  section Happy path
    candidate-gate on the first declaration => passed record with entry block and observed build, template hash, thinking: 5: cli
  section Edge case - refused at load
    load fails => record refused at step load with the verbatim line => next candidate: 1: cli
  section Edge case - deferred
    unknown model architecture => record deferred => stop, owner decides: 1: cli
  section Teardown
    gate stops its server => no llama-server left, GPU 0 MiB: 5: system
```

## Tasks to do

### `1)` Declarations

> One declaration per pinned candidate, from the spike's table.

1. Write each declaration (spike pins, `Q8_0`, family `ibm`/`liquid`, `thinking_control: "none"`, language claim, `client_commercial_use` true for Apache-2.0, false for `lfm1.0`).

### `2)` Gate, one at a time

> Smallest download first; stop at the first candidate that later completes both suites.

1. Check GPU, port, D: free space before each run.
2. Run `wave-local-ai-v2-candidate-gate` with `LLAMA_SERVER_PATH` (b10537) and `SLM_MODELS_DIR=D:\ia\models`; log to `evidence/`.
3. On `deferred`: stop the story for the owner. On `refused`: record, move on.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | Each declaration parses (`parse_candidate`) |
| 2 | One record per gate run in the candidate record; a pass's `observed` carries `llama_cpp_build`, `chat_template_hash`, `thinking` |
