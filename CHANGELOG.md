# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
