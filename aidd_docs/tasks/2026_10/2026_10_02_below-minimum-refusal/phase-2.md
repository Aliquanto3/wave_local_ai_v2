---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: The pre-flight check and its placement in the three writers

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/preflight.py        ✅ observe, first_failure, enforce, RequirementRefusal, PreflightError
├── src/wave_local_ai_v2/__init__.py         ✅ enforce after the profile resolves, before the model path
├── src/wave_local_ai_v2/quality_cli.py      ✅ same placement
└── src/wave_local_ai_v2/judge_probe.py      ✅ same placement
```

## Tasks

- Observe total RAM, allocatable VRAM (declared, else NVML; read only when a VRAM minimum is declared), free disk only while the weights are absent.
- Refuse on the first failing requirement (RAM, VRAM, disk); a declared minimum nothing observed stops without a record; a `not_yet_declared` one is reported on stderr and not checked.
- A refused `gpu` run names the `cpu_only` profile of the same entry and machine when one is declared, and runs nothing.

## Validation

`uv run pytest tests/test_preflight.py tests/test_cli.py tests/test_quality_cli.py tests/test_judge_probe.py`
