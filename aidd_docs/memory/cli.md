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
  - `--suite` takes a registered suite id, default
    `classification-support-routing` — so an invocation without the flag
    behaves as before. `suite_registry.resolve` answers it from the data
    definitions in `src/wave_local_ai_v2/suite_data/<suite_id>.json` (id,
    version, `task_suite`, the four generation constraints, the scoring-rule
    name, the declared `level`, the items with their tags), gated by
    `suite_gate.gate_suite` at load. A `development` suite below the
    thresholds publishes indicative; a `publication` suite that falls short
    of its 100-item floor, its declared `size_target`, the 25% share or a
    per-item `licence`/`source`/`source_revision` is refused. Every row
    names its `suite_level`. An unregistered id (including the old `classification` /
    `translation` values) or an unknown scoring rule is refused as one stderr
    line naming what is wrong. `quality_cli.py` holds no suite table and
    imports no suite: a further suite is a new data file plus, only where its
    scoring differs, a new entry in `scoring_rules.SCORING_RULES`. Unknown
    top-level and item keys are carried as data (`SuiteDefinition.extra`, the
    item mapping) and exported in the snapshot.
  - `--prompt-variant VARIANT_ID[@VERSION]` names the registered prompt
    variant (`prompt_variants.py`) every item runs under, default `baseline`,
    latest version when none is given; an unregistered id or version exits
    `1` before any process. A variant may declare the task families it
    `applies_to`: every item of the suite still runs, and outside those
    families the authored prompt is sent unchanged and each row states
    `prompt_variant_noop: true` (quality rows, schema "27"). `baseline` v1
    applies everywhere; `output_compressed` v1 appends a terse-output
    instruction on `classification` and is a no-op on `translation`;
    `constrained_output` v1 sends a GBNF grammar admitting only the closed
    label set with each `classification` answer (no instruction added) and
    is a no-op on `translation`. Each quality row names
    `constraint_mechanism` (`gbnf` or `none`) and `constraint_grammar_hash`
    (schema "28"). A constraining variant exits `1` before any process when
    the engine declares no request field for its mechanism or when a cloud
    provider is enabled: run it with `QUALITY_PROVIDERS=local`. Under a
    campaign the variant must be one it declares, and a campaign pairing a
    constraining variant with an engine declaring none of its mechanisms is
    refused at load.
    - `classification-support-routing` (`task_suite` `classification`, rule
      `exact_label_match`): 20 support messages routed into one of four labels
      (`en`/`fr`/`de`, each >=25% share), 32 output tokens, scored by exact
      label match. Publishes `correct`, `suite_accuracy` and
      `language_breakdown` (`scoring.score_suite_by_language`: per-language
      accuracy/n/indicative). Prints `accuracy=`.
    - `translation-business-short-form` (`task_suite` `translation`, rule
      `chrf_against_reference`): 21 hand-written short business sentences in three
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
    - `code-generation-python-javascript` (`task_suite` `code-generation`,
      rule `unit_tests_pass`): 24 hand-written function tasks, 12 Python and
      12 JavaScript, instructions 8 each in `en`/`fr`/`de`, 512 output
      tokens. The first fenced block of the answer (else the whole answer)
      runs against the item's tests in a Docker container
      (`code_sandbox.py`: `--pull never`, `--network none`, no mount,
      read-only root, `tmpfs` workdir, user 65534, 256 MiB, 64 pids, 20 s
      wall clock enforced by an in-container watchdog, host kill and
      `rm -f` only past a grace), run from the image's resolved local id;
      JavaScript under `node --test`. A pass needs exit 0 and a per-run
      nonce reached after the last test, so code that exits 0 before its
      tests ran fails. Item 1.0 when every test passes, else 0.0 with `compile_error`/`tests_failed`/`timeout` beside
      the shared reasons. Publishes the graded block (tests as
      `reference_output`) plus the code block (schema "30"):
      `programming_language`, `sandbox` (runtime, image, image id, caps) and
      `programming_language_breakdown` (a cell only per tagged language).
      Images: `CODE_SANDBOX_PYTHON_IMAGE` (default `python:3.12-slim`) and
      `CODE_SANDBOX_NODE_IMAGE` (default `node:22-slim`), local only. No
      `docker` on PATH, no daemon or a missing image exits `1` as one line
      before settings or any process; generated code never runs on the host.
  - One row never carries both score shapes (`row_contract` refuses it):
    select on `task_suite` before comparing any score column. A
    single-reference chrF compares models against identical references, not
    translation quality absolutely.
  - Each cloud provider's requests are paced (`MISTRAL_REQUEST_PACING_S`,
    default `1.1`; `GOOGLE_REQUEST_PACING_S`, default `4.1`, seconds between
    requests) and retried with backoff on a 429/5xx under a batch retry
    budget derived from the number of items the invocation calls for:
    `max(CLOUD_RETRY_MIN_RETRIES, ceil(items * CLOUD_RETRY_RETRIES_PER_ITEM))`
    (defaults `4` and `0.2`: 4 for a 20-item batch, 20 for 100, 60 for 300;
    shared across the whole batch, counted as retries beyond the first
    attempt). A refusal (a model absent from the catalog, a 400) is never
    retried whatever the budget. Every row records how many retries it took
    (`retries`) and the budget each cloud provider's calls drew from
    (`retry_budget`, `{}` on a local row).
  - A cloud failure before the first item (pre-flight, missing key) skips
    the provider and writes nothing. A failure **mid-batch** (provider
    error, transport error, exhausted budget) stops the batch at that item:
    the items already answered are written, each marked `partial_failure`
    (`provider`, `item_id`, `reason`) with its suite-level score `null`, and
    stderr says `"<provider> partial: run <run_id> failed on item '<id>'
    ..."`; no headline is printed. A failure on the first item writes
    nothing (`"<provider> skipped: failed on item '<id>': ..."`). The run
    still exits 0. A local failure still aborts the run.
  - `--resume <run_id>` re-runs a prior invocation under its own id instead
    of minting a fresh one and works **per item**: for each provider it
    issues calls only for the suite items that `(run_id, provider,
    task_suite)` never wrote (`results.resume_missing_items`) and appends
    their rows; a provider with every item on disk is skipped (`"<provider>
    skipped: run <run_id> already complete"`), never re-paid for. Rows
    already on disk are never rewritten. A resume whose earlier rows were
    written under another configuration (`model_id`, `suite_version`,
    `prompt_set_hash`, `prompt_variant_id`/`_version`, `sampling`,
    `roster_entry_id`, `endpoint`, `thinking_policy`; on the probe also the
    judge model ids) is refused before anything runs, naming the field, and
    exits 1 writing nothing. A batch the resume completes
    publishes its suite-level score over every item (prior rows plus new),
    through the same per-rule aggregate an uninterrupted batch uses; one
    that fails again stays partial and names the new failing item. Cost and
    token totals on a resumed segment's rows cover that invocation's calls
    only: sum the segments for the batch's cost. The `task_suite` element
    is load-bearing now that one store holds two suites — a classification
    `run_id` is not evidence about a translation batch that never ran. Every
    row a `--resume` invocation writes is marked `resumed: true`, even when
    the given `run_id` was never used before (behaves like a fresh run,
    honestly marked resumed anyway). `wave-local-ai-v2-judge-probe
    --resume` follows the same rule: a judge failure writes the items
    already judged as partial (exit 1), and the resume generates and judges
    only the missing items, so no recorded judge call is issued again.
