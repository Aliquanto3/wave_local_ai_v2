---
objective: "On a v* tag, once test, build and verify-tag succeed, CI assembles one zip archive holding the five tables, their column dictionary and manifest, the reference bundle they were derived from, LICENSE, LICENSE-DATA, a commit-stamped CITATION.cff and a README naming the release and commit; a verification refuses a hand-edited table, a clone-only path or a version or commit disagreement, and only then does a job holding contents: write alone create the GitHub Release and attach it."
status: implemented
---

# Plan: Each release attaches one archive that needs no clone

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | One assembly script that builds and verifies the release archive from the bundle at the checked-out commit, one `release` job in `ci.yml` that runs it on a `v*` tag and creates the Release, and one README section saying where the archive is |
| **Source** | `aidd_docs/backlog/stories/each-release-attaches-one-archive-that-needs-no-clone.md` |

## Phases

| #   | Phase                                                         | File                         |
| --- | ------------------------------------------------------------- | ---------------------------- |
| 1   | The assembly script: build, stamp, describe and verify        | [`phase-1.md`](./phase-1.md) |
| 2   | The `release` job, its workflow tests and the README pointer  | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The archive is a `.zip` (`wave-local-ai-v2-<version>.zip`, one top folder of the same name), written with the standard library and fixed entry timestamps. | Windows Explorer, macOS Finder and the common Linux desktops open a zip with nothing installed; Explorer opens a `.tar.gz` only on recent Windows 11 builds. Fixed timestamps make two builds of one commit byte-identical. |
| The bundle parts sit in the archive at their repository paths (`aidd_docs/results/...`, `aidd_docs/roster/models.json`), with each shipped directory's `NOTICE.md`; the tables sit at the archive root. | `bundle_manifest.csv` records the paths it read (`aidd_docs/results/runtime-reference.jsonl`, ...) and `LICENSE-DATA` names its covered parts by the same paths, so both resolve inside the archive with no rewrite of either file. |
| The bundle shipped is every part the export reads: both reference row files, `fiches/`, `aidd_docs/roster/models.json`, `suite-definitions/`, plus `comparisons/` and `leader-sets/`. The superseded `*.schema-1.jsonl` rows are not shipped. | The acceptance asks for the bundle the tables were derived from; the two record directories are read by the export (`comparison_records.csv`), so regeneration from the archive alone needs them. The schema-1 files feed no table. |
| Derivation is proven twice inside `verify`: every shipped bundle file equals the repository's bytes at the checked-out commit, and the export regenerated from the repository equals every shipped CSV byte for byte. | A hand-edited table fails the second; a hand-edited bundle copy (which would let an edited table pass if regenerated from the copy) fails the first. |
| "Points at a path that exists only in a clone" is checked as: every token that names a repository top-level directory or tracked top-level file (`aidd_docs/`, `src/`, `tests/`, `scripts/`, ..., `CHANGELOG.md`, `pyproject.toml`, ...) must resolve to an entry of the archive. One reviewed exception list, scoped to `LICENSE-DATA` alone, names the scope paths that licence covers in the repository but the archive does not ship (suite sources under `src/`, the judge probe, the untracked live stores, the model-output spike); the archive README lists each with its permalink at the tagged commit. | `LICENSE-DATA` is shipped verbatim (its legal text is not the archive's to rewrite) and its scope list names the repository. Scoping the exception to that file and those exact paths keeps the check failing on any new pointer anywhere else, including a manifest path or a citation comment. |
| The archive's `CITATION.cff` is the repository copy with its header comment (which points at `tests/test_citation.py` and the repository README) replaced by an archive header, and `commit: <sha>` inserted after `version:`. | CFF 1.2.0's `commit` key is the stamp the repository copy promises; the replaced comment would otherwise fail the self-describing check. |
| The archive README's citation is the repository README's checked attribution string (between its markers) followed by the commit. | One derivation (`tests/test_citation.py` holds the README string equal to `CITATION.cff`); the archive does not re-derive it. |
| Version and commit agreement is enforced in `build` and again in `verify`: the tag minus `v`, `build_info.version()`, `CITATION.cff`'s `version`, the archive README's release line and the stamped citation must agree, and the given commit must equal `git rev-parse HEAD` of the checkout and the README's commit line. | The acceptance's last-but-one line; the `release` job runs these before `gh release create`, so a disagreement fails the job with no Release. |
| The `release` job needs `test`, `build` and `verify-tag`, runs only on `refs/tags/v`, holds `contents: write` alone, and creates the Release with the preinstalled `gh` CLI (`gh release create "$GITHUB_REF_NAME" <zip> --verify-tag`). `publish` and the workflow-level `contents: read` are unchanged. | No third-party action to pin; `--verify-tag` refuses to create a tag that does not exist. Running beside `publish` rather than after it keeps the image push and the Release independent. |
| The script lives in `scripts/` and imports the package (`bundle_export`, `build_info`). | The story names `scripts/`; reusing `build_export`/`write_csv` keeps one derivation. Not covered by the `src/` coverage floor, so its tests exercise every refusal. |
| Local evidence: one archive built into a temp dir with the current commit and `v0.2.0`, its listing and verify output saved in `evidence/`; the zip itself is not kept. | The orchestrator forbids committing the archive and any network write; the real Release needs the owner's tag. |
| `machine_id`, `profile_id` and `campaign_id` column-dictionary meanings drop their repository paths (`aidd_docs/roster/machines.json`, `aidd_docs/roster/profiles.json`, `aidd_docs/campaigns/<id>.json`). | The self-describing check found them in `column_dictionary.csv`; `machines.json` and `profiles.json` themselves cite `context_input/` notes and task evidence, so shipping them would move the problem, and `aidd_docs/campaigns/` does not exist yet. |
| The roster's free-text `read_from` notes (in `models.json` and its `roster.csv` projection) name `aidd_docs/results/README.md` and two task `evidence/runtime.jsonl` files; they are reviewed exceptions linked at the commit, not rewritten. | The roster is a bundle part whose provenance notes belong to the preflight stories; rewriting them here would change published data. Reported for the owner. |

## Evidence

| What | Where |
| ---- | ----- |
| Local build at `HEAD` (`28bb23d`, working tree with this change uncommitted) for `v0.2.0`: listing (39 files), two builds byte-identical, a hand-edited table refused, a wrong tag refused | [`evidence/local-build.txt`](./evidence/local-build.txt) |
| The archive README that build wrote | [`evidence/archive-README.md`](./evidence/archive-README.md) |
| Pending (owner): the first `v*` tag pushed, the Release URL, and opening the four tables on a machine with no clone and no Python | story "Evidence it publishes" |
