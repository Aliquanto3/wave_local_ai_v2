---
objective: "The release-build job installs pyarrow at a pinned version for itself alone and ships one typed Parquet copy beside each of the five CSV tables in the archive; a check reads every copy back and compares it to its CSV cell by cell under the column dictionary's types, empty cells included, failing the build on any disagreement; the archive README says the CSV is right and names the pyarrow version; and the same build runs on demand (workflow_dispatch) without a tag, a Release or an image push."
status: implemented
---

# Plan: Parquet copies ship beside the CSV and never disagree with it

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | One Parquet script (types from the dictionary, write, cell-by-cell check), an opt-in `--parquet` on the archive's `build`/`verify`, and an on-demand trigger on the release path that creates no Release, with the write token split off into a job that runs no project code |
| **Source** | `aidd_docs/backlog/stories/parquet-copies-ship-beside-the-csv-and-never-disagree-with-it.md` |

## Phases

| #   | Phase                                                             | File                         |
| --- | ----------------------------------------------------------------- | ---------------------------- |
| 1   | The pinned `release` group, the Parquet script and the archive's `--parquet` | [`phase-1.md`](./phase-1.md) |
| 2   | The release jobs: on-demand trigger, Parquet step, token split, workflow tests | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| `pyarrow==25.0.1` is declared in a non-default `[dependency-groups] release` group (`uv add --group release pyarrow==25.0.1`), locked in `uv.lock`. Only the `release-build` job installs it (`uv sync --locked --group release`). | `project.dependencies` stays free of it; `uv sync` (test, verify-tag) installs only the default `dev` group; the Dockerfile's `uv sync --locked --no-dev` installs no group at all, so the image cannot pick it up. Locking it keeps the pin and its hashes reviewed like every other dependency. |
| The dependency audit exports `--all-groups`. | Without it the audit reads only the default groups and the one dependency that runs beside the `contents: write` token would go unaudited. Strengthens the gate; no other change to the audit. |
| One Parquet file per data table (`<table>.parquet`, the five tables), none for `column_dictionary.csv` and `bundle_manifest.csv`. | The acceptance says "one Parquet file per CSV table"; the story's "four tables" predates the fifth (`comparison_records`). The dictionary and manifest describe the tables, they are not tables of results. |
| A timestamp cell must carry the `+00:00` offset; a naive one or any other offset is refused (review fix). | The unit is a UTC timestamp and every current value is `+00:00`; storing another offset as UTC would normalize the CSV text silently, the one thing the copy must not do. |
| Arrow types come from the dictionary's `unit` cell through one explicit unit-to-type table (boolean, int64, float64, date32, timestamp[us, UTC], string); a unit missing from that table fails the build. Every empty CSV cell is a Parquet null, in every type. | The dictionary has no type column; its `unit` is the closest typed fact it states. Failing on an unknown unit keeps a new column from shipping silently mistyped; the on-demand run surfaces it between releases. CSV cannot tell an empty string from null, and the dictionary says what an empty cell means, so null is the faithful copy. |
| The check is independent of the writer: it reads the Parquet back, requires the same columns in order, the dictionary's Arrow type per column, the same row count, and each cell equal to the CSV cell parsed under that type (timestamps compared as UTC microseconds, so no time-zone database is needed). | "Cell by cell under the column dictionary's types, empty cells included." Comparing parsed values, not re-rendered text, is what "under the types" means. |
| Parquet is opt-in on the archive script (`build --parquet`, `verify --parquet`); without the flag the archive is the story-15 archive, unchanged. With it, the five `.parquet` entries join the expected files (byte-compared like every derived file) and `verify` runs the check on each pair, printing one line per table. | Keeps `pyarrow` out of the test matrix; `release-build` always passes it. Byte comparison keeps the archive deterministic and derived; the cell check is the semantic proof. |
| The clone-only path scan skips `.parquet` entries. | They are compressed binary; each is proven cell-equal to its CSV, which the scan reads. |
| The archive README gains a "Parquet copies" section (only with `--parquet`): the CSV is normative wherever the two could disagree, and the `pyarrow` version that wrote them. | Acceptance line 2. |
| On-demand trigger: `workflow_dispatch` on the workflow. Story 15's `release` job splits (review fix): `release-build` (`contents: read`) runs on a `v*` tag push after `test`, `build`, `verify-tag`, or on a dispatch after `test`, builds and verifies the archive with the Parquet check, records its sha256 as a job output and uploads it as the `release-archive` artifact; `release-publish` (`contents: write`, `actions: read`) runs on a tag push only, downloads that artifact with `gh run download`, checks the digest and runs `gh release create --verify-tag`. On a dispatch the release name is `v<packaged version>`. `publish` gains a `push` guard so a dispatch on a tag ref pushes no image. | "Without cutting a tag and without creating a Release". The write token never sits beside dependency code (pyarrow, pytest, uv): `release-publish` has no checkout and no action. `upload-artifact` reuses the pin already in the test job; no `download-artifact` is pinned anywhere in the repo, so the preinstalled `gh` downloads instead of a guessed action SHA. `build` and `verify-tag` are tag-gated and skipped on a branch dispatch, hence the explicit result checks in `release-build`'s `if`. |
| `release-build` runs the Parquet tests (`pytest tests/test_release_parquet.py --no-cov`) where `pyarrow` is installed; the test matrix skips them (`importorskip`). | "The check itself, run where pyarrow is available." `--no-cov`: one file cannot meet the repo-wide floor. |
| The GitHub on-demand run is owner-pending; a local rehearsal of the same commands is the evidence kept here. | No `workflow_dispatch` or network write in the night run. |

## Evidence

| What | Where |
| ---- | ----- |
| Local rehearsal of the dispatch path, `release-build`'s commands in order (`HEAD` `aa3b104`, this change uncommitted): `RELEASE_TAG=v0.2.0`, the Parquet tests 28 passed, every table compared and equal (five lines), the digest recorded and checked on a copy as `release-publish` would, two builds byte-identical (sha256 `d824276f...`), `uv export --no-dev` names no pyarrow | [`evidence/on-demand-rehearsal.txt`](./evidence/on-demand-rehearsal.txt) |
| The archive README that build wrote, with its "Parquet copies" section | [`evidence/archive-README.md`](./evidence/archive-README.md) |
| Pending (owner): one `workflow_dispatch` run of CI on GitHub once this is merged, its `release-build` job log (the five "compared ... equal" lines) and the `release-archive` artifact, `release-publish` skipped, filed with the delivery | story "Evidence it publishes" |
