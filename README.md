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

`main` takes changes only through a checked pull request — the ruleset that
enforces it is tracked in
[`.github/rulesets/main.json`](.github/rulesets/main.json).

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
file supports and how it was produced. This committed `*-reference.jsonl`
evidence predates the first release tag — it carries no version binding and
must not be read as evidence "for v0.1.0" or any other tag.

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

## Pull and run (no clone)

The image carries no clone, no model weights, and no `.env` — it installs the
project from the locked deps and ships the pinned CPU `llama-server` build.
This path reaches the same first-run weight download and the same two CLIs as
the clone-and-`uv sync` path above, at the same level of detail.

```sh
docker pull ghcr.io/aliquanto3/wave_local_ai_v2:v0.1.0
```

You still need `compose.yaml` — the one file a pull-only reader has no clone
to read from disk. Fetch it directly for the tag you pulled, and make the
directory the result rows land in:

```sh
curl -fsSLO https://raw.githubusercontent.com/Aliquanto3/wave_local_ai_v2/v0.1.0/compose.yaml
mkdir -p results
```

`compose.yaml` runs `ghcr.io/aliquanto3/wave_local_ai_v2:${WAVE_IMAGE_TAG:-latest}`
and has no build section, so it uses the image you just pulled and never tries
to build one. Set `WAVE_IMAGE_TAG=v0.1.0` to run the exact tag rather than
`latest`. Rows land in `./results` on the host (override with `RESULTS_DIR`);
the container runs as your own uid so those files come back owned by you.

**First run — download the model weights.** The image ships no GGUF; populate
`SLM_MODELS_DIR` on the **host** exactly as
[`docs/setup.md` §3](docs/setup.md#3-get-the-model-weights-and-verify-the-checksum)
describes, at this exact relative path:

```
<SLM_MODELS_DIR>/Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
```

sha256: `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3`
(same file, same checksum as the clone path — a clone-path reader who already
did this step can reuse the same directory).

Then, with `SLM_MODELS_DIR` set on the host and a `.env` populated per the
[`.env` keys](#env-keys) table (`MISTRAL_API_KEY` at minimum for the quality
CLI):

```sh
docker compose run --rm runtime   # one runtime row
docker compose run --rm quality   # one row per (item, model)
```

`N_CPU_MOE`, `THREADS`, the pinned model file, and the pinned `llama.cpp`
build are fitted to this project's own development laptop, exactly as they
are on the clone path — this image is not a machine-portable container. That
arrives, if it does, with
[`every-published-row-explains-and-reproduces-itself`](aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md),
not here.

**NVIDIA GPU:** the shipped image is CPU-only. See
[`docs/setup.md`'s NVIDIA section](docs/setup.md#nvidia-gpu-documented-untested-in-ci)
for the base image and flags a GPU deployment would need — documented, not
built or tested by this project's CI.

**What CI proves about this image, and what it doesn't:**

- CI proves, on every pull request and again on the tag before it publishes
  (`.github/workflows/ci.yml`, job `build`): the image builds on a GPU-less
  Ubuntu runner; `docker run --entrypoint llama-server <image> --version`
  exits 0, so the pinned binary is present and executable with no model and
  no GPU; `docker run <image>` with `SLM_MODELS_DIR` empty exits 1 and prints
  exactly `error: SLM_MODELS_DIR is not set`; `docker inspect` reports
  `org.opencontainers.image.source` and `.revision` equal to this repository's
  URL and the commit the build ran on.
- CI does **not** prove: that a real CPU or GPU inference run completes
  inside the container, that the compose volumes behave correctly against
  real weights, that the published package is anonymously pullable (that is
  a one-time manual visibility switch, verified at the first tag), or that
  the NVIDIA path works at all. Those belong to the epic's fresh-machine
  walk, done by a human on real hardware — not to this repository's CI.

## Project status

This is an active benchmark harness, not a finished product. See
[`aidd_docs/backlog/`](aidd_docs/backlog/) for the roadmap (epics and stories),
and [`CONTRIBUTING.md`](CONTRIBUTING.md) if you want to pick up an item.
