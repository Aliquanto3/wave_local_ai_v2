---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Demo mode, declared-set options route, occupancy lock

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/settings.py      ✏️ SERVICE_DEMO_MODE (strict, off by default); ServiceSettings.machine_id from MACHINE_ID
├── src/wave_local_ai_v2/demo_console.py  ✅ declared sets (kinds, suites, roster entries, this machine's profiles), request validation, occupancy lock
├── src/wave_local_ai_v2/service.py       ✏️ /api/console router: unconditional key gate, then demo-mode gate; GET /options
├── tests/test_settings.py                ✏️ demo mode unset/true/false/other
├── tests/test_demo_console.py            ✅ sets, every validation refusal, lock
└── tests/test_service.py                 ✏️ console routes keyless from loopback and off it, demo off
```

## Tasks

- `demo_console.options_payload`: kinds, `suite_registry.registered_ids()`, roster entry ids, per-entry declared profiles of the service machine (`{profile_id, machine_id, compute_mode}`), the service machine or its named absence, the current holder.
- `validate_request`: closed field set; identifier allow-list; membership in each set; another machine refused naming both; no machine declared on the service refused naming `MACHINE_ID`.
- Lock: `try_acquire` returns the holder when busy, `record_run_id`, `release`.

## Validation

`uv run pytest tests/test_settings.py tests/test_demo_console.py tests/test_service.py`
