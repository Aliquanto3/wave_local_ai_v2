---
status: done
---

# Instruction: Per-item quantities as compared fields; energy as an observation

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/
│   ├── comparison.py      ✏️ compared quantity, continuous_measurement kind => Wilcoxon, energy observation, family identity
│   ├── read_model.py      ✏️ the eleven fields partitioned (not rendered)
│   └── bundle_export.py   ✏️ the eleven fields described
└── tests/                 ✏️ test_comparison, test_read_model, test_bundle_export
```

## User Journey

```mermaid
flowchart TD
  A[compare --quantity item_tokens_out] --> B[refusals + label checks]
  B --> C[per-item values over identical item ids]
  C --> D[Wilcoxon record]
  E[compare --quantity energy_kwh] --> F[observation: no paired test, reason, batch values]
```

## Test Scope

```mermaid
journey
  section Happy path
    constructed variant pair on item_tokens_out => compare => Wilcoxon over identical item ids: 5: system
  section Edge case - energy
    same pair on energy_kwh => compare => observation with the tracker-resolution reason, no p: 1: system
  section Edge case - predates schema
    rows below 18 => compare on item_ttft_ms => refusal naming the field: 1: system
  section Edge case - score unchanged
    committed records => recompute => byte-identical: 1: system
```

## Tasks to do

### `1)` Comparison

1. Quantity constants, scoring kind `continuous_measurement` in the test table with its reason.
2. `compare_sides(..., quantity=)`; refusals for an absent field or mismatched labels; energy member.
3. Family definition and key and default path carry a non-score quantity; `--quantity` flag.

### `2)` Read side

1. Read-model partition, bundle dictionary, `EXCLUDED_FROM_DIFFERING`.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | A constructed baseline/variant pair compared on output tokens produces a Wilcoxon record over identical item ids; energy is an observation saying why |
| 2 | The bundle export and the read-model partition accept a schema "18" row; score records are unchanged |
