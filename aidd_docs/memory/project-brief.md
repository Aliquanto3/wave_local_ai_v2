# Project Brief

What this project is, the problem it solves, and its domain language.

## What it is

- A reproducible benchmark suite that compares small language models running locally via llama.cpp against cloud LLM APIs, across shared task suites, measuring both runtime cost and per-task quality.
- Audience: clients evaluating on-prem vs cloud LLM deployments.

## Why it exists

- Clients need defensible comparisons, not anecdotes. Reproducible scores with signed hardware fiches and inter-judge agreement make results auditable.
- Predecessor (v1: Streamlit + Ollama) validated the model-registry pattern, CodeCarbon Green IT config, and LLM-as-a-judge approach. v2 replaces Ollama with llama.cpp for lower-level control, pip with uv, and Streamlit with FastAPI + React.

## Domain language

| Term | Meaning |
| ---- | ------- |
| SLM | small language model running locally via llama.cpp |
| task suite | a labelled set of prompts covering one capability (e.g. classification, translation) |
| hardware fiche | a signed record of CPU, RAM, GPU, driver, llama.cpp build, quant, and flags for one run |
| quality score | a per-task metric that is reproducible given model + prompt + seed |
| runtime metric | a per-run metric bound to a hardware fiche: TTFT, tokens/s, RAM/VRAM, energy, carbon |
| TTFT | time to first token |
| quant | quantization format of a GGUF model file (e.g. IQ4_XS, Q3_K_XL) |
| GGUF | the model file format llama.cpp loads |
| MoE | mixture-of-experts architecture; affects expert routing, CPU offload, and VRAM usage |
| LLM-as-a-judge | using two cloud LLMs from different families to score open-ended outputs; inter-judge agreement makes scores defensible |
| inter-judge agreement | the degree to which Mistral and Google AI reach the same verdict; reported alongside judged scores |

## Key features

- CLI benchmark runner: launch llama.cpp, run task suites, collect results
- Runtime instrumentation: TTFT, tokens/s, RAM/VRAM via llama.cpp server metrics, energy and carbon via CodeCarbon
- Quality scoring: deterministic metrics where possible; LLM-as-a-judge (Mistral + Google AI) for open-ended tasks
- On-prem vs cloud comparison: same task suites run against local SLMs and cloud APIs
- Results split by design: `quality` table (reproducible) and `runtime` table (hardware-bound, tagged with hardware fiche)
