---
status: done
---

# Instruction: Bench session

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
aidd_docs/tasks/2026_10/2026_10_04_laptop-republishes-bundle/evidence/
├── machine-state.txt  ✅ power, nvidia-smi, top CPU processes, free RAM before the session
├── stores/runtime.jsonl, stores/quality.jsonl  ✅ the session's live stores
├── fiches/  ✅ the session's live fiche registry
└── refs/  ✅ the per-pair reference files
```

## User Journey

```mermaid
flowchart TD
  S[capture machine state] --> F1[flagship runtime run 1] --> F2[flagship runtime run 2 vs run 1]
  F2 --> Q1[quality run 1: local flagship + mistral] --> Q2[quality run 2 vs run 1]
  Q2 --> G1[0.6B gpu run 1] --> G2[0.6B gpu run 2 vs gpu run 1]
  G2 --> C1[0.6B cpu_only run 1] --> C2[0.6B cpu_only run 2 vs cpu_only run 1]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    no llama-server running, GPU at 0 MiB => GPU free before each step: 5: system
  section Happy path
    eight runs from the clone => four verdict-bearing second runs, each reproduced or not_reproduced against its own first: 5: cli
  section Edge case - cpu_only VRAM
    cpu_only run => row written => vram_used_mib is not_applicable on row and repetitions: 1: cli
  section Teardown
    every llama-server stopped by PID => GPU back to 0 MiB: 5: system
```

## Tasks to do

### `1)` Capture the machine state

### `2)` Run the eight runs, one at a time, GPU free before each

1. Paid calls only in the two quality runs, key injected into that command only.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1    | `machine-state.txt` names power source, GPU memory, top CPU processes, free RAM |
| 2    | Each second run's verdict names its own first run's `run_id`; no gpu-vs-cpu_only throughput verdict exists; Mistral calls = 40 |
