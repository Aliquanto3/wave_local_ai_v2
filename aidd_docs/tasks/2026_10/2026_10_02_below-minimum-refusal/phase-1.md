---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Declared requirements and their loader, calibrated from published peaks

## Architecture projection

```txt
.
├── aidd_docs/roster/models.json             ✅ requirements per entry per mode, roster_version 6
├── src/wave_local_ai_v2/roster.py           ✅ REQUIREMENTS_BY_MODE, _parse_requirements, required by load_roster
├── src/wave_local_ai_v2/bundle_export.py    ✅ column dictionary for the requirement fields
└── tests/                                   ✅ fixtures carry ROSTER_REQUIREMENTS; loader tests in test_preflight.py
```

## Tasks

- Each entry declares `gpu` (`ram_gb`, `vram_gb`, `disk_gb`) and `cpu_only` (`ram_gb`, `disk_gb`), each `{value, source, read_from}`, calibrated per the plan's Decisions.
- Loader refuses: missing block, missing mode or requirement, unknown requirement (`vram_gb` under `cpu_only`), non-positive or boolean declared value, `not_yet_declared` with a value, unknown source, empty `read_from`.

## Validation

`uv run pytest tests/test_preflight.py tests/test_roster.py tests/test_bundle_export.py`
