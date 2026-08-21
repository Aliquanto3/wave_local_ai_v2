# Architecture

The macro technical shape: the stack, how the pieces fit, and the decisions behind them.

## Stack

- Python, managed by uv (lockfile, fast installs, editable dev install)
- pytest for tests, mypy for type checking, ruff for linting and formatting
- pre-commit wires the fast gate (ruff + mypy) before every commit

## How it fits together

```mermaid
flowchart LR
    CLI["CLI benchmark runner"]
    Llama["llama.cpp server\n(localhost:8080)"]
    Cloud["Cloud APIs\n(Mistral · Google AI)"]
    Results["Results store\n(quality · runtime)"]
    HF["Hugging Face\n(model download)"]

    CLI --> Llama
    CLI --> Cloud
    CLI --> Results
    HF --> Llama
```

## Key decisions

- **llama.cpp over Ollama**: direct control over inference flags (`--n-cpu-moe`, `-fa`, `--jinja`, etc.), quantization choice, and memory layout; Ollama abstracts these away.
- **uv over pip**: reproducible installs via lockfile, faster CI, single tool for venv + deps + scripts.
- **Two cloud providers for LLM-as-a-judge**: Mistral and Google AI are from different model families; inter-judge agreement is reported alongside judged scores, making them defensible to clients.
- **Quality / runtime split**: quality scores are reproducible (model + prompt + seed); runtime metrics are hardware-bound and must be tagged with a signed hardware fiche. The two are never merged into a single table.

## Gotchas

- Runtime metrics are NOT reproducible across machines. Every result row must carry its hardware fiche (CPU, RAM, GPU, driver, llama.cpp build, quant, flags). A number without a fiche is meaningless.
- llama.cpp has architecture-specific flags that are not optional: `--load-mode none` is required when `--n-cpu-moe` is set (otherwise mmap pages from disk), `--jinja` is required for `<think>` tag parsing, `-np 1` avoids the 4-slot default allocation.
- MoE models (e.g. Qwen3) have a fixed number of experts; `--n-cpu-moe` has a hard ceiling and sweep gains are typically within measurement noise.
