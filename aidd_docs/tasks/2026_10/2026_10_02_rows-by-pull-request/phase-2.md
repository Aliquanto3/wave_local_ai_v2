---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: The merge command and its refusals

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/bundle_merge.py   ✅ merge, refusals, --check, wave-local-ai-v2-merge-bundle
├── src/wave_local_ai_v2/settings.py       ✏️ DEFAULT_REFUSALS_REFERENCE_PATH
├── pyproject.toml                         ✏️ entry point
└── tests/test_bundle_merge.py             ✅
```

## User Journey

```mermaid
flowchart TD
  A[machines/* locations on main] --> B[wave-local-ai-v2-merge-bundle]
  B -->|clean| C[runtime, quality and refusals reference files]
  B -->|collision, undeclared machine, misfiled row, run in two locations| D[refused naming rows, ids and hash; nothing written]
```

## Test Scope

```mermaid
journey
  section Setup
    two declared machines' locations with rows and refusals => fixture ready: 5: system
  section Happy path
    merge twice => byte-identical bundle, refusals only in their own file: 5: cli
  section Edge case - collision
    one fiche hash under two machine ids => merge => refused naming both rows, both ids, the hash: 1: cli
  section Edge case - undeclared
    row with an undeclared machine id => merge => refused naming it: 1: cli
```

## Tasks to do

### `1)` Merge

> Derive, never choose.

1. Read every declared machine's location; refuse undeclared location directories, unresolved or misfiled machine ids, one run id in two locations, fiche-hash collisions.
2. Write the three bundle files in sorted machine order, lines unchanged; refuse to overwrite the pinned pre-merge snapshot.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Deterministic bundle; collision and undeclared machine refused by name; refusals only in their own file |
