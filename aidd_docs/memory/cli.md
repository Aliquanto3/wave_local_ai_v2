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
- `wave-local-ai-v2-quality` — quality benchmark: scores the 20-item
  classification suite (`en`/`fr`/`de`, each >=25% share) against the local
  SLM and up to two cloud models (`QUALITY_PROVIDERS`, default
  `local,mistral,google`), appending one row per (item, model) to
  `aidd_docs/results/quality.jsonl`. Every row carries `language_breakdown`
  (`scoring.score_suite_by_language`): per-language accuracy/n/indicative,
  the same batch-level pattern `suite_accuracy` uses.
  - Each cloud provider's requests are paced (`MISTRAL_REQUEST_PACING_S`,
    default `1.1`; `GOOGLE_REQUEST_PACING_S`, default `4.1`, seconds between
    requests) and retried with backoff on a 429/5xx up to
    `CLOUD_RETRY_MAX_ATTEMPTS` (default `4`, shared across the whole batch,
    not per item) before that provider is skipped — the same
    skip-not-abort contract as a missing key or a pre-flight failure. Every
    row records how many retries it took (`retries`).
  - `--resume <run_id>` re-runs a prior invocation under its own id instead
    of minting a fresh one: a provider whose rows for that `run_id` are
    already all on disk is skipped (`"<provider> skipped: run <run_id>
    already complete"`), never re-paid for; an incomplete one (including
    `local`) is re-run from item 1. Every row a `--resume` invocation writes
    is marked `resumed: true`, even a provider it re-ran from scratch, and
    even when the given `run_id` was never used before (behaves like a
    fresh run, honestly marked resumed anyway).
- `uv run python -m wave_local_ai_v2.suite_snapshot` — exports the
  classification suite's identity (id, version, prompt-set hash), caps and
  every item to `aidd_docs/results/suite-definitions/<suite_id>.json`. A
  snapshot of the suite as the code holds it at export time, not a live
  registry a row resolves through at read time; re-run after any suite edit.
  No `pyproject.toml` entry point — invoked as a module, not a CLI command.
- `wave-local-ai-v2-validate` — invalidation validator: checks every row of
  one or more results files (default: the two live stores,
  `RUNTIME_RESULTS_PATH`/`QUALITY_RESULTS_PATH`) against the stored fiche
  registry (`FICHE_REGISTRY_DIR`, default `aidd_docs/results/fiches/`).
  Three classes: `edited` (a stored fiche no longer hashes to its own
  filename; names the changed field(s) via `git show HEAD:...` when the
  registry is git-tracked), `missing` (a row cites a hash absent from the
  registry, or has no `fiche_hash` at all despite being at or past
  `row_contract.FICHE_HASH_SCHEMA_VERSION`), and the non-fatal `legacy`
  (a row predating that schema version — its absent `fiche_hash` is
  expected, not an integrity failure). Exits `1` on any `edited`/`missing`
  row, `0` otherwise, printing the checked count.

Both benchmark commands stamp every row they write with a `run_id` and a UTC `captured_at`, so the
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
