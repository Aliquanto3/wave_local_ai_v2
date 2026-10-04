---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Profile registry, loader and resolver with its refusal

## Architecture projection

```txt
.
├── aidd_docs/roster/profiles.json        ✅ per-(machine, mode) defaults, the flagship's laptop gpu override
├── src/wave_local_ai_v2/profiles.py      ✅ loader, resolver, ResolvedProfile, ProfileError
└── tests/test_profiles.py                ✅ order, defaults, missing triple, undeclared value, shipped registry
```

## Tasks

- Loader refuses: unknown mode, unknown machine, a value not `{value, source, read_from}`, `not_yet_declared` with a value, `cpu_only` with `n_cpu_moe` or `n_gpu_layers` other than 0, an entry override naming an undeclared (machine, mode).
- `resolve(registry, entry, machine_id, compute_mode, *, operator_n_cpu_moe, operator_threads)`: entry default, then profile, then operator; records overrides; refuses a missing triple naming it and the entry's declared profiles; refuses an undeclared value nobody overrode.

## Validation

`uv run pytest tests/test_profiles.py`