- `uv run python -m wave_local_ai_v2.suite_snapshot` — exports **every
  registered** suite's identity (id, version, prompt-set hash), caps, thinking policy and
  every item to
  `aidd_docs/results/suite-definitions/<suite_id>@<suite_version>.json`, one
  file per (suite, version): a version bump adds a file beside its
  predecessor rather than overwriting it, so a published row keeps resolving
  to the definition it was produced against. A
  snapshot of each registered definition at export time (its data plus the
  computed `prompt_set_hash`, without the scoring-rule name or `task_suite`),
  not what a run resolves through; re-run after any suite edit. An existing
  file with different content is refused (exit `1`, nothing written): a
  changed definition takes a version bump.
  No `pyproject.toml` entry point — invoked as a module, not a CLI command.
- `uv run python -m wave_local_ai_v2.use_case_coverage` — publishes the
  use-case coverage record (`src/wave_local_ai_v2/use_case_coverage.json`,
  one declared state per PRD use case) to
  `aidd_docs/results/use-case-coverage.json`, only when every entry
  resolves; otherwise exits `1`, writes nothing and names every failing
  entry (missing, no state, a suite id `suite_registry` does not resolve,
  an out-of-scope entry without a reason). `--record`/`--output` override
  the two paths. Module invocation, like `suite_snapshot`.
