---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Row read-back and failure reporting

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/demo_console.py  ✏️ final_event: the view read back, or exit status and the CLI's last `error:` line
├── src/wave_local_ai_v2/service.py       ✏️ read_back through get_quality / get_runtime
└── tests/test_{demo_console,service}.py  ✏️ success, nonzero exit, exit 0 without run_id, row missing; structural no-writer test
```

## Tasks

- Final event never builds a row; on exit 0 it is the existing view route's answer for the announced `run_id`.
- Structural test: no service-side module references `append_row` or opens a store for writing.

## Validation

`uv run pytest tests/test_demo_console.py tests/test_service.py`
