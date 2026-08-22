---
objective: "Every counted repetition records GPU temperature, NVML throttle reasons and CPU package temperature (or its declared unavailability); the row flags itself unreliable when gen_tok_per_s spread exceeds a configured threshold, reports the same statistic for ttft_ms and prompt_tok_per_s, declares its inter-repetition thermal posture, and states ttft_source on every runtime row."
status: implemented
---

# Plan: Each repetition records machine state, and the row states its TTFT provenance

## Overview

| Field      | Value                                                                                                                                                                                                                                                                                                            |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**   | Extend the existing repetition/aggregation/row-contract machinery so a runtime row carries per-repetition machine state, a spread-based `unreliable` flag, a declared thermal posture, and a labelled TTFT provenance — never forking the modules the prior increment built.                                    |
| **Source** | Stories 10-11 of `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md`: `each-repetition-records-machine-state-and-the-row-flags-excess-spread.md`, `runtime-rows-state-where-their-ttft-came-from.md`. Authority: PRD Methodology 7 and 20 over the stories; epic decisions table. |

## Phases

| #   | Phase                                                    | File                         |
| --- | --------------------------------------------------------- | ----------------------------- |
| 1   | NVML temperature/throttle reads and per-repetition sampling | [`phase-1.md`](./phase-1.md) |
| 2   | Spread, the unreliable flag, thermal posture, settings      | [`phase-2.md`](./phase-2.md) |
| 3   | TTFT provenance                                            | [`phase-3.md`](./phase-3.md) |
| 4   | Live validation, changelog, docs                           | [`phase-4.md`](./phase-4.md) |

## Resources

| Source                                                                                       | Verified                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `uv run python -c "import pynvml; ..."`, installed `nvidia-ml-py==13.610.43`                    | `nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)`, `nvmlDeviceGetCurrentClocksThrottleReasons(handle)` and `nvmlDeviceGetCurrentClocksEventReasons(handle)` all exist on this binding; the `nvmlClocksEventReason*` bit constants exist for decoding. |
| `uv run python -c "import psutil; print(hasattr(psutil, 'sensors_temperatures'))"`, installed `psutil==7.2.2` | `False` — confirms the epic's premise live rather than assumed.                                                                                                                                                                    |
| `Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature` (PowerShell, ordinary privilege, no `wmi` package installed) | `Access denied`. No CPU package temperature reader exists on this platform at ordinary privilege without a vendor driver. Spike concludes `unavailable`, per phase-1's classification.                                          |
| `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`, criteria 7 and 20 | Wording matches the two stories' acceptance verbatim; no gap between story and PRD authority for this increment.                                                                                                                 |

## Decisions

| Decision                                                                                                              | Why                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GPU throttle reasons are read via `nvmlDeviceGetCurrentClocksEventReasons`, not the deprecated `...ThrottleReasons` name. | Both exist on the pinned `nvidia-ml-py==13.610.43` and return the same bitmask; NVML's own naming migration (R520+) retired `ClocksThrottleReasons` in favour of `ClocksEventReasons`. Reading the installed package settled this rather than guessing between two live symbols.        |
| CPU package temperature is a two-field pair: `cpu_temp_c: float \| None` and `cpu_temp_source: "psutil" \| "unavailable"`. | Mirrors the `energy_kwh` / `energy_method` pattern the row already carries: a value that can be `None` beside a label naming how (or whether) it was obtained, rather than overloading the value field with a sentinel string.                                                          |
| `thermal_posture` is a row-level field, not per-repetition, with today's value `"fixed_cooldown"`.                       | The posture describes the protocol the whole repetition set ran under (`cooldown_s` between counted repetitions, already shipped), not a per-repetition observation. Declaring it lets a reader distinguish this row from a future back-to-back or temperature-ceiling posture without inferring it from `cooldown_s` alone. |
| Spread is computed for all three aggregated timing metrics via one `AGGREGATION_LABELS`-driven helper, but only `gen_tok_per_s`'s spread can set `unreliable`.  | Reuses the single-source-of-truth pattern `aggregation.py` already documents (`AGGREGATION_LABELS` drives both row-building and `row_contract` gating) rather than adding a second, parallel mechanism for the two non-flagging metrics.                                                |
| `ttft_source` is produced inside `parse_timings`, not assigned in `__init__.py`.                                        | The label belongs where the number is read, matching the story's explicit ask and keeping `__init__.py` from re-deriving something `timings.py` already knows.                                                                                                                          |

