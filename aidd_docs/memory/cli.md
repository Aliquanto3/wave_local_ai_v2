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
- `wave-local-ai-v2-quality` — quality benchmark: scores one selectable task
  suite against the local SLM and up to two cloud models
  (`QUALITY_PROVIDERS`, default `local,mistral,google`), appending one row
  per (item, model) to `aidd_docs/results/quality.jsonl`.
  - `--suite` picks the suite, `choices=classification|translation`, default
    `classification` — so every invocation written before the flag existed
    behaves identically. `_SUITES` is a two-entry `SuiteSpec` dispatch table
    in `quality_cli.py` (items, identity, caps, batch scorer), deliberately
    not a registry: that belongs to the use-case epic.
    - `classification`: 20 support messages routed into one of four labels
      (`en`/`fr`/`de`, each >=25% share), 32 output tokens, scored by exact
      label match. Publishes `correct`, `suite_accuracy` and
      `language_breakdown` (`scoring.score_suite_by_language`: per-language
      accuracy/n/indicative). Prints `accuracy=`.
    - `translation`: 21 hand-written short business sentences in three
      directions (`en→fr`, `fr→de`, `de→en`, seven each, so each *source*
      language is 33%), 128 output tokens, scored by an in-repo chrF
      (`chrf.py`, sacreBLEU's defaults, published on `0..1`) against a
      hand-written reference. Publishes the graded block — `item_score`,
      `suite_score`, `score_breakdown` (per source language:
      score/n/indicative), `metric_id`/`metric_version`/`metric_params`,
      `reference_output` and `subject_output` — and nulls `correct`,
      `suite_accuracy` and `language_breakdown`. Prints `suite_score=`.
      `unparseable` is structurally unreachable (no closed set, no
      extraction step) and its count stays 0.
  - One row never carries both score shapes (`row_contract` refuses it):
    select on `task_suite` before comparing any score column. A
    single-reference chrF compares models against identical references, not
    translation quality absolutely.
  - Each cloud provider's requests are paced (`MISTRAL_REQUEST_PACING_S`,
    default `1.1`; `GOOGLE_REQUEST_PACING_S`, default `4.1`, seconds between
    requests) and retried with backoff on a 429/5xx up to
    `CLOUD_RETRY_MAX_ATTEMPTS` (default `4`, shared across the whole batch,
    not per item, and counted as retries beyond the first attempt) before
    that provider is skipped — the same skip-not-abort contract as a missing
    key or a pre-flight failure. Every row records how many retries it took
    (`retries`).
  - `--resume <run_id>` re-runs a prior invocation under its own id instead
    of minting a fresh one: a provider whose rows for that `run_id` **and
    this suite** are already all on disk is skipped (`"<provider> skipped:
    run <run_id> already complete"`), never re-paid for; one with no rows at
    all (including `local`) is re-run from item 1. A provider holding *some*
    of the suite's items is skipped too (`"... is partially written (N/M
    items); re-running would duplicate them"`): resume works per
    `(run_id, provider, task_suite)` batch, so re-running it would write a
    second row for every item already on disk. The `task_suite` element is
    load-bearing now that one store holds two suites — a classification
    `run_id` is not evidence about a translation batch that never ran. Every
    row a `--resume` invocation writes is marked `resumed: true`, even a
    provider it re-ran from scratch, and even when the given `run_id` was
    never used before (behaves like a fresh run, honestly marked resumed
    anyway).
- `uv run python -m wave_local_ai_v2.suite_snapshot` — exports **both**
  suites' identity (id, version, prompt-set hash), caps and every item to
  `aidd_docs/results/suite-definitions/<suite_id>.json`, one file each. A
  snapshot of each suite as the code holds it at export time, not a live
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
