# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A dense Qwen3 size ladder in the roster beside the MoE flagship, at
  `roster_version` `2`: `qwen3-0.6b-q8`, `qwen3-1.7b-q8` and
  `qwen3-4b-q4km`, each a vendor-official GGUF pinned by **commit sha**
  rather than by `main`, each carrying the sha256 read off the file that is
  actually loaded. The quants are what each vendor repo publishes — `Q8_0` at
  0.6B and 1.7B (those repos contain exactly one quant each), `Q4_K_M` at 4B
  — so the ladder varies size and is deliberately not quant-uniform; that is
  named in `docs/setup.md` and in the results README rather than left for a
  reader to assume away. All three are Apache-2.0, from one Qwen3 generation,
  on an architecture (`qwen3`) checked against build `b10537`'s own
  `LLM_ARCH_NAMES` rather than inferred from the family name. Total download
  4.63 GiB against the flagship's 17.7, so a machine that cannot host the
  flagship can still run every suite in this project.
- A dense `architecture` block (`kind: "dense"`, `expert_count: 0`) and a
  `validated_host.n_cpu_moe` of `null` on each new entry, which is what makes
  "this entry carries no MoE offload" a checkable fact rather than a
  convention: `roster.validate_host_fit` refuses a dense entry handed any
  offload value, and the committed fiche for each run records the command
  that actually launched, `--n-cpu-moe` absent from all three.
- The launch seam that lets a dense entry run at all. `host_n_cpu_moe` gains
  an unset state (`None`) meaning "read the selected entry", and
  `server.build_flags` resolves it from `validated_host.n_cpu_moe` **before**
  calling `validate_host_fit`, emitting `--n-cpu-moe` only when the resolved
  value is not `None`. It is a resolution change rather than a
  `kind == "dense"` branch in the flag builder on purpose: the refusal stays
  a refusal, so an operator who writes `SERVER_N_CPU_MOE=0` against a dense
  entry still gets a `RosterError` naming it with no process spawned. `0` is
  an instruction to offload no experts; `None` is the absence of an
  instruction, and a dense model can honour the second but not the first.
- A per-entry run loop in `docs/setup.md` as the whole multi-model recipe —
  no runner script, no fleet orchestrator. `ROSTER_ENTRY_ID` already selects
  the entry and `load_dotenv(override=False)` leaves a shell-set value in
  place, so a `foreach` over three entry ids is the entire seam; a script
  would have to own sequencing and failure semantics the CLIs already own.
- A published side-by-side per use case in `aidd_docs/results/README.md`:
  four models on classification, four on translation, four on runtime, each
  with its `run_id`, quant, `-ngl` and whether it carried an MoE-offload
  flag, plus the two caveats the comparison genuinely carries (the ladder is
  Qwen3 and the flagship Qwen3.6, so the architecture axis spans a
  generation; and the quants are not uniform). The finding it records is that
  the dense rows measure **instruction-following on a raw `/completion`
  endpoint** rather than classification or translation ability: with no chat
  template applied, these Qwen3 releases continue the prompt instead of
  answering it, all three run the 32-token classification cap dry on every
  item, and one 4B translation is shown verbatim producing correct German
  after first continuing the French source. A weak result reported with its
  cause, not omitted. Five divergences from the story that asked for this,
  recorded on the story file and in the plan: scored on classification and
  translation only, because the rewriting suite does not exist yet and
  nothing fabricates a row for it; three dense models rather than the "at
  least one" the story names, since one point cannot separate "dense wins"
  from "this particular small model wins"; published to the live stores and
  the results README rather than into the committed reference bundle, which
  is frozen one schema behind and whose regeneration is separately filed
  work; the launch seam above, which the story assumed already existed and
  did not; and the cloud comparator cited from the `google` rows already on
  disk rather than re-run, since they are the same suites, versions and items
  already paid for.
