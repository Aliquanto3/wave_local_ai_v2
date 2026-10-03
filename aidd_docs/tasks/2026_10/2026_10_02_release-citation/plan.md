---
objective: "CITATION.cff at the repository root names the work, the packaged version, the author, the repository URL and both licences, a test holds its version equal to the packaged version, and the README's attribution string is derived from it and checked against it, with the owner's identity held as marked placeholders that fail the build on a tag."
status: implemented
---

# Plan: One citation names the release and is the attribution a reuser copies

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | One `CITATION.cff`, one attribution string derived from it in the README licence section, and a test module that keeps the version and the string in step and refuses a release with an unresolved author identity |
| **Source** | `aidd_docs/backlog/stories/one-citation-names-the-release-and-is-the-attribution-a-reuser-copies.md` (owner decision D3 of the 2026-10-02 night run: placeholder identity) |

## Phases

| #   | Phase                                                   | File                         |
| --- | ------------------------------------------------------- | ---------------------------- |
| 1   | `CITATION.cff` and its version and placeholder checks   | [`phase-1.md`](./phase-1.md) |
| 2   | The README attribution string derived from the citation | [`phase-2.md`](./phase-2.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| https://github.com/citation-file-format/citation-file-format/blob/1.2.0/schema.json (as bundled by `cffconvert` 2.0.0) | The file validates against the CFF 1.2.0 schema; run once with `uvx cffconvert --validate`, transcript in `evidence/`. |

## Decisions

| Decision | Why |
| -------- | --- |
| The author identity is held as marked placeholders (`PLACEHOLDER-OWNER-GIVEN-NAMES`, `PLACEHOLDER-OWNER-FAMILY-NAMES`, `PLACEHOLDER-OWNER-AFFILIATION`, and a commented `orcid` line carrying `PLACEHOLDER-OWNER-ORCID`). No name, email or ORCID is copied from `pyproject.toml`, `LICENSE` or git config. | Owner decision D3: the story's "Needs" line leaves the identity to the owner, and this run does not make that choice. The ORCID stays a comment because the CFF schema pattern only admits a real-shaped ORCID URL, and a fake but valid-shaped one is exactly the kind of value that could ship unnoticed. |
| A test fails when any `PLACEHOLDER-` marker remains in `CITATION.cff` or the README attribution while the run is on a tag (`GITHUB_REF` under `refs/tags/`); off a tag it skips and names the unresolved fields. | `ci.yml`'s `publish` job needs `test`, and `test` runs on `v*` tags, so the tag build cannot publish with a placeholder, with no workflow change (the story forbids one). Failing on every push would turn the whole branch red until the owner answers. |
| The structural checks (required keys, licence ids, no `commit`, version) run on every push with `pyyaml` (already a dev dependency); full schema validation is evidenced once with `cffconvert` run through `uvx`, not added as a dependency. | The story names no validator package and the brief allows a new dependency only when the story names it. |
| `license:` lists `MIT` and `CC-BY-4.0`, with a comment naming which part each covers. | CFF takes SPDX ids; the split itself lives in `LICENSE` and `LICENSE-DATA`, so the citation names both and points there rather than restating the scope. |
| The attribution format is `{authors} ({year}). {title}, version {version}. {repository-code}. Code: MIT; data: CC-BY 4.0.`, `year` taken from `date-released`. | It carries every element the acceptance names (work, author, version, licence, link) plus the year a citation needs, and one derivation function produces it, so the README cannot hold a second form. |
| `LICENSE-DATA` section 4's "will be stated ... Until it is" sentence is rewritten to point at the README string and `CITATION.cff`, keeping the interim Section 3(a) rule (licensor Aliquanto3, work, licence and link, repository, changes) while the author fields are placeholders; the README says the same in one line. | The pointer would otherwise be false; the interim rule keeps a valid CC-BY attribution available until the owner fills `CITATION.cff` (review round 1). The section sits above the hashed legal-code marker, so the integrity test is unaffected. |
| `date-released` must equal the date of the cited version's `## [x.y.z] - YYYY-MM-DD` heading in `CHANGELOG.md`. | The simplest honest tie between the date and the version: both are committed, so the check runs in CI with no git history or tags, and a version bumped without its dated heading, or with a stale `date-released`, fails. |
