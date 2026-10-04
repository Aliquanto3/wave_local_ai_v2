---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: validated_host moved into profiles; build_flags and host-fit on the resolved profile

## Architecture projection

```txt
.
├── aidd_docs/roster/models.json            ✏️ validated_host removed, roster_version 5
├── src/wave_local_ai_v2/roster.py          ✏️ REQUIRED_FIELDS, RosterEntry, validate_host_fit(entry, profile)
├── src/wave_local_ai_v2/server.py           ✏️ build_flags(entry, profile, model_path)
├── src/wave_local_ai_v2/settings.py        ✏️ SERVER_N_CPU_MOE / SERVER_THREADS as unset-means-None overrides
├── src/wave_local_ai_v2/candidate_gate.py  ✏️ load_profile in place of validated_host
├── src/wave_local_ai_v2/bundle_export.py   ✏️ validated_host column docs removed
└── tests/                                  ✏️ test_launch_byte_identical.py (D4 only), test_server, test_roster, test_settings, fixtures
```

## Validation

`tests/test_launch_byte_identical.py` green with `BASELINE_FLAGS` unchanged; laptop vs tower gpu profiles differ in `-t` / `--n-cpu-moe`; a `cpu_only` profile never emits `--n-cpu-moe`.
