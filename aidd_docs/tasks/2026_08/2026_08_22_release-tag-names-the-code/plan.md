---
objective: "The running code reports its own version and commit sha from any surface (installed distribution or container, with or without a git checkout), a tag that disagrees with the packaged version fails CI before publish, and CHANGELOG.md/README.md/CONTRIBUTING.md tell an operator what shipped and how to cut the first release."
status: implemented
---

# Plan: A release tag names the code a row can cite

## Overview

| Field      | Value                                                                                                   |
| ---------- | --------------------------------------------------------------------------------------------------------- |
| **Goal**   | Expose `version()`/`commit_sha()` at runtime, gate the tag-vs-version agreement in CI, and document the release |
| **Source** | `aidd_docs/backlog/stories/a-release-tag-names-the-code-a-row-can-cite.md`                              |

## Phases

| #   | Phase                              | File                          |
| --- | ----------------------------------- | ------------------------------ |
| 1   | `build_info` surface and its tests  | [`phase-1.md`](./phase-1.md)  |
| 2   | CI tag gate and image sha injection | [`phase-2.md`](./phase-2.md)  |
| 3   | Changelog and release documentation | [`phase-3.md`](./phase-3.md)  |

## Resources

| Source                                                                                                                  | Verified                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)                                                          | The section shape this plan's `CHANGELOG.md` follows: `## [Unreleased]`, then `## [X.Y.Z] - YYYY-MM-DD` with prose entries, newest first.  |
| [Python docs: `importlib.metadata.version`](https://docs.python.org/3/library/importlib.metadata.html#importlib.metadata.version) | Raises `PackageNotFoundError` if the distribution named isn't installed; not caught here because every context this code runs in (dev venv, CI, image) has the project installed. |

## Decisions

| Decision                                                                                             | Why                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| The tag-vs-version check is a new `verify-tag` job, not a step folded into `build`.                  | `build` also runs on pull requests, where there is no tag to check; a separate job scoped by `if: startsWith(github.ref, 'refs/tags/v')` avoids threading a tag-only conditional through an existing step, and lets `publish`'s `needs:` name it directly. |
| The CI checks (`verify-tag`, the extended image label check) call `build_info.version()`/`commit_sha()` through `python -c`, not a second parsing of `pyproject.toml` or the build args. | Matches the acceptance criterion that the packaged version has "no second hardcoded copy that can drift" — the workflow asserts against the same surface a client would read, not a reimplementation of it. |
| Performing the GHCR visibility switch and recording the verified anonymous pull is left for after the first tag is cut, not done in this plan. | The switch needs a package that `publish` has already pushed, and the story's scope note is explicit that the tag itself is cut after merge. `CONTRIBUTING.md` gets the checklist step; the human runs it post-tag. |
