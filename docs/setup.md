# Setup: from a fresh clone to two results rows

This walk takes a fresh machine to one runtime row (`runtime.jsonl`) and one
set of quality rows (`quality.jsonl`). Steps 1-3 need no GPU and no API key —
they work on a CI-class Linux container. A GPU-bearing machine becomes
mandatory only at step 4.2 (the first `wave-local-ai-v2` run), since that's
where `llama-server` actually loads the model and runs inference.

## 1. Prerequisites and install

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) installed
- `git`
- **~18 GB free disk** for the weights and the binary, **32 GB system RAM**, and
  an **NVIDIA GPU with CUDA 12.x support** to reach a runtime row comparable to
  the committed evidence — see
  [the README's hardware section](../README.md#hardware-you-need-before-downloading-anything)
  before starting step 3, which downloads 17.7 GB.

The GPU/CUDA driver is only required to *run* the benchmarks (step 4 onward),
not to reach this point.

```sh
git clone <this-repo-url>
cd wave_local_ai_v2
uv sync
uv run pre-commit install
```

`uv sync` is the only command needed to reach the platform-specific steps
below, and it needs no GPU or API key. `uv run pre-commit install` is the
contributor step: it installs both the commit-stage and push-stage hooks in one
command — see `aidd_docs/memory/coding-assertions.md` for what each stage runs.
Running the benchmarks does not require it.

## 2. Get `llama-server`, build `b10537`

Every command below is pinned to `b10537` — the build the committed reference
evidence (`aidd_docs/results/*-reference.jsonl`) was produced under. A
different build is not wrong to use, but its results are not comparable to
the committed evidence without saying so.

All assets are on the release page:
<https://github.com/ggml-org/llama.cpp/releases/tag/b10537>

**Windows, NVIDIA GPU** (matches this project's own laptop fiche):

Download and extract both into the same folder:

- `llama-b10537-bin-win-cuda-12.4-x64.zip`
- `cudart-llama-bin-win-cuda-12.4-x64.zip`

Set `LLAMA_SERVER_PATH` to the extracted `llama-server.exe`.

**Windows, CPU-only** (no NVIDIA GPU):

Download and extract `llama-b10537-bin-win-cpu-x64.zip`. Set
`LLAMA_SERVER_PATH` to the extracted `llama-server.exe`.

**Linux x86_64:**

Download and extract `llama-b10537-bin-ubuntu-x64.tar.gz`. Set
`LLAMA_SERVER_PATH` to the extracted `llama-server`.

Both of the last two are **CPU builds**. They run, and they produce rows, but
those rows measure a different backend than the committed reference evidence,
which was produced on the CUDA build. Just as with the build tag: not wrong to
use, not comparable without saying so.

**Any other platform, or a future build tag missing your asset:**

Build from source per
<https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>, checking
out the matching build tag first. This is not conditioned on today's release
actually missing an asset for your platform — it's the fallback for whenever
one eventually does.

### NVIDIA GPU (documented, untested in CI)

The published container image (see the
[README's pull-and-run section](../README.md#pull-and-run-no-clone)) is
**CPU-only** — it does not ship the CUDA build above. A GPU deployment would
need, instead:

- **Base image:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04` (matching the
  CUDA 12.x this project's hardware section already requires), not
  `python:3.12-slim` — the shipped `Dockerfile` builds the CPU image only.
- **Docker runtime flag:** `--gpus all` (or `--runtime=nvidia`, depending on
  your Docker Engine / NVIDIA Container Toolkit setup).
- **`llama-server` flags that change:** the CPU build's `-ngl 99` and
  `--n-cpu-moe 37` (both in `src/wave_local_ai_v2/server.py`) exist to force
  every layer onto GPU and then push MoE experts back to CPU RAM under a
  6 GB-VRAM ceiling; a GPU deployment with more VRAM would lower or drop
  `--n-cpu-moe` to keep more experts resident on the GPU. There is no second
  set of magic numbers documented here — `server.py`'s constants are the
  bare-metal precedent to start from and re-tune per your own VRAM budget.

**Untested in CI** — no GitHub-hosted runner carries a GPU, so this path is
documented, not built or exercised by this repository's CI.

### Building the image from a clone

`compose.yaml` runs the published image and carries no build section, so that
a reader who pulled the image and fetched that one file never triggers a build
they have no context for. From a clone, layer the developer overlay on top:

```sh
docker compose -f compose.yaml -f compose.build.yaml build
docker compose -f compose.yaml -f compose.build.yaml run --rm runtime
```

The overlay tags the build under the same name `compose.yaml` runs
(`ghcr.io/aliquanto3/wave_local_ai_v2:${WAVE_IMAGE_TAG:-latest}`), so plain
`docker compose run --rm runtime` afterwards reuses the local build instead of
pulling.

### Publishing: the one-time GHCR visibility switch

A package first pushed to GHCR by a workflow's `GITHUB_TOKEN` is **private**,
whatever the repository's own visibility, and there is no API to pre-create a
public user package. After the first `v*` tag publishes, the owner sets it
public once, by hand:

**github.com/Aliquanto3?tab=packages** → `wave_local_ai_v2` → *Package
settings* → *Danger zone* → *Change visibility* → *Public*.

Until that is done, the README's `docker pull` fails with an authentication
error for anyone signed out. It is a one-time step per package, not per
release.

### Docker Desktop memory (WSL2)

Running the full 35B roster model inside a container needs the Docker
Desktop WSL2 VM to actually have enough RAM to load it — the container does
not automatically see the host's full memory. On Windows, Docker Desktop's
default WSL2 memory cap can sit well under the ~18 GB the model file alone
needs; `llama-server` fails at load time (`failed to fit params to free
device memory`) rather than falling back to something smaller. If you hit
this, raise the limit in `%UserProfile%\.wslconfig`:

```ini
[wsl2]
memory=24GB
```

then restart Docker Desktop (or `wsl --shutdown` from PowerShell) for it to
take effect. Even with enough memory, CPU-only inference of a 35B MoE model
inside a container is slow — expect the same order of magnitude as the
bare-metal CPU path in the previous section, not the CUDA-build numbers in
the committed reference evidence.

## 3. Get the model weights and verify the checksum

- Repo: `unsloth/Qwen3.6-35B-A3B-GGUF` on Hugging Face
- Revision: `main` (commit `a483e9e6cbd595906af30beda3187c2663a1118c` at the
  time this was written)
- File: `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf` (17.7 GB)
- sha256: `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3`

Download to this **exact** relative path under `SLM_MODELS_DIR` — it matches
`MODEL_RELATIVE_PATH` in `src/wave_local_ai_v2/__init__.py` and
`quality_cli.py` byte for byte:

```
<SLM_MODELS_DIR>/Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
```

Using the `hf` CLI:

```sh
hf download unsloth/Qwen3.6-35B-A3B-GGUF Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
  --local-dir <SLM_MODELS_DIR>/Qwen3.6-35B-A3B
```

Or the direct URL:
`https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf`

Verify the checksum:

```sh
# POSIX
sha256sum <SLM_MODELS_DIR>/Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
```

```powershell
# Windows
Get-FileHash -Algorithm SHA256 "<SLM_MODELS_DIR>\Qwen3.6-35B-A3B\Qwen3.6-35B-A3B-UD-IQ4_XS.gguf"
```

The output must match `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3`.

## 4. Configure `.env` and run

```sh
cp .env.example .env       # POSIX
copy .env.example .env     # Windows
```

Fill `SLM_MODELS_DIR` (the parent directory from step 3) and
`LLAMA_SERVER_PATH` (the binary path from step 2).

**4.1 — everything up to here runs on a GPU-less container.**

**4.2 — first run, needs a GPU-bearing machine, no cloud credential:**

```sh
uv run wave-local-ai-v2
```

One row lands in `RUNTIME_RESULTS_PATH` (default
`aidd_docs/results/runtime.jsonl`).

**4.3 — second run, set `MISTRAL_API_KEY` first:**

```sh
uv run wave-local-ai-v2-quality
```

One row per (item, model) lands in `QUALITY_RESULTS_PATH` (default
`aidd_docs/results/quality.jsonl`).

`GOOGLE_API_KEY` can be left unset — nothing under `src/` reads it yet, and
both commands run without it.
