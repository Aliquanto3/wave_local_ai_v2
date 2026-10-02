---
status: done
---

# Instruction: The variant registry, its load-time hash check, and the one application function

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/
│   └── prompt_variants.py      ✅ registry (baseline v1, identity), definition hash, load check, resolve, apply_variant
└── tests/
    └── test_prompt_variants.py ✅ baseline loads; edited definition at unchanged version refused naming it; unknown id/version refused
```

## User Journey

```mermaid
flowchart TD
  A[import prompt_variants] --> B[load_registry recomputes each definition hash]
  B -->|matches| C[REGISTRY: baseline v1]
  B -->|differs| D[PromptVariantError naming the variant and its version]
  C --> E[resolve id + version]
  E --> F[apply_variant on the authored prompt]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    Registry entries as a literal tuple => known baseline entry: 5: system
  section Happy path
    load the tracked registry => baseline v1 identity loads with its hash: 5: system
    apply baseline to an authored prompt => the same string comes back: 5: system
  section Edge case - edited definition
    definition edited, version unchanged => load => refused naming baseline and version 1: 1: system
  section Edge case - unknown variant
    unregistered id or version => resolve => refused naming it: 1: system
```

## Tasks to do

### `1)` Registry and loader

> A tracked registry whose entries carry id, version, definition and definition hash, refused at load on a mismatch.

1. `definition_hash`: sha256 over canonical JSON of the definition.
2. `load_registry(entries)`: recompute each hash, refuse a mismatch naming id and version, refuse duplicate (id, version).
3. Module-level `REGISTRY = load_registry(REGISTERED_VARIANTS)`.

### `2)` Resolve and apply

> One function applies a variant; nothing else transforms a prompt.

1. `resolve(variant_id, version=None)` -> entry, refusing an unknown id or version.
2. `apply_variant(variant, authored_prompt)` dispatching on the definition's transformation (`identity` only).

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | `baseline` v1 loads; an edited definition at an unchanged version raises naming `baseline` and version `1` |
| 2 | `apply_variant(baseline, text)` returns `text`; an unknown id or version raises naming it |
