# CLI

The command-line interface for running benchmarks.

## Commands

- `wave-local-ai-v2` — runtime benchmark: launches llama-server, sends one fixed
  prompt, appends one row (hardware fiche, timings, GPU stats, energy) to
  `aidd_docs/results/runtime.jsonl`
- `wave-local-ai-v2-quality` — quality benchmark: scores the classification suite
  against the local SLM and the Mistral cloud model, appending one row per
  (item, model) to `aidd_docs/results/quality.jsonl`

Both stamp every row they write with a `run_id` and a UTC `captured_at`, so the
rows of one invocation are selectable back out of the append-only store. The two
stores are never merged (see `architecture.md`).

## Distribution

- Installed in editable mode via `uv sync` (dev workflow)
- Entry point declared in `pyproject.toml` under `[project.scripts]`
- Not published to PyPI; local benchmark runs only
