# Review: A release tag names the code a row can cite

- **Verdict**: changes-requested
- **Diff**: `main...working tree`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 0 critical, 2 warning, 3 minor

## Phases

### Phase 1 — `build_info` surface and its tests

- [x] `uv run python -c "...version(); ...commit_sha()"` runs clean in the dev venv and prints `0.1.0` then a real sha — ran it: printed `0.1.0` then `9cbfb44474a5573c5d8d9948a9f1a7becb918455` — `src/wave_local_ai_v2/build_info.py:25,30`
- [x] `uv run pytest tests/test_build_info.py -v` passes all four, no real git process and no real metadata read — ran it: `4 passed in 0.17s`; every case stubs `_installed_version`, `shutil.which` or `subprocess.run` — `tests/test_build_info.py:6,12,24,36`

### Phase 2 — CI tag gate and image sha injection

- [x] `docker build --build-arg REVISION=deadbeef` then `--entrypoint python ... commit_sha()` prints `deadbeef` — `ENV WAVE_BUILD_SHA="${REVISION}"` sits after `ARG REVISION` in the `runtime` stage and the venv is on `PATH` — `Dockerfile:55`, `Dockerfile:45` (mechanism verified statically; the image build itself runs in CI)
- [x] A tag whose name and packaged version disagree fails `verify-tag` and `publish` never starts — `.github/workflows/ci.yml:124-148` (job, `if: startsWith(github.ref, 'refs/tags/v')`, `exit 1` naming both values) and `.github/workflows/ci.yml:152` (`needs: [test, build, verify-tag]`)
- [x] The extended "OCI labels name the source and the commit" step proves `commit_sha()`, the revision label and `github.sha` agree — `.github/workflows/ci.yml:112-121` (mechanism verified statically; runs on the next tag build)

### Phase 3 — Changelog and release documentation

- [x] `CHANGELOG.md` has `## [Unreleased]` and a `## [0.1.0]` whose bullets are prose naming capabilities, zero commit subjects — `CHANGELOG.md:8`, `CHANGELOG.md:10-33`
- [x] README's "Results layout" states the reference evidence predates the first tag in one sentence — `README.md:91-93`
- [x] `CONTRIBUTING.md` has "Cutting a release" covering the version bump, changelog move, `aidd-vcs:03-release-tag`, the `verify-tag` gate and the first-tag GHCR switch with its anonymous-pull check — `CONTRIBUTING.md:56-80`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | fit | 1 | `src/wave_local_ai_v2/build_info.py:41-46` | `git rev-parse HEAD` inherits the process CWD, so outside this checkout the function reports whatever repository the caller happens to stand in. Proven: from a throwaway repo at HEAD `2134dcef…`, `commit_sha()` returned `2134dcef…`, not this project's `9cbfb44…`. That is fabricated provenance, which the module docstring (`build_info.py:12-14`) and the story's "the image label and the sha the code reports name the same commit" both forbid. Not 🔴 only because no row consumes the value yet. | **Applied.** git is now anchored at the package's own location (`build_info.py:26,45`), so a non-editable install degrades to `None` and a dev checkout still resolves this repo; `tests/test_build_info.py:36-53` asserts the argv. Re-verified from the same foreign repo: `commit_sha()` now returns `9cbfb44…`, not `2134dcef…`. |
| 🟡 | fit | 3 | `CHANGELOG.md:10-33` | The `[0.1.0] - 2026-08-22` entry stops at the container image and never mentions the surface this very change adds. `CONTRIBUTING.md:56-59` says the release lands on `main` first and the tag is cut after, so v0.1.0 will contain `build_info`, the `WAVE_BUILD_SHA` injection and the `verify-tag` gate — yet an operator reading the changelog for v0.1.0 learns none of it. The plan asked for exactly seven bullets, but the plan was written before this branch existed. | **Applied.** `CHANGELOG.md:34-40` adds the build-provenance bullet to `## [0.1.0] ### Added`: version from installed metadata, sha injected as `WAVE_BUILD_SHA` beside the OCI revision label, explicit null when neither exists, and the tag-vs-version gate. |
| 🟢 | rot | 2 | `.github/workflows/ci.yml:118-121` | The third comparison is unreachable. `revision_label` is already asserted equal to `$GITHUB_SHA` at `:108-111`, so once `reported_sha == revision_label` holds at `:114`, `reported_sha != $GITHUB_SHA` can never be true. The "three-way agreement" the plan asked for is two independent edges, not three. | Drop the `:118-121` block, or move it above the `:114` check so the two live comparisons are label-vs-`GITHUB_SHA` and `commit_sha()`-vs-`GITHUB_SHA`. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/build_info.py:47-51` | The two deliberate degradation paths are untested: the `except (CalledProcessError, OSError)` branch (a directory that is not a checkout) and the `sha or None` collapse of an empty `stdout`. The plan's Test Scope listed only four cases, so the criteria pass, but the branches that exist purely to guarantee "explicit null, never fabricated" are the ones with no proof. | Add two cases: `subprocess.run` raising `CalledProcessError` → `None`, and returning `stdout="\n"` → `None`. |
| 🟢 | code | 1 | `tests/test_build_info.py:16-17,26-31` | Isolation is inconsistent with the module's own design. The version case patches the module-local `_installed_version` alias precisely to avoid touching the stdlib globally (plan phase-1, task 2.1), but the sha cases patch `build_info.shutil` / `build_info.subprocess`, which *are* the stdlib modules — so a global `subprocess.run` stub is live for anything else running during those tests. | Import the two callables under private aliases (`_which`, `_run`) the way `_installed_version` already is, and patch those. |

## Verification

| Metric        | Value                                                                                                                                  |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Verified      | 100% (8/8)                                                                                                                             |
| Files checked | `src/wave_local_ai_v2/build_info.py`, `tests/test_build_info.py`, `.github/workflows/ci.yml`, `Dockerfile`, `CHANGELOG.md`, `README.md`, `CONTRIBUTING.md` |
| Unchecked     | none                                                                                                                                   |
| Unplanned     | none                                                                                                                                   |
