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
