---
objective: "One CLI command launches llama-server for Qwen3.6-35B-A3B, runs one fixed prompt, and writes one runtime row carrying every hardware-fiche field, with tok/s matching the validated baseline within +/-1.5 tok/s."
status: in-progress
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Runtime measurement harness (Increment 1)

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Single CLI command produces one valid runtime row for Qwen3.6-35B-A3B on this machine, complete hardware fiche included. No task suite, no scoring, no cloud, no API/front end. |
| **Source** | User request (raw text): "Increment 1 — runtime measurement harness" |

## Phases

| #   | Phase                          | File                          |
| --- | ------------------------------ | ------------------------------ |
| 1   | Fiche and results store        | [`phase-1.md`](./phase-1.md)  |
| 2   | llama-server process lifecycle | [`phase-2.md`](./phase-2.md)  |
| 3   | Metrics collection              | [`phase-3.md`](./phase-3.md)  |
| 4   | CLI wiring (end to end)         | [`phase-4.md`](./phase-4.md)  |

## Resources

| Source | Verified |
| ------ | -------- |
| `context_input/baseline_qwen36.md` | Validated flag set and expected tok/s for `--n-cpu-moe 37` on this machine; harness must reproduce, not rediscover, this command. |
| `context_input/hardware.md` | This machine's fiche fields (CPU, RAM, GPU, driver 572.70, CUDA ceiling 12.8). |
| `aidd_docs/memory/architecture.md` | Mandatory flags (`--load-mode none`, `--jinja`, `-np 1`), `energy_method` tagging rule, quality/runtime table split. |
| Local filesystem | `llama-server.exe` (build b10537, matches baseline) found at `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`. |
| Local filesystem | Model file found at `D:\ia\models\Qwen3.6-35B-A3B\Qwen3.6-35B-A3B-UD-IQ4_XS.gguf`, matching `SLM_MODELS_DIR` in `.env`. |
| `nvidia-smi.exe` | Present at `C:\Windows\System32\nvidia-smi.exe`; confirms NVML is reachable on this machine for VRAM/GPU-draw collection. |
| `uv pip list` | No runtime deps installed yet (only dev tools). `pynvml`/`nvidia-ml-py`, `codecarbon`, `psutil` must be added; `requests` already present. |

## Decisions

| Decision | Why |
| -------- | --- |
| Results store is an append-only JSONL file (`aidd_docs/results/runtime.jsonl` or similar, decided in phase 1), not a database. | No results-store convention exists yet; JSONL keeps the hardware-fiche's variable-shape dict trivial to append without a schema migration, and matches the project's file-based, no-infra-yet stage. |
| llama-server path and model path are read from environment variables (extend `.env`), not hardcoded. | The binary and model live outside the repo (`C:\Users\Anael\llama_cpp\...`, `D:\ia\models\...`); hardcoding breaks on the "Tour" secondary machine referenced in `hardware.md`. |
| CodeCarbon's `EmissionsTracker` wraps only the generation call, not process startup/shutdown. | Startup/shutdown energy is noise relative to the measured task; keeping the tracked window tight to the single request keeps the energy figure attributable to the fixed prompt. |
