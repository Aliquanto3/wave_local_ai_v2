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
```

`uv sync` is the only command needed before the platform-specific steps below,
and it needs no GPU or API key.

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