- Translation as a second deterministically-scored use case, selectable with
  `wave-local-ai-v2-quality --suite translation`. `chrf.py` is the character
  n-gram F-score (Popović 2015) reproducing sacreBLEU's default
  parameterisation — `char_order 6`, `beta 2`, whitespace collapsed — in
  sixty lines of `Counter` arithmetic with no I/O and no randomness. It is
  in-repo rather than a `sacrebleu` dependency deliberately: the package
  pulls `numpy`, `regex`, `portalocker`, `tabulate`, `colorama` and `lxml`
  into a project whose CI audits every transitive dependency and whose
  reproduction story asks a client engineer to install the tree, and six
  packages for sixty lines fails that trade. sacreBLEU's source stays the
  specification, cited by URL in the module docstring, so the implementation
  is checkable against it rather than being a private variant; scores are
  published on `0..1` rather than sacreBLEU's `0..100`, because the store
  already reports `suite_accuracy` on `0..1` and two scales in one file is a
  reading trap. `translation_suite.py` holds 21 hand-written short business
  sentences in three directions arranged as a cycle — `en→fr`, `fr→de`,
  `de→en`, seven each — so every language appears once as a source and once
  as a target and each *source* language is 33% of the suite; every source
  text is authored natively in its own language, no item is a translation of
  another item's source, and the suite passes `suite_gate.gate_suite` with no
  indicative reason at 21 items. All three per-language cells are marked
  indicative (seven items against the 10-item cell threshold), which is the
  honest report of a real limitation rather than a set inflated to hide it.
  `scoring.py` gains the graded scorer beside the exact-match one —
  `score_translation_item`, `score_graded_suite`,
  `score_graded_suite_by_language` — sharing the same four-key failure
  taxonomy and the same ordering (empty, then truncation, then the score), a
  failed generation scoring `0.0` under its named reason and staying in the
  denominator. There is no `unparseable` branch and the count stays 0: that
  reason names a completion no member of a closed label set could be found
  in, and a translation has no closed set. Nothing is extracted from a
  completion before scoring — no preamble stripped, no paragraph selected —
  because any such rule would be a scoring choice sacreBLEU would not
  reproduce, so a model that answers "Sure! Here it is:" is genuinely worse
  at the instruction and its score says so. The per-language cell key is
  `score`, not `accuracy`: a chrF mean and an exact-match rate are different
  statistics and one key holding either would be unnameable.
  `SCHEMA_VERSION` `"9"` → `"10"`: a deterministic graded row carries the
  graded block (`row_contract.GRADED_FIELDS` — `metric_id`,
  `metric_version`, `metric_params`, `item_score`, `suite_score`,
  `score_breakdown`, `reference_output`), required only on a row carrying any
  of it, so every existing classification row and every judged probe row
  validates unchanged and no reference bundle is regenerated. `subject_output`
  is deliberately outside that trigger set — `judge_probe.py` already writes
  it as a non-required extra key, and including it would make every probe row
  declare itself graded — and is required inside the structural check
  instead, which also refuses a score outside `0..1`, a named failure
  carrying a non-zero score, and a row publishing a graded score alongside a
  non-null `correct` or `suite_accuracy`. A row carrying both texts and its
  metric parameters is Methodology 16 applied to a score: an auditor
  recomputes the number with sacreBLEU and catches us.
  `verdict.quality_verdict` now decides on `item_score` when neither side of
  a batch carries a `predicted_label`, and returns `not_comparable` with a
  reason when neither value is available — Methodology 8 says "identical
  per-item predicted labels **or scores**" and only the first half was
  implemented, so two translation runs would have come back `reproduced` off
  two sets of nulls, the exact failure `judge_probe.py` documents and routes
  around by hand. The block names the deciding field (`compared_field`). Two
  different translations can coincidentally score the same and be called
  reproduced; that is accepted, because the published rule is about scores
  and pinning reproduction to output text would be stricter than the rule the
  PRD states. `results.resume_skip_reason` filters on `task_suite` as well as
  provider: the pair a resume reasons about is now the triple
  `(run_id, provider, task_suite)`, because one store holds two suites and a
  classification `run_id` was silently evidence about a translation batch
  that never ran. `--suite` resolves one frozen `SuiteSpec` — items,
  identity, caps and a batch scorer — threaded through the local loop, both
  cloud batches and the row builder; `_SUITES` is a literal two-entry
  dispatch table and deliberately **not** a registry, which belongs to the
  use-case epic, the same discipline `_CLOUD_PROVIDERS` follows for
  providers. The flag defaults to `classification`, so every invocation
  written before it existed behaves identically and its rows are unchanged
  apart from `schema_version`. `suite_snapshot.py` now exports both suites
  under one parameterised rule and the classification JSON is byte-identical
  to the tracked copy. Four divergences from the story that asked for this,
  recorded on the story file and in the plan: every provider in
  `QUALITY_PROVIDERS` is a subject rather than the single "cloud model" the
  story names; the result appears alongside classification only, because the
  rewriting suite is a later story and nothing fabricates a row for it; the
  graded score is a conditional row block rather than an overload of
  `correct`/`suite_accuracy`, which would publish a character-n-gram F-score
  under the name "accuracy"; and the suite carries the identity, prompt-set
  hash and generation caps Methodology 2-5 requires and the story, written
  before that methodology, does not mention. Caveat stated on the suite, in
  `chrf.py`, in `docs/setup.md` and in the results README: chrF against a
  *single* reference penalises a valid alternative translation, the German
  references were not reviewed by a native speaker in-project, and a score is
  defensible as a comparison between models measured against identical
  references — never as an absolute translation-quality figure.
