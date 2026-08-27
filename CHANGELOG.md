# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
