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
  suites' identity (id, version, prompt-set hash), caps, thinking policy and
  every item to
  `aidd_docs/results/suite-definitions/<suite_id>@<suite_version>.json`, one
  file per (suite, version): a version bump adds a file beside its
  predecessor rather than overwriting it, so a published row keeps resolving
  to the definition it was produced against. A
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
- `wave-local-ai-v2-serve` — read-only results service: four `GET` routes over
  the two stores, answering the views a pitch screen needs without a terminal.
  Writes nothing: every store file is opened for reading, and every non-`GET`
  method on every route answers `405` with `Allow: GET`.
  - `GET /api/runs` — the run index, as **two separately named collections**
    (`runtime_runs`, `quality_runs`), each with its own `unreadable` count and
    the schema floor in force. The one route that reads both files, and it
    joins nothing.
  - `GET /api/runs/{run_id}/quality` — one entry per quality row, each
    declaring its `score_shape` (`exact_match` or `graded`) and carrying only
    that shape's fields.
  - `GET /api/runs/{run_id}/runtime` — the runtime fields with the row's fiche
    resolved beside it.
  - `GET /api/runs/{run_id}/energy?store=runtime|quality` — the three energy
    channels each beside its own method label, plus the emissions/scope
    fields. `store` is **required**: both row kinds carry the same energy
    fields, so an unnamed or unrecognised store is a `422` naming the
    parameter, never a probe of both. A `run_id` the named store does not
    carry is a `404` naming the run and the store, never an empty list.
  - Every field a row does not carry comes back as a marked absence —
    `{"absent": true, "reason": ..., "detail": {...}}` — over three finite
    reasons: `predates_schema`, `null_in_row`, `pointer_unresolved`. Nothing
    is defaulted, zero-filled or inferred, and the service computes no
    verdict, score, agreement or aggregate.
  - `SERVICE_API_KEY` is **required to start**, unconditionally — a loopback
    bind is not an exemption, and no key value ships in this repo. A loopback
    client is then answered with no header; every other client must send a
    matching `X-API-Key` or gets a `401`. An unparsable peer address counts as
    non-loopback, and no proxy header is read: `main()` passes
    `proxy_headers=False` to uvicorn, whose own default (`True`) would
    otherwise let `X-Forwarded-For` rewrite the peer address the gate reads.
    Serving this behind a reverse proxy is therefore a decision to make
    deliberately, not a default to inherit.
    There is no `/openapi.json`, `/docs` or `/redoc`: FastAPI mounts those
    outside the gated `/api` router, so they are disabled rather than left to
    answer a keyless client with the route list.
  - `SERVICE_HOST` (default `127.0.0.1`), `SERVICE_PORT` (default `8000`) and
    `SERVICE_SCHEMA_FLOOR` (default `7`) are the rest of its configuration; the
    store, roster, fiche-registry and suite-definition paths come from the same
    env vars the benchmark CLIs use. A row below the floor is counted in
    `unreadable` naming its version, never rendered half-populated and never
    dropped. Pointing `RUNTIME_RESULTS_PATH`/`QUALITY_RESULTS_PATH` at
    `aidd_docs/results/*-reference.jsonl` serves the committed bundle with no
    code change.
  - Plain HTTP. TLS and the browser's own side of the key are a later story in
    this epic — this is not the finished posture.

Both benchmark commands stamp every row they write with a `run_id` and a UTC `captured_at`, so the
rows of one invocation are selectable back out of the append-only store. The two
stores are never merged (see `architecture.md`).

## Roster and host settings

Both commands resolve the model to launch through the tracked roster
(`ROSTER_PATH`, default `aidd_docs/roster/models.json`) and select which
entry to use via `ROSTER_ENTRY_ID`. The roster holds four entries at
`roster_version` 2:

| Entry id | Model | Arch | Quant |
| -------- | ----- | ---- | ----- |
| `qwen3.6-35b-a3b-ud-iq4xs` | Qwen3.6-35B-A3B | MoE, 40 experts | `UD-IQ4_XS` |
| `qwen3-0.6b-q8` | Qwen3-0.6B | dense | `Q8_0` |
| `qwen3-1.7b-q8` | Qwen3-1.7B | dense | `Q8_0` |
| `qwen3-4b-q4km` | Qwen3-4B | dense | `Q4_K_M` |

`ROSTER_ENTRY_ID` defaults to the MoE flagship. Running several entries in
turn is a shell loop over the ids, not a runner script: `load_dotenv(override=
False)` leaves a shell-set value in place, and `.env` does not set the
variable at all. Each invocation is its own `run_id`.

Two more env vars set the launch flags that are host-fitted rather than
roster data: `SERVER_THREADS` (default `8`) and `SERVER_N_CPU_MOE`, which has
two states. **Unset** means the selected entry decides — its own
`validated_host.n_cpu_moe`, so `37` for the flagship and *no `--n-cpu-moe` at
all* for a dense entry, whose value is `null`. **Set** overrides the entry,
and a dense entry given any value (`0` included) refuses with a `RosterError`
naming it before anything spawns. See `architecture.md`'s Gotchas for why
these, and not the roster, are the knob to change on different hardware.

## Distribution

- Installed in editable mode via `uv sync` (dev workflow)
- Entry point declared in `pyproject.toml` under `[project.scripts]`
- Not published to PyPI; local benchmark runs only
