# wave-local-ai-v2

[![CI](https://github.com/Aliquanto3/wave_local_ai_v2/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliquanto3/wave_local_ai_v2/actions/workflows/ci.yml)

A reproducible benchmark suite that compares small language models (SLMs) running
locally via [llama.cpp](https://github.com/ggml-org/llama.cpp) against cloud LLM
APIs, measuring runtime cost and per-task quality separately, on shared task
suites.

## Who this is for

- **Clients evaluating on-prem vs cloud LLM deployment.** Read the evidence in
  [`aidd_docs/results/README.md`](aidd_docs/results/README.md) and its
  `*-reference.jsonl` files. You don't need to run anything.
- **Developers reproducing the benchmark.** Follow
  [`docs/setup.md`](docs/setup.md) end to end; you'll run both CLIs on your own
  machine.

The quality table and the runtime table are **never merged into one**: quality
scores are reproducible given model + prompt + seed, while runtime metrics are
bound to the hardware that produced them and must carry a signed hardware
fiche. See the "Quality / runtime split" decision in
[`aidd_docs/memory/architecture.md`](aidd_docs/memory/architecture.md) and the
evidence layout in [`aidd_docs/results/README.md`](aidd_docs/results/README.md).

A merge is blocked by a lint, format, or type-check failure, a test failure,
coverage dropping below 80%, a secret detected in the diff, or an unwaived
high/critical-severity dependency finding — see open exceptions in
[`docs/dependency-waivers.yml`](docs/dependency-waivers.yml).

## Hardware you need before downloading anything

The roster model, `Qwen3.6-35B-A3B-UD-IQ4_XS` (17.7 GB GGUF), needs:

- **32 GB system RAM**
- An **NVIDIA GPU with CUDA 12.x support** — the committed evidence was
  produced on a 6 GB laptop GPU using `--n-cpu-moe` to offload experts to CPU
  RAM. VRAM is not the ceiling here; system RAM is.
- **~18 GB free disk** for the model file plus the `llama-server` binary.

This is the class of the project's own laptop fiche
([`context_input/hardware.md`](context_input/hardware.md)), not a guarantee for
every machine. Runtime numbers are **not portable** across machines — see the
"Gotchas" section of
[`aidd_docs/memory/architecture.md`](aidd_docs/memory/architecture.md).

## Setup, running, results — at a glance

The full walk (binary, weights, `.env`) is in
[`docs/setup.md`](docs/setup.md). Once those pieces are in place, the one setup
command is:

```sh
uv sync
```

### `.env` keys

| Key | Holds | Read by |
| --- | ----- | ------- |
| `SLM_MODELS_DIR` | Directory containing the local GGUF weights | `wave-local-ai-v2`, `wave-local-ai-v2-quality` |
| `LLAMA_SERVER_PATH` | Path to the `llama-server`(`.exe`) binary | `wave-local-ai-v2`, `wave-local-ai-v2-quality` |
| `RUNTIME_RESULTS_PATH` | Where runtime rows are appended (default `aidd_docs/results/runtime.jsonl`) | `wave-local-ai-v2` |
| `QUALITY_RESULTS_PATH` | Where quality rows are appended (default `aidd_docs/results/quality.jsonl`) | `wave-local-ai-v2-quality` |
| `MISTRAL_API_KEY` | Mistral API credential | `wave-local-ai-v2-quality` |
| `GOOGLE_API_KEY` | **Reserved** for the planned second LLM-as-a-judge (Google AI); read by nothing under `src/` today | — |

`wave-local-ai-v2` needs **no cloud credential at all**: inference runs entirely
against a local `llama-server`. (Its energy tracker, CodeCarbon, does attempt one
best-effort geolocation lookup to pick a carbon-intensity factor; it is
unauthenticated, times out in half a second, and a failure only downgrades the
energy figure.) `wave-local-ai-v2-quality` is the only command that needs
`MISTRAL_API_KEY`.

| Command | Produces |
| ------- | -------- |
| `wave-local-ai-v2` | One runtime row, with its hardware fiche, appended to `runtime.jsonl` |
| `wave-local-ai-v2-quality` | One row per (item, model) appended to `quality.jsonl` |

### Results layout

`runtime.jsonl` / `quality.jsonl` are per-machine, untracked, append-only —
every CLI run writes to them. `runtime-reference.jsonl` /
`quality-reference.jsonl` are the curated, committed evidence: no CLI ever
writes to them. See
[`aidd_docs/results/README.md`](aidd_docs/results/README.md) for what each
file supports and how it was produced.

### Energy caveat

Every row carries an `energy_method` field, and it is the only thing that says
whether the number means anything:

- `measured_nvml` — GPU draw read via NVML, a real measurement.
- `estimated_tdp` — no NVML figure, so the total is TDP-estimated. CPU energy on
  Windows is always in this class (no RAPL access) and can be off by a **factor
  of 2-3** under thermal throttling.
- `unavailable` — the tracker failed to start or to stop cleanly; the row has no
  energy figure at all.

Treat energy and carbon figures as **estimates**, not measurements, unless the
row says `measured_nvml`.

## Project status

This is an active benchmark harness, not a finished product. See
[`aidd_docs/backlog/`](aidd_docs/backlog/) for the roadmap (epics and stories),
and [`CONTRIBUTING.md`](CONTRIBUTING.md) if you want to pick up an item.
