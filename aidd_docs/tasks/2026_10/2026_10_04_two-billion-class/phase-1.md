---
status: done
---

# Instruction: Candidate gate runs, in gate order

## Architecture projection

```txt
.
├── aidd_docs/roster/candidate-records.jsonl                        ✏️ one record per gate run
└── aidd_docs/tasks/2026_10/2026_10_04_two-billion-class/evidence/
    ├── candidates/<entry_id>.json                                   ✅ one declaration per pinned candidate
    └── gate-<entry_id>.log                                          ✅
```

## User Journey

```mermaid
flowchart TD
  A[GPU free, port 8080 free, D: >= 20 GB after download] --> B[gate LFM2.5-1.2B-Instruct]
  B -->|passed| M[gate Granite 3.1 1B-A400M MoE]
  B -->|refused| C[gate Granite 3.1 1B-A400M MoE, then Granite 4.0 H 1B, Granite 4.0 1B until a non-Qwen family passes]
  B -->|deferred| O[stop: owner build tradeoff]
  M -->|passed| E[class holds its MoE]
  M -->|refused or deferred| R[moe_absent_reason names the record]
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
    candidate-gate on a declaration => passed record with entry block and observed build, template hash, thinking: 5: cli
  section Edge case - refused at load
    load fails => record refused at step load with the verbatim line => next candidate: 1: cli
  section Edge case - deferred
    unknown model architecture => record deferred => stop, owner decides: 1: cli
  section Teardown
    gate stops its server => no llama-server left, GPU 0 MiB: 5: system
```

## Tasks to do

### `1)` Declarations

1. One declaration per pinned candidate (spike pins, `Q8_0`, `liquid`/`ibm`, `thinking_control: "none"`, language claim off the base card, `client_commercial_use` false for `lfm1.0`).

### `2)` Gate, one at a time

1. GPU, port, D: free space before each run (stop under 20 GB left).
2. `wave-local-ai-v2-candidate-gate` with `LLAMA_SERVER_PATH` (b10537) and `SLM_MODELS_DIR=D:\ia\models`; log to `evidence/`.
3. Once a non-Qwen family passed, only the MoE candidate is still tried.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | Each declaration parses (`parse_candidate`) |
| 2 | One record per gate run; a pass's `observed` carries `llama_cpp_build`, `chat_template_hash`, `thinking` |
