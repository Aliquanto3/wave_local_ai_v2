---
status: done
---

# Instruction: Docs and the local-run evidence

## Architecture projection

```txt
.
├── CHANGELOG.md                         ✏️ schema "18"
├── aidd_docs/memory/cli.md              ✏️ --quantity on the compare command
├── aidd_docs/results/README.md          ✏️ the per-item fields and how to read them (no figures)
└── aidd_docs/tasks/2026_10/2026_10_01_quality-item-tokens-and-first-token-time/evidence/  ✅ run output
```

## User Journey

```mermaid
flowchart TD
  A[two local baseline batches, qwen3-0.6b-q8] --> B[evidence quality.jsonl]
  B --> C[compare --quantity item_tokens_out / item_ttft_ms / energy_kwh]
  C --> D[evidence records + summary]
```

## Test Scope

```mermaid
journey
  section Setup
    env points every results path at evidence/ => no committed store touched: 5: cli
  section Happy path
    run the quality CLI twice locally => rows carry per-item tokens and TTFT: 5: cli
    compare on output tokens => paired record: 5: cli
  section Teardown
    git diff aidd_docs/results => empty: 5: cli
```

## Tasks to do

### `1)` Docs

1. CHANGELOG, cli.md, results README.

### `2)` Evidence

1. Two local runs into `evidence/`, the three comparison records, a summary file.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | A reader finds the fields, their labels and the energy rule documented |
| 2 | Real rows carry per-item figures and a paired output-token record exists; committed stores unchanged |
