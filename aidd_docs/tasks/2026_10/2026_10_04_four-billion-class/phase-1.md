---
status: done
---

# Instruction: Candidate gate runs, in gate order

## Architecture projection

```txt
.
├── aidd_docs/roster/candidate-records.jsonl                        ✏️ one record per gate run
└── aidd_docs/tasks/2026_10/2026_10_04_four-billion-class/evidence/
    ├── candidates/<entry_id>.json                                   ✅ one declaration per pinned candidate
    └── gate-<entry_id>.log                                          ✅
```

## User Journey

```mermaid
flowchart TD
  A[GPU free, port 8080 free, D: >= 20 GB after download] --> B[gate Granite 3.1 3B-A800M MoE]
  B -->|passed| S[search ends: non-Qwen and MoE, Q128 a]
  B -->|refused| C[gate Ministral 3 3B, then Phi-4-mini until a non-Qwen family passes, then Phi-tiny-MoE]
  B -->|deferred| O[stop: owner build tradeoff]
```

## Tasks to do

### `1)` Declarations

1. One declaration per pinned candidate (spike pins, `Q4_K_M` except Phi-tiny-MoE's only `Q8_0`, `ibm`/`mistral`/`microsoft`, `thinking_control: "none"`, language claim off the base card, Phi-tiny-MoE `context_size: 4096`).

### `2)` Gate, one at a time

1. GPU, port, D: free space before each run (stop under 20 GB left).
2. `wave-local-ai-v2-candidate-gate` with `LLAMA_SERVER_PATH` (b10537) and `SLM_MODELS_DIR=D:\ia\models`; log to `evidence/`.
3. Stop once a non-Qwen MoE passed (Q128 (a)).

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | Each declaration parses (`parse_candidate`) |
| 2 | One record per gate run; a pass's `observed` carries `llama_cpp_build`, `chat_template_hash`, `thinking` |
