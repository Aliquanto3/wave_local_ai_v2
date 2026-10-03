# Evidence: a GPU run and a CPU-only run never share a fiche

Laptop (`laptop-mobile-gpu`), 2026-10-03, pinned build
`llama-b10537-bin-win-cuda-12.4-x64` (CUDA asset), roster entry
`qwen3-0.6b-q8`. Every results path, the reference path and the fiche registry
point into this folder (night-run rule), not the live store.

## 1. Which flag set is genuinely CPU-only (spike)

One completion of a 4001-token prompt, `nvidia-smi` sampled every 0.5 s.

| Launch | GPU utilisation during prompt processing | GPU memory used | Prompt tok/s | Log |
| ------ | ---------------------------------------- | --------------- | ------------ | --- |
| `-ngl 0` | 74%, then 35% | 397 MiB | 2227 | `spike-ngl0.log`, `spike-ngl0.server.log` |
| `-ngl 0 --device none` | 0% throughout | 107 MiB (CUDA context only) | 211 | `spike-devnone.log`, `spike-devnone.server.log` |

`-ngl 0` alone still offloads prompt-processing work to the GPU on the CUDA
build. `--device none` is the additional setting that makes the run CPU-only,
so `cpu_only` emits `-ngl 0 --device none` (`server.CPU_ONLY_DEVICE_FLAGS`).
`-fa on` and `--load-mode auto` were accepted in both launches. The process
still opens a CUDA context (about 107 MiB, no utilisation). This is the
laptop's observation only; the tower and the professional PC (CPU asset)
await machine-readiness order 0.

## 2. Epic success check 1, for real

Command (environment in the order the script set it):

```sh
LLAMA_SERVER_PATH=...\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe
SLM_MODELS_DIR=D:\ia\models QUALITY_PROVIDERS=local ROSTER_ENTRY_ID=qwen3-0.6b-q8
MACHINE_ID=laptop-mobile-gpu
RUNTIME_REPETITIONS=2 RUNTIME_COOLDOWN_S=0 RUNTIME_WARMUP_COUNT=0
RUNTIME_RESULTS_PATH=RUNTIME_REFERENCE_PATH=<evidence>/runtime.jsonl
FICHE_REGISTRY_DIR=<evidence>/fiches
COMPUTE_MODE=gpu      uv run wave-local-ai-v2   # run 1
COMPUTE_MODE=cpu_only uv run wave-local-ai-v2   # run 2, reference = run 1's row
```

| Run | `compute_mode` | `fiche_hash` | gen tok/s | prompt tok/s |
| --- | -------------- | ------------ | --------- | ------------ |
| 1 | `gpu` | `73ec536e09346ef914cf61b5412bfc87d36b22436543f1204cb628a6f79e97a0` | 209.9 | 12829.1 |
| 2 | `cpu_only` | `d85245776b892c47e9105362b9c15fb74711cdcb790db3133b1a52fec2de67db` | 29.9 | 300.4 |

Two different hashes, two stored fiches (`fiches/`), each with its own flags:

- `gpu`: `-m <path> -ngl 99 -c 32768 -fa on -t 8 --jinja -np 1 --load-mode auto ...`
- `cpu_only`: `-m <path> -ngl 0 --device none -c 32768 -fa on -t 8 --jinja -np 1 --load-mode auto ...`

Run 2's verdict against run 1's row (`runtime.jsonl`, second row):

```json
{"verdict": "not_comparable", "reference_run_id": null, "differing_fields": ["compute_mode", "flags"], "reason": "no reference row matches every blocking field"}
```

GPU during run 2 (`cpu-only-nvidia-smi.log`): 21 one-second samples at
107 MiB and 0% while the `cpu_only` server ran.

`wave-local-ai-v2-validate` over `runtime.jsonl` with
`FICHE_REGISTRY_DIR=<evidence>/fiches`: `checked 2 row(s)`, exit 0
(`validate.log`).

## 3. Refusal before any server starts

`refusal.log`: the same environment with no `COMPUTE_MODE` exits 1 with
`error: COMPUTE_MODE is not set: a run declares gpu or cpu_only, never a default`.

## 4. Observed, owned elsewhere

The `cpu_only` row still publishes `vram_used_mib` 254.7 (whole-GPU memory,
the CUDA context included). The epic's success check 3 (a `cpu_only` row's
VRAM declared not applicable, never a number) belongs to a later story of
this epic, not this one.
