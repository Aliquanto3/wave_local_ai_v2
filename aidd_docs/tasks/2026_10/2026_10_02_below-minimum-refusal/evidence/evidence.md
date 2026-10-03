# Evidence: a raised declaration refuses, the restored one runs

Laptop (`laptop-mobile-gpu`), 2026-10-03, pinned build
`llama-b10537-bin-win-cuda-12.4-x64`, roster entry `qwen3-0.6b-q8`, compute
mode `gpu`. Every results path, the reference path, the fiche registry and the
refusal directory point into this folder (night-run rule), not the committed
stores.

```sh
LLAMA_SERVER_PATH=...\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe
SLM_MODELS_DIR=D:\ia\models QUALITY_PROVIDERS=local ROSTER_ENTRY_ID=qwen3-0.6b-q8
MACHINE_ID=laptop-mobile-gpu COMPUTE_MODE=gpu RUNTIME_REPETITIONS=2
RUNTIME_COOLDOWN_S=0 RUNTIME_WARMUP_COUNT=1
RUNTIME_RESULTS_PATH=RUNTIME_REFERENCE_PATH=<evidence>/runtime.jsonl
FICHE_REGISTRY_DIR=<evidence>/fiches REFUSALS_DIR=<evidence>/refusals
# 1. a copy of models.json with the 0.6B's gpu ram_gb raised from 1.08 to 64
ROSTER_PATH=<scratch>/raised-roster.json uv run wave-local-ai-v2  # runtime-raised.log, exit 1
# 2. the shipped models.json, declaration restored
uv run wave-local-ai-v2                                          # runtime-restored.log, exit 0
```

| Run | Declared `ram_gb` | Observed | Exit | Runtime rows | Refusal records |
| --- | --- | --- | --- | --- | --- |
| raised | 64 | 33.72 GB | 1 | 0 (no `runtime.jsonl` created) | 1 |
| restored | 1.08 | 33.72 GB | 0 | 1 (schema "26", `qwen3-0.6b-q8@laptop-mobile-gpu/gpu`) | still 1 |

The raised run stopped before the build probe and before any `llama-server`
started (no server process, no fiche written by it), named the requirement,
the mode, the declared minimum and the observed value, and named the
`cpu_only` profile of the same entry and machine without running it:

```text
error: refused: roster entry 'qwen3-0.6b-q8' under compute mode 'gpu' requires ram_gb >= 64.0 GB (...); machine 'laptop-mobile-gpu' reports 33.72 GB. Nothing was started and no row was written; the refusal is recorded in ...\refusals\laptop-mobile-gpu.jsonl. A cpu_only profile exists for this entry on this machine (qwen3-0.6b-q8@laptop-mobile-gpu/cpu_only); it is not run in this one's place: set COMPUTE_MODE=cpu_only to run it
```

Its one refusal record is `refusals/laptop-mobile-gpu.jsonl` (every field of
`row_contract.REFUSAL_FIELDS`, no `schema_version`). The restored run's row
peaked at `process_rss_bytes` 1077616640 (1.078 GB), under the declared 1.08.
Both runs printed that `vram_gb` is not checked (not yet declared).
`wave-local-ai-v2-validate` over the row with this registry: `checked 1
row(s)`, exit 0 (`validate.log`).

Pending (D1): the professional PC's own refusal of the flagship under
`cpu_only` (declared 17.74 GB against its 16 GB) needs an operator on that
machine; it is proven here only on constructed observations
(`tests/test_preflight.py`).
