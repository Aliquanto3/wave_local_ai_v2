# Evidence: every row and fiche names its run profile

Laptop (`laptop-mobile-gpu`), 2026-10-03, pinned build
`llama-b10537-bin-win-cuda-12.4-x64`, roster entry `qwen3-0.6b-q8`. Every
results path, the reference path and the fiche registry point into this
folder (night-run rule), not the live stores.

```sh
LLAMA_SERVER_PATH=...\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe
SLM_MODELS_DIR=D:\ia\models QUALITY_PROVIDERS=local ROSTER_ENTRY_ID=qwen3-0.6b-q8
MACHINE_ID=laptop-mobile-gpu RUNTIME_REPETITIONS=2 RUNTIME_COOLDOWN_S=0
RUNTIME_WARMUP_COUNT=1 RUNTIME_RESULTS_PATH=RUNTIME_REFERENCE_PATH=<evidence>/runtime.jsonl
FICHE_REGISTRY_DIR=<evidence>/fiches
COMPUTE_MODE=gpu uv run wave-local-ai-v2                       # runtime-gpu.log, exit 0
COMPUTE_MODE=cpu_only uv run wave-local-ai-v2                  # runtime-cpu-only.log, exit 0
COMPUTE_MODE=cpu_only SERVER_THREADS=6 uv run wave-local-ai-v2 # runtime-cpu-only-threads-override.log, exit 0
```

`profile-fields.txt` (schema, mode, row `profile_id`, row `profile_overrides`,
fiche hash prefix, fiche `profile_id`, launched `-ngl`/device flags, `-t`,
verdict):

| Run | Row `profile_id` | `profile_overrides` | Fiche | Launched |
| --- | --- | --- | --- | --- |
| gpu | `qwen3-0.6b-q8@laptop-mobile-gpu/gpu` | `{}` | `73ec536e...` | `-ngl 99 -t 8` |
| cpu_only | `qwen3-0.6b-q8@laptop-mobile-gpu/cpu_only` | `{}` | `d8524577...` | `-ngl 0 --device none -t 8` |
| cpu_only, `SERVER_THREADS=6` | `qwen3-0.6b-q8@laptop-mobile-gpu/cpu_only` | `{"threads": {"profile": 8, "operator": 6}}` | `ea458dc8...` | `-ngl 0 --device none -t 6` |

All three rows are schema "26" and each fiche carries the row's `profile_id`.
The `cpu_only` fiche hashes to `d8524577...`, the same identity story 1 and
story 5 stored for this model and mode: moving the thread count from the
roster into the profile changed nothing that is launched. The overridden run
is a different fiche (its `-t` enters the engine configuration hash) and its
row names the deviation. `wave-local-ai-v2-validate` over the file with this
registry: `checked 3 row(s)`, exit 0 (`validate.log`).
