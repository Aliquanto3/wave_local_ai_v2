# CLI

The command-line interface for running benchmarks.

## Commands

- `wave-local-ai-v2` — runtime benchmark: launches llama-server once, runs one
  warm-up plus N counted repetitions of the fixed prompt (a cooldown between
  them, a pinned seed, `cache_prompt: false` forcing a full prefill every
  time), and appends one row (hardware fiche, median/mean/sd + peak
  aggregates, the raw ordered repetitions, energy) to
  `aidd_docs/results/runtime.jsonl`. `RUNTIME_REPETITIONS` (default 5),
  `RUNTIME_COOLDOWN_S` (default 10.0) and `RUNTIME_WARMUP_COUNT` (default 1)
  override the protocol. A failing repetition fails the whole row: nothing
  is written.
- `wave-local-ai-v2-quality` — quality benchmark: scores the classification suite
  against the local SLM and the Mistral cloud model, appending one row per
  (item, model) to `aidd_docs/results/quality.jsonl`

Both stamp every row they write with a `run_id` and a UTC `captured_at`, so the
rows of one invocation are selectable back out of the append-only store. The two
stores are never merged (see `architecture.md`).

## Roster and host settings

Both commands resolve the model to launch through the tracked roster
(`ROSTER_PATH`, default `aidd_docs/roster/models.json`) and select which
entry to use via `ROSTER_ENTRY_ID` (default `qwen3.6-35b-a3b-ud-iq4xs`, the
shipped baseline entry). Two more env vars set the launch flags that are
host-fitted rather than roster data: `SERVER_N_CPU_MOE` (default `37`) and
`SERVER_THREADS` (default `8`) — see `architecture.md`'s Gotchas for why
these, and not the roster, are the knob to change on different hardware.

## Distribution

- Installed in editable mode via `uv sync` (dev workflow)
- Entry point declared in `pyproject.toml` under `[project.scripts]`
- Not published to PyPI; local benchmark runs only