- `uv run python -m wave_local_ai_v2.subset_replay (--suite <id> | --definition
  <path>) --source <rows.jsonl>` — replays a drawn suite's recorded
  `selection_rule` (`subset_sampler.py`, sampler version `1`) over a source
  table, one JSON row per line carrying `source`, `language`, the rule's
  stable source key and content fields. Exits `0` when the redraw gives the
  same item ids in the same order and every item's text still matches its
  `content_hash`; exits `1` naming the first differing position, every item
  whose hash moved, every item the source no longer holds, or why nothing
  could be replayed (no rule, unreadable source, an unfillable stratum). The
  recorded loader and generator (`CPython random.Random` + major.minor) are
  printed, not enforced: rows are put in canonical order
  (source, then stable key) before sampling, so their arrival order is
  irrelevant. Module invocation, like `suite_snapshot`.
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
- `wave-local-ai-v2-export --output-dir <dir>` — the published bundle as five
  flat CSV tables (`quality_items`, `runtime_aggregates`, `fiches`, `roster`,
  `comparison_records`), `column_dictionary.csv` and `bundle_manifest.csv`
  (`bundle_export.py`, standard library only). `comparison_records` holds one
  row per family record, comparison, leader-set record and leader-set subject
  read from `comparisons/` and `leader-sets/` (`--comparisons-dir`,
  `--leader-sets-dir`), named by `record_kind`. A missing record directory holds
  no record of its kind (header-only table, kinds named `carried=false`, 0
  entries in the manifest); a malformed record, or one citing a run or record
  the bundle read does not hold, refuses the export. Reads the committed reference bundle by default,
  never the live stores unless pointed at them; every pointer is resolved into
  columns, nothing is computed, absence stays an empty cell listed in the
  row's `fields_not_carried`, and the manifest declares the `schema_version`
  the rows carry, not the live constant. A row field the dictionary does not
  describe refuses the export; see `aidd_docs/results/README.md`. The record
  columns' meaning, unit and null reasons are read from `comparison.py` and
  `leader_set.py`, never defined in the export.
- `uv run python scripts/recompute_from_export.py <export-dir>` — the
  third-party check over an export directory alone (standard library, imports
  nothing from the package): recomputes every interval block, every
  `mcnemar_exact` comparison and each family's Holm-adjusted p from the CSVs,
  prints each value beside the published cell, exits `1` on any difference.
