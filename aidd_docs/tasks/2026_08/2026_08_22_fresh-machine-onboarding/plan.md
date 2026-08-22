---
objective: "A reader who has just cloned the repo reaches one runtime row and one quality row using only commands and downloads named in README.md, docs/setup.md and CONTRIBUTING.md, with no undocumented fix."
status: implemented
---

# Plan: A fresh machine reaches both benchmarks from the README alone

## Overview

| Field      | Value                                                                                                                          |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------|
| **Goal**   | Write `README.md`, `docs/setup.md`, `CONTRIBUTING.md`; annotate `.env.example`; fix the French `.gitignore` header. No code.  |
| **Source** | `aidd_docs/backlog/stories/a-fresh-machine-reaches-both-benchmarks-from-the-readme-alone.md`                                  |

## Phases

| #   | Phase                                    | File                          |
| --- | ----------------------------------------- | ------------------------------ |
| 1   | README as the entry point                | [`phase-1.md`](./phase-1.md)  |
| 2   | Fresh-machine setup walk + env hygiene    | [`phase-2.md`](./phase-2.md)  |
| 3   | Contribution gate + cross-doc proof       | [`phase-3.md`](./phase-3.md)  |

## Resources

| Source                                                                                              | Verified                                                                                                                                                        |
| ----------------------------------------------------------------------------------------------------| ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `https://github.com/ggml-org/llama.cpp/releases/tag/b10537`                                         | Asset names for build `b10537`: `llama-b10537-bin-win-cuda-12.4-x64.zip` (+ `cudart-llama-bin-win-cuda-12.4-x64.zip`), `llama-b10537-bin-win-cpu-x64.zip`, `llama-b10537-bin-ubuntu-x64.tar.gz` (CPU). All three platforms this story requires have a prebuilt asset for this exact build; no platform needs the source-build fallback for `b10537` itself, but the fallback is still documented for a future build tag that drops one. |
| `https://huggingface.co/api/models/unsloth/Qwen3.6-35B-A3B-GGUF?blobs=true` (raw JSON, fetched via `curl`, not the summarizing fetch) | File `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf`, size 17730509792 bytes, LFS `sha256` `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3`, repo commit `a483e9e6cbd595906af30beda3187c2663a1118c` on `main`. Matches `MODEL_RELATIVE_PATH` in `src/wave_local_ai_v2/__init__.py:26` and `quality_cli.py:29` exactly. |
| `src/wave_local_ai_v2/server.py:23-35`                                                              | This machine's flag values to disclose as such (not portable): `N_CPU_MOE = 37`, `THREADS = 8`, `CONTEXT_SIZE = 32768`, `-ngl 99`, `-fa on`, `--load-mode none`, `-np 1`, sampler flags. |
| `src/wave_local_ai_v2/settings.py`, `.env.example`                                                  | Every `.env` key read: `SLM_MODELS_DIR`, `LLAMA_SERVER_PATH` (both `_require_existing_path`), `RUNTIME_RESULTS_PATH`, `QUALITY_RESULTS_PATH` (both optional, defaulted), `MISTRAL_API_KEY` (optional at load, required by `quality_cli.py:98` before the quality run). `GOOGLE_API_KEY` is read by nothing under `src/` (`grep -rn GOOGLE_API_KEY src` empty). |
| `pyproject.toml` `[project.scripts]`                                                                | `wave-local-ai-v2` and `wave-local-ai-v2-quality` are the only two entry points; names to match verbatim in docs. |
| `aidd_docs/memory/architecture.md`, `context_input/hardware.md`                                     | Energy caveat wording and the roster model's minimum hardware (32 GB RAM, NVIDIA GPU, ~18 GB free disk for weights + binary — sized off the laptop fiche, the smallest machine the evidence was produced on). |

## Decisions

| Decision                                                                                  | Why                                                                                                                                                                            |
| ------------------------------------------------------------------------------------------| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GOOGLE_API_KEY` stays in `.env.example`, documented as reserved, not removed.            | `model_candidates.md` names Google AI as the planned second judge; deleting the key would silence a roadmap item the story only asks to disambiguate, not cancel.           |
| The full fresh-machine walk lives in `docs/setup.md`; `README.md` links it rather than inlining every command. | The story's own file list separates them, and a first-time reader needs the pitch and audience before the command list; the acceptance criteria that need copy-pasteable commands apply to whichever page carries them, not to README specifically. |
