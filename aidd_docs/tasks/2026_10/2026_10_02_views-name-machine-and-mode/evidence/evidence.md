# Evidence: a cpu_only row's VRAM reads not applicable, and the views name the machine

Laptop (`laptop-mobile-gpu`), 2026-10-03, pinned build
`llama-b10537-bin-win-cuda-12.4-x64`, roster entry `qwen3-0.6b-q8`. Every
results path, the reference path and the fiche registry point into this
folder (night-run rule), not the live stores.

## 1. The live cpu_only row under schema "25"

```sh
LLAMA_SERVER_PATH=...\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe
SLM_MODELS_DIR=D:\ia\models QUALITY_PROVIDERS=local ROSTER_ENTRY_ID=qwen3-0.6b-q8
MACHINE_ID=laptop-mobile-gpu COMPUTE_MODE=cpu_only
RUNTIME_REPETITIONS=2 RUNTIME_COOLDOWN_S=0 RUNTIME_WARMUP_COUNT=1
RUNTIME_RESULTS_PATH=RUNTIME_REFERENCE_PATH=<evidence>/runtime.jsonl
FICHE_REGISTRY_DIR=<evidence>/fiches
uv run wave-local-ai-v2
```

Exit 0 (`runtime-cpu-only.log`): `gen_tok_per_s=31.1 prompt_tok_per_s=262.0
... repetitions_n=2`. The row cites fiche `d8524577...`, the same cpu_only
fiche order 1's proof stored: same machine, mode and flags, so the same
identity. Order 1's row published `vram_used_mib` 254.7 (the CUDA context);
this one publishes none.

`vram-grep.log` (every `vram_used_mib` in the file):

| Place | Value |
| ----- | ----- |
| row (peak aggregate) | `"not_applicable"` |
| warm-up repetition 0 | `"not_applicable"` |
| counted repetitions 1, 2 | `"not_applicable"` |
| `aggregation.vram_used_mib` (the statistic's label) | `"peak_over_counted_repetitions"` |
| numeric `vram_used_mib` anywhere | none |

`gpu_draw_w` stays measured (17.955 W) and `gpu_energy_method` stays
`measured_nvml`: the GPU's own channel keeps its measurement and label.
`wave-local-ai-v2-validate` over the file: `checked 1 row(s)`, exit 0
(`validate.log`).

## 2. The runtime view over that row

`runtime-view.json` is `read_model.runtime_view` over this folder's store,
as the service serialises it: `machine_id` `laptop-mobile-gpu`,
`compute_mode` `cpu_only`, `vram_used_mib` the absence
`{"absent": true, "reason": "not_applicable", "detail": {"compute_mode":
"cpu_only"}}`, and `machine` the declared entry with `memory_type` `DDR4`,
rated and configured speed 3200 MT/s and `gpu_present` true, each
`source: declared` with its `read_from`.

## 3. Screenshots

Pending: the dashboard is served only over TLS with an API key, and this
unattended run had no browser session and no local certificate pair. The
rendering itself is covered by `RuntimeView.test.tsx` ("not applicable",
machine, mode and "DDR4 (declared)") and `ComparisonView.test.tsx` ("machine
laptop-mobile-gpu", "mode gpu"). The comparison view also needs a quality row
from a schema "23"+ run to show a live machine column.