- The judge machinery, as four modules. `judge_protocol.py` holds one prompt
  shell per language (`en`/`fr`/`de`), each written in that language, each
  carrying its own id and a `prompt_provenance.template_hash` content hash
  taken over the shell alone, plus the `OPEN_ENDED_QUALITY_1_TO_5` rubric,
  versioned independently of the shells — a rubric revision moves
  `rubric_version` and leaves `template_hash` byte-identical, and an item
  whose language no variant covers is refused (`UnsupportedJudgeLanguageError`)
  rather than judged in English by default. `judge.py` holds the
  provider-agnostic `JudgeBackend` protocol, the parse into the rubric's scale
  — an empty, unparseable or out-of-scale reply fails with a named reason and
  leaves the score `None`, never `0`, with the raw text kept as the row's
  evidence — and judge selection by model family, where a judge of the
  subject's own family raises `JudgeFamilyCollisionError` before any call is
  made, never a silent skip and never a substitution; a single-judge block
  must be given the reason only one judge scored the item, since the collision
  is a refusal rather than a filter and the judge call itself cannot know. `judge_backends.py` is
  the only judge-path module importing `mistral_client`/`google_client`,
  binding each to the protocol through `retry.py`'s pacer and run-scoped
  budget. `agreement.py` computes quadratic-weighted Cohen's kappa for an
  ordinal rubric and the unweighted form for a categorical one, publishes
  exact-match and within-one rates beside the value, returns kappa as an
  explicit null with its own reason when either judge's scores are constant
  (`zero_variance`, deliberately stricter than the mathematically undefined
  `zero_expected_disagreement`, which is kept as its own separate reason) and
  when fewer than two items were scored (`insufficient_items`, which is what a
  single row's own block carries, kappa being a suite-level figure), and owns
  the contested rule and the judged headline. `roster.py` gains the
  family constants, an in-code `MODEL_FAMILIES` declaration keyed by literal
  dated model ids, an optional `family` field on a roster entry, and
  `family_of`, which prefers the entry's own value and refuses an unknown
  model rather than defaulting one; the shipped roster file is unchanged and
  `roster_version` does not move. `SCHEMA_VERSION` `"8"` → `"9"`: a judged
  quality row carries the whole judge block (`row_contract.JUDGED_FIELDS`),
  required only on a row that carries any of it, so an existing deterministic
  quality row validates unchanged; a judged row carrying neither an agreement
  figure nor the single-judge flag is refused naming what is absent, as is one
  claiming both. Judge-call tokens are costed per judge provider at that
  provider's own table rate into `judge_cost`
  (`cost.judge_cost_fields`), and the row's `cost_total` remains the subject
  generation's — whether judge tokens are summed into it stays open with
  criterion 16. New configuration: `CONTESTED_ORDINAL_MAX_DELTA`, default `1`,
  an item being contested when its two ordinal scores sit strictly further
  apart than that, or when its categories differ at all. Deliberately not in
  this increment: no CLI wiring, no judged suite, and no live judge call —
  every test here runs against stubbed HTTP, and the live two-path proof and
  the judged probe belong to the next story. One divergence to record: the 1-5
  ordinal rubric publishes quadratic-weighted Cohen's kappa with the raw
  agreement figures beside it, where the PRD's criterion 10 and the epic's own
  decision row say absolute score delta.
- A shared, provider-agnostic pacing/retry layer (`retry.py`: `Pacer`,
  `RetryBudget`, `call_with_retry`) backs both cloud clients, which now raise
  a typed `RetryableRequestError` (429/5xx for Mistral, 429/503 for Google,
  carrying a parsed retry hint where the provider sends one) distinct from
  their existing non-retryable errors. The quality CLI wires one `Pacer` +
  one run-scoped `RetryBudget` per provider batch (`MISTRAL_REQUEST_PACING_S`
  default `1.1`, `GOOGLE_REQUEST_PACING_S` default `4.1`,
  `CLOUD_RETRY_MAX_ATTEMPTS` default `4`), replacing the unpaced Mistral loop
  and the prior `GOOGLE_REQUEST_PACING_S` stopgap; a budget exhaustion still
  skips that provider with one stderr line rather than aborting the run. A
  new `--resume <run_id>` flag re-runs a prior invocation's id, skipping a
  `(run_id, provider)` batch already fully written (`results.rows_for_run`)
  and re-running an unwritten one from item 1 — never re-paying a cloud
  provider for a batch it already finished, and refusing a partially written
  one rather than duplicating the items it already holds. `retries` and
  `resumed` become required on quality rows (`SCHEMA_VERSION` `"7"` → `"8"`);
  the published reference bundle stays at `"7"` until it is regenerated by
  real runs rather than back-filled (`aidd_docs/results/README.md`).
- Google AI Studio (`gemini-3.5-flash-lite`, pinned) added as a second cloud
  subject to the quality CLI, alongside Mistral, under the same pinning and
  reproducibility discipline (`google_client.py`; `GOOGLE_API_KEY`).
  `cost.GOOGLE_PRICE_TABLE` and `PRICE_TABLES` generalise the per-provider
  cost lookup; `scoring.score_item` gains an optional `truncation_reason`
  override, since Google can report fewer generated tokens than the cap it
  enforced. The quality CLI's cloud provider set is itself configuration
  (`QUALITY_PROVIDERS`, default `local,mistral,google`): a provider left out,
  missing its key, or failing its own pre-flight/batch call is skipped —
  one stderr line, zero rows — rather than aborting the whole run, a change
  from Mistral's prior hard-required behavior, made after a live run found
  this project's Mistral workspace rate-limited on its Free tier.

- The classification suite reaches 20 items across `en`/`fr`/`de` (10/5/5,
  each language >=25% share): 5 natively-authored French and 5 German
  hand-written items added alongside the existing 10 English ones,
  `SUITE_VERSION` `"1"` → `"2"`. A new `scoring.score_suite_by_language`
  computes per-language accuracy/n/indicative, reusing `suite_gate.LANGUAGES`
  and `MIN_PER_LANGUAGE_CELL_ITEMS`; every quality row now carries the result
  as `language_breakdown`, required by the writer gate. `SCHEMA_VERSION`
  `"6"` → `"7"`.
- A suite definition snapshot (`suite_snapshot.py`, `uv run python -m
  wave_local_ai_v2.suite_snapshot`) exports the classification suite's
  identity, caps and every item to `aidd_docs/results/suite-definitions/
  <suite_id>.json` — a snapshot a bundle reader resolves a published row's
  `suite_id`/`suite_version` against, not a live registry.
- The published reference bundle (`runtime-reference.jsonl`,
  `quality-reference.jsonl`, `fiches/`, the roster, `suite-definitions/`) is
  regenerated under the current schema against the 20-item suite: two
  runtime runs and two quality runs (local + mistral), the second of each
  kind carrying a verdict against the first, validated clean (`checked 82
  row(s)`, exit 0) with a deliberate-edit proof case. The prior 10-item,
  EN-only bundle is kept, not deleted, renamed to `*-reference.schema-1.jsonl`
  for published-evidence continuity — the suffix counts superseded bundle
  generations, not a `schema_version`: those rows carry `schema_version` `"2"`
  or no such key at all.
- A tracked, versioned roster file (`aidd_docs/roster/models.json`) now pins
  each model's identity (repo, revision, file, display name, checksum,
  architecture) and its full flag set. `server.build_flags`, the resolved
  model file, the published `model_id` and
  `quant` all resolve through the roster and the two host-fitted settings
  (`SERVER_N_CPU_MOE`, `SERVER_THREADS`) rather than from source constants.
  `llama_cpp_build` is now a live probe of the running binary
  (`build_probe.probe_build`), not a hardcoded string.
