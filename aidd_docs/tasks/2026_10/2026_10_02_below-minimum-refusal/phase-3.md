---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: The refusal record, its contract and its per-machine file

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/row_contract.py     ✅ REFUSAL_FIELDS, REFUSAL_CONTRACT_VERSION, validate_refusal
├── src/wave_local_ai_v2/results.py          ✅ append_refusal
└── src/wave_local_ai_v2/settings.py         ✅ REFUSALS_DIR, default aidd_docs/results/refusals (tracked)
```

## Tasks

- One record per refusal: entry, machine, mode, profile id, requirement, declared, observed, unit, release version, commit sha, timestamp.
- Never a row: no `schema_version` (refused by the contract), never selectable by a schema floor, kept out of every results store.

## Validation

`uv run pytest tests/test_preflight.py`