- `uv run python scripts/assemble_release_archive.py build --tag v<x.y.z>
  --commit <sha> --output-dir <dir> [--parquet]` (and `verify --tag --commit
  [--parquet] <zip>`) — the release archive the `release-build` CI job builds
  and verifies (read-only token) on a `v*` tag and on demand
  (`workflow_dispatch`), and `release-publish` (the only `contents: write`
  job, tag push only, no project code) attaches to the Release: the export
  regenerated from the committed bundle, the bundle parts at their repository
  paths, both licences, `CITATION.cff` stamped with the commit and a README.
  Refuses a tag, packaged version, citation version or `HEAD` that disagree,
  a table that differs from the regenerated export, and a file naming a
  repository path the archive does not hold outside `PATHS_NOT_SHIPPED`.
  `--parquet` (always passed by the job; needs the `release` dependency
  group's pinned `pyarrow`, `uv sync --locked --group release`) adds one typed
  Parquet copy per table (`scripts/release_parquet.py`, types from the
  dictionary's `unit`) and refuses any copy that differs from its CSV in a
  cell, printing one "compared ... equal" line per table.
- `wave-local-ai-v2-compare (--reference <run_id> --candidate <run_id>
  [--reference-where field=value ...] [--candidate-where field=value ...] |
  --comparisons <declaration.json>) [--dimension model|prompt_variant]
  [--quantity score|item_tokens_in|item_tokens_out|item_ttft_ms|energy_kwh]
  [--alpha 0.05] [--rows <jsonl>] [--records-dir <dir>] [--output <path>]`
  — paired comparison (`comparison.py`) over the published quality rows
  (default `quality-reference.jsonl`, read-only). Writes one immutable family
  record per invocation (one suite by one dimension; comparisons spanning two
  suites refuse the invocation, exit `1`) to `aidd_docs/results/comparisons/<suite>@<version>.<dimension>.<family_id[:12]>.json`,
  holding every declared comparison (a JSON array of `{reference: {run_id,
  where}, candidate: {...}}`, or the one pair the flags name), its size,
  tested and refused counts, and each member's Holm-adjusted p over the
  members not refused (a null p counted as 1, so the adjustment size equals
  the tested count), the verdict read against it. A grown family is a new
  record listing the ids it `supersedes`, found among the records in
  `--records-dir` (default `comparisons/`); a declaration leaving out any
  comparison of the current record is refused (exit `1`): a family only
  grows. A re-run matching a published record re-emits it. Each comparison is
  McNemar's exact test when the rows score `correct`, Wilcoxon signed-rank
  (Pratt zeros, exact sign-flip up to 50 non-zero pairs, no continuity
  correction) when they score `item_score` — chosen from the row shape, never
  by flag. A member is refused (still listed, exit `0`) naming each field when its sides
  differ on suite identity, `suite_level`, a generation constraint, the metric
  triple, the scoring kind or the compared field, and when a constraint or the
  metric is null on either side. Sides differing outside the declared
  dimension publish an observation naming the confound, verdict `not
  comparable` (its p kept in `result`). Along `model`, `engine_id` and
  `engine_build` (schema "22") move with the axis only between a local and a
  cloud side; two local sides on another engine or build are confounded.
  `--quantity` (default `score`)
  compares a per-item measurement instead (schema "18" rows): the item's own
  tokens in or out, or its engine-reported first-token time, scoring kind
  `continuous_measurement`, Wilcoxon signed-rank over the same item ids; a
  member is refused when a side's rows do not carry the field or the two
  sides' `item_measurement_kind` / `item_ttft_source` labels differ.
  `--quantity energy_kwh` publishes each side's per-batch energy and their
  difference as an observation whose reason says why there is no paired test
  (energy is per batch; per-item energy is below tracker resolution). The
  quantity is part of the family (`family_definition.compared_quantity`,
  named in the file name only off the default), so score records keep their
  shape. A reader drops the batch's cold first item with
  `--reference-where item_first_in_batch=false --candidate-where
  item_first_in_batch=false`. No timestamp: a
  re-run is byte-identical; a different existing file is refused (exit `1`);
  no published record is rewritten.
  - `--leader-sets [--leader-sets-dir <dir>] [--fiche-registry-dir <dir>]`
    replaces the declared comparisons (`leader_set.py`): per suite and machine
    class (the fiche's `machine_id`, `compute_mode`, `cpu`, `ram_gb`,
    `gpu_name`, `os`, absent ones listed as not recorded) it takes the local
    subject (`run_id` + `model_id`) with the highest published suite score
    (tie: first `(run_id, model_id)`), grows the suite's `model` family by the
    comparisons against it, and writes one leader-set record per group to
    `aidd_docs/results/leader-sets/<suite>@<version>.<id[:12]>.json`: each
    subject `member`, `excluded` or `not compared` (record `incomplete`). Cloud
    subjects never enter. Superseded by `leader_set_id`, never edited; a
    re-run reports every record `unchanged`.
- `wave-local-ai-v2-candidate-gate --candidate <declaration.json> [--records
  <jsonl>]` — the roster's verification gate (`candidate_gate.py`): one
  declared candidate through seven steps, cheapest first, first failure stops
  (commit-sha revision and file on the hub, licence read and scanned for a
  benchmark-publication ban, disk headroom, download with sha256/bytes/GGUF
  architecture/total params read off the bytes, one load under the probed
  build, `/props` template plus the declared thinking control verified,
  EN/FR/DE claim recorded). Appends one record to
  `aidd_docs/roster/candidate-records.jsonl`: `passed` with the full entry
  block, `refused`, or `deferred` (unknown architecture under the pinned
  build). Never writes `models.json`; exits `0`/`1`/`2` (pass / recorded
  refusal / nothing recorded). See `docs/setup.md` 3.2.
- `wave-local-ai-v2-composition-check [--roster <models.json>]` — Methodology
  13's composition rule (`composition_check.py`): per size class the families
  it spans, dense/MoE presence, the single-family-ladder label and the MoE
  declaration, then per entry its figures and licence terms. Exits `1` naming
  the class or entry when a class spans one family unlabelled, has no MoE and
  no reason, or an entry lacks a resolvable family, class, figures or licence,
  or its class disagrees with its total parameters; `2` when the roster does
  not load. Run before a roster table is published; not in the merge gate
  while the shipped roster fails it (four unlabelled `qwen` classes, quoted in
  `aidd_docs/results/README.md`).
- `wave-local-ai-v2-promote --run-id <id> [--run-id <id> ...] [--machine
  <machine_id>]` — copies the named runs' rows from the live stores
  (`RUNTIME_RESULTS_PATH`, `QUALITY_RESULTS_PATH`) line-for-line into the
  machine's tracked location `<MACHINE_RESULTS_ROOT>/<machine_id>/` (default
  root `aidd_docs/results/machines`; machine from `--machine` or `MACHINE_ID`)
  and their fiches file-for-file from `FICHE_REGISTRY_DIR` into
  `TRACKED_FICHE_REGISTRY_DIR` (default `aidd_docs/results/fiches`)
  (`machine_results.py`). All or nothing: exits `1`, writing nothing, on an
  undeclared machine, a `run_id` with no row, a row whose `machine_id` is not
  the machine's (a cloud subject's `not_applicable` quality row is accepted),
  or a fiche absent from the live registry or differing from the tracked copy.
  Idempotent. Loads no model settings.