- Every published row now carries a `schema_version` and is refused by the
  writer (`append_row`) unless it is contract-complete for its kind.
- The classification suite declares its generation caps (max output tokens,
  stop sequences, context length), a stable suite id/version, a prompt-set
  hash, and per-item language/provenance/contamination-risk tags.
- A suite gate marks an under-sized or language-imbalanced suite indicative
  rather than passing or failing it outright — today's 10-item, EN-only suite
  included, and refuses one whose items carry no language or provenance tag.
- Every runtime and quality row now carries `release_version`, `commit_sha`
  and `tree_dirty`, captured once per run and degrading to explicit nulls
  when git is unavailable, so a row names the exact code and tree state that
  produced it.
- Every row now carries the endpoint, prompt-template id, prompt-template
  content hash, and capture-or-reconstruction label that produced its
  prompt. The writer gate refuses a row whose endpoint applies a template
  but whose `prompt_template_id` is `none`.
- A failed quality generation (empty, truncated at the suite's cap, truncated
  at the model's own context limit, or unparseable) now scores 0, stays in
  the suite's denominator, and names its `failure_reason`; every quality row
  also carries the suite's aggregated `failure_counts`.
- `mistral_client.complete_prompt` now returns a structured result
  (`content`, `endpoint`, `finish_reason`, `generated_tokens`) instead of a
  bare string.
- The runtime harness now runs a declared repetition protocol: one warm-up
  (excluded from N, per-request `cache_prompt: false` forces a full
  prefill) plus N≥2 counted repetitions with a cooldown between them, a
  seed pinned per request while the validated baseline flag set stays
  untouched, and median/mean/sample-sd/peak aggregates over the counted
  set. A row now carries the ordered raw repetitions alongside the
  aggregate, plus `sampling`, `seed_pinned`, `warmup_count`,
  `warmup_repetitions`, `cooldown_s`, `repetitions_n`,
  `slot_reset_method`, and an `aggregation` map declaring the statistic
  behind every published measurement.
- A repetition that returns blank content, an unparseable timings block, or
  a `exceed_context_size_error` refusal now fails the whole row by index
  and reason — no retry, no substituted value, nothing written.
- Every counted and warm-up repetition now records its machine state: GPU
  temperature and decoded NVML clock event reasons (`gpu_idle`,
  `sw_thermal_slowdown`, `hw_power_brake_slowdown`, etc.), plus CPU package
  temperature or its declared `"unavailable"` on platforms with no
  admin-free reader (confirmed live: this Windows build has none).
- A runtime row now carries the `gen_tok_per_s`/`ttft_ms`/`prompt_tok_per_s`
  spread (sample sd over median) for its counted repetition set, and flags
  itself `unreliable` when `gen_tok_per_s`'s spread exceeds
  `RUNTIME_SPREAD_THRESHOLD` (default `0.10`) — the other two metrics'
  spread is published but never sets the flag. Every row also declares its
  `thermal_posture` (today: `"fixed_cooldown"`, the fixed inter-repetition
  cooldown this harness already runs).
- Every runtime row now states `ttft_source` (`"server_reported"` today),
  naming that its `ttft_ms` comes from llama-server's own reported timing,
  not an independent client-side measurement — refused by the row contract
  if it names anything else.
- The hardware fiche is now a stored, content-addressed artifact
  (`aidd_docs/results/fiches/<hash>.json`, write-once) instead of ten fields
  flattened onto every row: a runtime or quality row now cites its fiche by
  `fiche_hash` alone. The fiche's identity hash covers `cpu`, `ram_gb`,
  `gpu_name`, `gpu_driver_version`, `os`, `cuda_ceiling`, `llama_cpp_build`,
  `quant`, `roster_entry_id` and the roster entry's `sha256` — never the raw
  flag list (kept on the stored fiche as evidence only) or a filesystem path.
- `wave-local-ai-v2-validate`, a new CLI, proves a stored fiche was edited or
  is missing: it re-hashes every cited fiche's own current content, names the
  changed field(s) via `git show HEAD:...` when the registry is
  git-tracked, and exits non-zero naming the affected row(s) by run id and
  position — distinguishing `edited` from `missing` from a third, non-fatal
  `legacy` class (a row predating the `fiche_hash` contract entirely,
  `row_contract.FICHE_HASH_SCHEMA_VERSION`).
- Every runtime and quality row now carries a `verdict` block
  (`reproduced` / `not_reproduced` / `not_comparable`), computed and stored
  by the harness against a configured reference file
  (`RUNTIME_REFERENCE_PATH`, `QUALITY_REFERENCE_PATH`). A runtime match
  compares exactly the four verdict-blocking fields resolved from the
  candidate and reference rows' own fiches (`llama_cpp_build`, `quant`,
  `gpu_name`, `flags`) — never CPU, RAM, driver, or OS — then compares
  `gen_tok_per_s` within `RUNTIME_REPRODUCTION_TOLERANCE` (default `0.10`); a
  quality match compares per-item `predicted_label` across a shared
  `model_id`/`suite_version`/seed and the same set of `item_id`s — an item
  present on one side only makes the batch `not_comparable`, so a partial
  overlap can never read as agreement.
