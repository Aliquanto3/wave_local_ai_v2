---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Profile id and override record on fiche and rows across the three writers

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/hardware.py      ✏️ profile_id on the fiche, outside every projection
├── src/wave_local_ai_v2/row_contract.py  ✏️ profile_id, profile_overrides; SCHEMA_VERSION "26"
├── src/wave_local_ai_v2/__init__.py      ✏️ resolve the profile before any spawn; stamp row and fiche
├── src/wave_local_ai_v2/quality_cli.py   ✏️ same
├── src/wave_local_ai_v2/judge_probe.py   ✏️ same
├── src/wave_local_ai_v2/read_model.py    ✏️ the two fields placed as not rendered
└── tests/                                ✏️ writer tests, test_hardware (rename does not move the hash), test_row_contract
```

## Validation

Every row and fiche names its profile; an overridden run names its override; renaming a profile does not move `fiche_hash`.