- `wave-local-ai-v2-merge-bundle [--check] [--bundle-dir <dir>]` — derives
  the published bundle (`runtime-reference.jsonl`, `quality-reference.jsonl`,
  `refusals-reference.jsonl`; `RUNTIME_REFERENCE_PATH`,
  `QUALITY_REFERENCE_PATH`, `REFUSALS_REFERENCE_PATH`, or all three in
  `--bundle-dir`) from every declared machine's location, lines unchanged, in
  sorted machine order (`bundle_merge.py`). Exits `1`, writing nothing, on a
  fiche-hash collision (two rows, two machine ids, one hash: both named,
  neither chosen), an undeclared machine id or location, a misfiled row or
  refusal, a row with no `run_id`, or one `run_id` in two locations; refuses
  to overwrite the pinned schema-"7" snapshot. `--check` writes nothing and exits `1` when the
  committed bundle differs (line endings normalised); CI runs it.
- `wave-local-ai-v2-campaign-completeness --campaign <id> [--campaigns-dir
  <dir>] [--rows <jsonl> ...]` — Methodology 22's completeness check
  (`campaigns.py`). A campaign is one tracked declaration,
  `aidd_docs/campaigns/<campaign_id>.json` (`CAMPAIGNS_DIR`; the file stem is
  the id, `none` is reserved): `engines`, `prompt_variants` (`{id,
  version}`), `roster_entries`, `suites`, one `machine` (`{machine_id,
  compute_mode}`) and `exclusions` (cells `refused` or `dropped`, each with
  `reason` and `evidence`; an omitted coordinate covers every declared value
  on its axis). Loading refuses, naming the value, more than 2 engines or 4
  variants, an id absent from its registry, an engine entry the engine
  registry refuses, an unknown key, and a cell excluded twice. The command
  lists every cell (engine x variant x roster entry x suite, declaration
  order) as `filled` with its sorted run ids, `refused`/`dropped` with its
  reason, `empty`, or `contradicted` (excluded yet holding rows), from the
  quality rows (`--rows`, repeatable; default `QUALITY_RESULTS_PATH`) whose
  `campaign_id`, engine, variant, roster entry, suite, machine and mode all
  match. Exits `1` naming each empty or contradicted cell, `2` when the
  declaration or a rows file does not load. Runtime rows name no suite and
  fill no cell. A later dimension (the harness list) extends this one
  declaration and its cell product.
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
    `{"absent": true, "reason": ..., "detail": {...}}` — over four finite
    reasons: `predates_schema`, `null_in_row`, `pointer_unresolved`,
    `not_applicable` (a `cpu_only` row's VRAM). Nothing
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
    dropped. `LEADER_SETS_DIR` (default `aidd_docs/results/leader-sets`) is
    where the overview reads each suite's current leader-set record. Pointing `RUNTIME_RESULTS_PATH`/`QUALITY_RESULTS_PATH` at
    `aidd_docs/results/*-reference.jsonl` serves the committed bundle with no
    code change.
  - Plain HTTP. TLS and the browser's own side of the key are a later story in
    this epic — this is not the finished posture.
  - The demo console (`demo_console.py`), the one non-`GET` surface: off
    unless `SERVICE_DEMO_MODE=true` (only `true`/`false` parse; anything else
    refuses start). Every `/api/console/*` route requires `X-API-Key` **from
    loopback too**, checked before demo mode (off = `403` naming the
    variable). `GET /api/console/options` lists the kinds, the suite
    registry's ids, the roster entries and, per entry, the declared run
    profiles of the service's own machine (`MACHINE_ID`; unset or undeclared
    = no profile, the absence named). `POST /api/console/runs` takes
    identifiers only (`kind`, `suite`, `roster_entry_id`, `machine_id`,
    `compute_mode`), refuses any other field, value, path or shell character
    and any other machine with no process started, holds one in-process lock
    (`409` naming the holder), and launches `python -u -m wave_local_ai_v2`
    or `... .quality_cli --suite <id>` without a shell, with
    `ROSTER_ENTRY_ID`/`MACHINE_ID`/`COMPUTE_MODE` set from the validated ids
    and `SERVICE_API_KEY` blanked. `GET /api/console/runs/{launch_id}/stream`
    is NDJSON (`{"line"}` per merged output line, then one `{"final"}`: the
    existing view route's payload for the announced `run_id`, or the exit
    status and the CLI's last `error:` line). Both CLIs print their `run_id`
    as their first stdout line and unwind through `running_server`'s teardown
    on `SIGBREAK`/`SIGTERM`; service shutdown stops a running child
    gracefully (killed after 25 s) before uvicorn drains open connections, so
    an open stream cannot hold the service up, and a forced exit still stops
    it.
  - The playground (`playground.py`), behind the same two gates (key from
    loopback too, then demo mode). `GET /api/playground/options` lists the
    roster ids, the two thinking policies, the caps
    (`PLAYGROUND_MAX_PROMPT_CHARS`, default 4000; `PLAYGROUND_MAX_TOKENS`,
    default 512), the loaded model and the lock's holder.
    `POST /api/playground/session` (`{"roster_entry_id"}`) launches
    llama-server through `server.build_flags` + `server.start_server` under
    the service machine's declared `gpu` profile (else `cpu_only`), from
    `LLAMA_SERVER_PATH`/`SLM_MODELS_DIR` (optional on the service; unset =
    `503` naming them), after the entry's declared minimums are compared
    with `preflight.observe`/`first_failure` (below one = `503` naming it, no
    refusal record); a second start switches models. `DELETE` stops it.
    `POST /api/playground/chat` (`{"prompt", "thinking_policy"}`) sends the
    prompt as message content only to the loopback `/v1/chat/completions`
    with `local_client.thinking_kwargs`' spelling, and streams NDJSON
    (`{"delta"}`/`{"reasoning"}`, then `{"final"}` with the policy, finish
    reason or error); no timing is forwarded. The playground and a console
    run share the one occupancy lock: each `409` carries
    `holder.session` (`run`/`playground`). Service shutdown stops the
    playground model. Nothing is written or logged.
  - The playground's one cloud subject, opt-in: `PLAYGROUND_CLOUD_SUBJECT`
    (`<provider>:<model>`, `mistral` or `google`, the model the provider
    client is pinned to; unset by default, and a `MISTRAL_API_KEY`/
    `GOOGLE_API_KEY` alone never enables it; set with no key, a wrong model
    or an unknown provider refuses service start). Set, the options carry
    `cloud_subject` (`provider`, `label`, `model`, never the key) and
    `POST /api/playground/session` takes `{"cloud_subject": "<provider>"}`
    in place of a roster id: it stops the playground's local model and takes
    the same occupancy lock (`holder.provider`), so it is refused during a
    run and a run is refused while it is selected. Each send goes through
    `mistral_client`/`google_client` under the provider's
    `*_REQUEST_PACING_S` and a one-item `CLOUD_RETRY_*` budget, with the
    quality CLI's sampler, each retry wait capped at
    `playground.PLAYGROUND_MAX_RETRY_WAIT_S` (10 s; a longer `Retry-After`
    is a refusal naming the provider); the answer arrives as one `delta`, `final`
    reports `thinking_policy: "not_sent"`, and a rate limit, provider
    error, transport error or empty text ends with `final.error` naming the
    provider (never the client's message, which quotes the response body).
    The send button reads `Send to <Provider>: the text leaves this
    machine` on every send, and the thinking selector is disabled. Every
    failure, an unexpected one included, ends with a `final` event. Nothing
    is written or logged.

Both benchmark commands stamp every row they write with a `run_id` and a UTC `captured_at`, so the
rows of one invocation are selectable back out of the append-only store. The two
stores are never merged (see `architecture.md`).

## Roster and host settings

Both commands resolve the model to launch through the tracked roster
(`ROSTER_PATH`, default `aidd_docs/roster/models.json`) and select which
entry to use via `ROSTER_ENTRY_ID`. The roster holds four entries at
`roster_version` 4:

| Entry id | Model | Arch | Quant |
| -------- | ----- | ---- | ----- |
| `qwen3.6-35b-a3b-ud-iq4xs` | Qwen3.6-35B-A3B | MoE, 40 experts | `UD-IQ4_XS` |
| `qwen3-0.6b-q8` | Qwen3-0.6B | dense | `Q8_0` |
| `qwen3-1.7b-q8` | Qwen3-1.7B | dense | `Q8_0` |
| `qwen3-4b-q4km` | Qwen3-4B | dense | `Q4_K_M` |

Each entry declares its `thinking_control`: the request arguments that
disable reasoning under its own chat template (all four:
`{"chat_template_kwargs": {"enable_thinking": false}}`), or `"none"` for a
model that does not reason. A `thinking_policy: disabled` batch sends exactly
that, refuses an entry declaring neither before launch, and, for an object
control, renders one fixed probe through `/apply-template` with and without it
before the first item (`local_client.verify_thinking_control`): two
byte-identical renders refuse the batch, naming entry, control and template
hash, with no row written.

Each entry also carries a `licence` block (`id`, `client_commercial_use`,
`read_on`, `source_url`) and a `language_claim` (`languages`, the subset of
`en`/`fr`/`de` the model card names, plus `source_url`, `read_on` and the
card's verbatim `statement` when it has one), both read off the repository at
the entry's pinned revision. The claim is never written by a suite result. A
declared `family` must be one of `roster.KNOWN_FAMILIES` (vendor lineage:
`qwen`, `mistral`, `google`, `ibm`, `liquid`, `microsoft`); anything else, and
any malformed block field, is refused at load naming the entry and the field.

Each entry also declares its `size_class` (`~0.5B`, `~2B`, `~4B`,
`~8B-and-up`, banded on total parameters at 1B/3B/6B, `roster.SIZE_CLASS_BANDS`)
with the two figures that justify it, `architecture.total_params` and
`bytes_on_disk`, both read off the GGUF; the file's top-level `size_classes`
block declares per class `single_family_ladder`, `moe_sought`, `moe_entry`
and `moe_absent_reason`. All are optional at load and shape-checked when
present; `wave-local-ai-v2-composition-check` is what names an absence.
The engine is resolved the same way, from the tracked engine registry
(`aidd_docs/roster/engines.json`, one entry, `llama.cpp`, the reference
engine, lifecycle `spawned`): the launch's `--host`/`--port`, the occupied-
port guard, the health path, the build probe and the field the thinking
control is carried in (`chat_template_kwargs`) all come from it. Every
runtime row and local quality row names `engine_id` and the probed
`engine_build`; a cloud row states `engine_id: "not_applicable"`. A batch
under `disabled` prints one `thinking switch verified:` line to stderr with
the two renders' hashes. An engine declaring no switch (`none`) cannot carry
an object control: a `disabled` batch whose entry declares one is refused
before any generation, and the candidate gate refuses such a candidate.

`ROSTER_ENTRY_ID` defaults to the MoE flagship. Running several entries in
turn is a shell loop over the ids, not a runner script: `load_dotenv(override=
False)` leaves a shell-set value in place, and `.env` does not set the
variable at all. Each invocation is its own `run_id`.

Right after the run profile resolves, every writer runs the pre-flight
(`preflight.py`): a machine below the roster entry's declared minimum for the
mode (`requirements` in `models.json`: RAM, VRAM under `gpu`, disk while the
weights are absent) refuses with a `RosterError` before the weights are
looked for or anything spawns, writes no row, and appends one refusal record
to `<MACHINE_RESULTS_ROOT>/<machine_id>/refusals.jsonl` (default root
`aidd_docs/results/machines`, tracked: the machine's results location). See
`docs/setup.md` section 1.2.

The host-fitted launch values are not roster data: every (roster entry x
machine x compute mode) triple runs under a named run profile
(`<entry>@<machine>/<mode>`) from `aidd_docs/roster/profiles.json`
(`profiles.py`), resolved roster entry default, then profile, then operator
override. `SERVER_THREADS` and `SERVER_N_CPU_MOE` are the operator overrides:
**unset** (no default) means the profile decides (on the laptop `-t 8`, and
`37` for the flagship under `gpu`, no `--n-cpu-moe` for a dense entry);
**set** replaces the profile's value and every row records it in
`profile_overrides` (schema "26"). A dense entry or a `cpu_only` run given
any `SERVER_N_CPU_MOE` (`0` included) refuses with a `RosterError` before
anything spawns. A triple with no declared profile, or a profile value still
`not_yet_declared` that the operator did not override (the tower's and the
professional PC's thread counts), refuses the same way, naming it. See
`docs/setup.md` section 4.

`MACHINE_ID` (a declared entry of `aidd_docs/roster/machines.json`) and
`COMPUTE_MODE` (`gpu` or `cpu_only`) are required by the runtime CLI, the
quality CLI and the judge probe, with no default: each refuses a missing or
undeclared value, or `gpu` on a machine declared GPU-less, before any server
starts. `cpu_only` launches `-ngl 0 --device none` with no `--n-cpu-moe`, and
refuses a `SERVER_N_CPU_MOE` value naming the mode.

`CAMPAIGN_ID` (optional) puts a runtime or quality run under a campaign
declaration: checked before the build probe or any spawn, it refuses a run
whose engine, variant, roster entry, suite (quality only), machine or mode
is outside the declaration, a declared-excluded cell, and a quality run with
a cloud provider enabled. Every row carries `campaign_id` (schema "24"): the
campaign's id, or `none` for a run under none and on every cloud row. The
judge probe refuses `CAMPAIGN_ID`.

## Distribution

- Installed in editable mode via `uv sync` (dev workflow)
- Entry point declared in `pyproject.toml` under `[project.scripts]`
- Not published to PyPI; local benchmark runs only