- Every runtime and quality row now carries three independently-labelled
  energy channels (`cpu_energy_kwh`/`cpu_energy_method`,
  `gpu_energy_kwh`/`gpu_energy_method`, `ram_energy_kwh`/`ram_energy_method`)
  in place of the single composite `energy_method`, plus an emissions block
  (`emissions_kg`, `emission_factor_kg_per_kwh`, `emission_region`,
  `emissions_scope`, `emissions_scope_formula_id`, `scope_comparability`). A
  channel's method label now derives from what CodeCarbon can structurally
  report (GPU: `measured_nvml` only when NVML found a GPU, else `unavailable`
  — never a value check), not from its magnitude, so a GPU that genuinely
  drew ~0W stays distinguishable from no GPU present. `measure_energy` moves
  to `codecarbon.OfflineEmissionsTracker`, removing a live IP-geolocation
  call. Local rows are Scope 2 (measured on this machine); mistral quality
  rows are Scope 3 (a Wh-per-token formula estimate, `emissions_scope_formula_id`
  set, `scope_comparability` naming the two are not like-for-like).
  `SCHEMA_VERSION` moves `"3"` → `"4"`.
- Every runtime and quality row now carries a cost block: `cost_total`,
  `cost_currency`, `cost_per_million_tokens` (normalized to
  `cost_per_million_total_tokens`, `null` when its denominator is unknown or
  zero — never fabricated), plus every field it was derived from
  (`kwh_price_eur`/`kwh_price_currency`/`kwh_price_recorded_at` for a local
  run, `list_price_input_per_million`/`list_price_output_per_million`/
  `list_price_per_million_tokens`/`list_price_currency`/
  `list_price_retrieved_at` for a cloud run — the inapplicable half is
  `null`, never both). A cloud row carries the two rates the price table
  actually charges, not only the blended effective rate its own token mix
  worked out to: the blend is derived *from* `cost_total`, so a row carrying
  only it could not recompute its own cost. Currencies (EUR for local, USD
  for Mistral's list price) are never converted between each other. The
  writer gate now refuses a row whose `cost_total` is non-null but both
  derivation bases (`kwh_price_eur`, `list_price_input_per_million`) are
  null. `mistral_client.complete_prompt` now also surfaces `prompt_tokens`
  and `total_tokens` from the response's `usage` block; a cloud batch whose
  responses omit `prompt_tokens` publishes a `null` token total, cost and
  Scope-3 estimate rather than pricing the prompts at zero. A runtime row's
  `tokens_in_total` sums `tokens_evaluated` across the counted repetitions,
  so it spans the same window as `tokens_out_total`, `energy_kwh` and
  `cost_total`. `SCHEMA_VERSION` moves `"4"` → `"6"`.

### Changed

- `SERVER_N_CPU_MOE` unset no longer means `37`. It means "the selected
  entry's `validated_host` decides": `37` for the MoE flagship, and no
  `--n-cpu-moe` at all for a dense entry. Set, it overrides the entry exactly
  as before, including the two refusals (above an MoE entry's `expert_count`,
  or any value at all on a dense entry). The flagship's launch command is
  byte-identical — both byte-identical tests pass with the `37` now arriving
  from the entry rather than from a settings constant, and
  `DEFAULT_HOST_N_CPU_MOE` stays as documentation of that entry's value.
- `roster_version` moves `1` → `2`, because the file's content changed and a
  row recording `roster_version: 1` must not be ambiguous between a one-entry
  and a four-entry roster. Rows already published keep their `1`; nothing is
  back-filled.
- Mistral completions are sent the suite's declared output cap
  (`max_tokens`), the same one the local `/completion` call applies as
  `n_predict`. Both halves of a comparison now run under the cap their rows
  publish; previously only the local half did.
- A runtime row is now a repetition set, not one request: `gen_tok_per_s`,
  `prompt_tok_per_s`, `ttft_ms`, `vram_used_mib`, `gpu_draw_w` and
  `process_rss_bytes` are now aggregates (median or peak) over the counted
  repetitions rather than a single sample. `SCHEMA_VERSION` moves `"1"` →
  `"2"`; quality rows move with it since the constant is shared.

## [0.1.0] - 2026-08-22

### Added

- A runtime benchmark harness that measures local SLM inference cost (latency,
  throughput, VRAM, energy) and appends each run as a row bound to a signed
  hardware fiche, so a runtime number is never read apart from the machine
  that produced it.
- A reproducible quality/classification scoring harness that judges model
  output against a pinned sampler configuration, comparing local models
  against cloud LLM APIs on shared task suites.
- A README and `docs/setup.md` onboarding walk that takes a new machine from
  clone to a first runtime and quality row, including model weight
  acquisition and checksum verification.
- A pre-commit fast gate (lint, format, type-check, secret scan) enforced on
  every commit, with the same command set re-run at push time and in CI.
- A CI check suite covering the fast gate, coverage-gated tests, and a
  dependency vulnerability audit, behind one stable `required` check.
- A branch protection ruleset on `main`, tracked in
  `.github/rulesets/main.json`, requiring a pull request and a green
  `required` check with no bypass actors.
- A container image, built and smoke-tested on every pull request and
  published to GHCR on every version tag, carrying the pinned CPU
  `llama-server` build and OCI labels naming its source and commit.
- A build-provenance surface the running code can read: its own version from
  installed metadata, with no second hardcoded copy to drift, and the commit
  it was built from — injected into the image as `WAVE_BUILD_SHA` beside the
  OCI revision label, resolved from the checkout when running from source,
  and an explicit null rather than a fabricated value when neither exists.
  CI refuses a tag whose name disagrees with the packaged version before the
  image is published.

[Unreleased]: https://github.com/Aliquanto3/wave_local_ai_v2/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Aliquanto3/wave_local_ai_v2/releases/tag/v0.1.0
