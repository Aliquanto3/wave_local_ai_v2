---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Launcher, run_id announcement, graceful stop, stream route

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/__init__.py      ✏️ print run_id first; graceful-stop handler
├── src/wave_local_ai_v2/__main__.py      ✅ `python -m wave_local_ai_v2`
├── src/wave_local_ai_v2/quality_cli.py   ✏️ print run_id first; graceful-stop handler; `__main__` guard
├── src/wave_local_ai_v2/server.py        ✏️ StopRequested, install_graceful_stop, readiness wait stops its server on any exception
├── src/wave_local_ai_v2/demo_console.py  ✏️ command table, child env, launch, stop_child, ConsoleRun pump/follow
├── src/wave_local_ai_v2/service.py       ✏️ POST /runs, GET /runs/{launch_id}/stream, lifespan stop
├── tests/conftest.py                     ✏️ restore the stop-signal handler after each test
└── tests/test_{cli,quality_cli,server,demo_console,service}.py ✏️
```

## Tasks

- `command_for`: `[sys.executable, "-u", "-m", <module>]` (+ `--suite <id>` for quality); env additions `ROSTER_ENTRY_ID`, `MACHINE_ID`, `COMPUTE_MODE` from the validated request.
- `child_env`: service env, `SERVICE_API_KEY` blanked, unbuffered.
- Stream timing asserted on a stub child that prints, sleeps, prints.

## Validation

`uv run pytest tests/test_demo_console.py tests/test_service.py tests/test_cli.py tests/test_quality_cli.py tests/test_server.py`
