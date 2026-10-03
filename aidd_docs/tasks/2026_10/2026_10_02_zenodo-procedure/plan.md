---
objective: "A written, optional procedure under docs/ for depositing a release archive on Zenodo and recording the returned DOI back into CITATION.cff and README.md, with no CI token, no automated deposit and the GitHub-to-Zenodo integration disabled, ready for the owner's one proving walk on the Zenodo sandbox."
status: implemented
---

# Plan: The Zenodo deposit is a written, optional procedure, proven once

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `docs/zenodo-deposit.md`, linked from `README.md`, states what to upload, every metadata value and its `CITATION.cff` source, the licence, the mixed-terms description, how the DOI is recorded back, and why nothing is automated; a small test pins the "nothing automated, no sandbox DOI" properties |
| **Source** | `aidd_docs/backlog/stories/the-zenodo-deposit-is-a-written-optional-procedure-proven-once.md` (owner answer Q40 (a): proven on the Zenodo sandbox) |
| **Mode**   | Written procedure only. The sandbox walk is the owner's (it needs a Zenodo sandbox account); the story stays `ready` until that walk and its corrections land. |

## Phases

| #   | Phase                                                      | File                         |
| --- | ---------------------------------------------------------- | ---------------------------- |
| 1   | The procedure, its README link and its guard test          | [`phase-1.md`](./phase-1.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| Zenodo help pages and developer docs, the Zenodo versioning FAQ, the CFF 1.2.0 schema guide | Read over HTTPS on 2026-10-03, read-only; every claim the procedure takes from them is listed with its URL in [`evidence/sources.md`](./evidence/sources.md). Form labels not found in any of them are marked in the procedure as "confirm on the walk" rather than guessed. |

## Decisions

| Decision | Why |
| -------- | --- |
| The deposit's resource type is Dataset, not Software. | The release archive holds tables, the bundle, licences and the citation, and no code (`scripts/assemble_release_archive.py` ships no `src/`). Zenodo's help says to pick the type that best describes the most significant content. `CITATION.cff`'s `type: software` cites the repository and is left unchanged. |
| The deposit's licence is CC-BY 4.0 alone. | Nothing in the archive is code, so listing MIT would claim MIT files the deposit does not hold. The description states that `LICENSE` ships because the citation names the repository's code, and that the parts `LICENSE-DATA` names as not granted are not CC-BY 4.0. |
| The DOI is recorded in `CITATION.cff` as an `identifiers` entry of `type: doi` with a `description` naming the release, not as the top-level `doi`. | The top-level `doi` is "the DOI of the software or dataset" with no version; once `version` moves on, it would present an older release's deposit as the current version's DOI. An `identifiers` entry carries its own description, and no check in `tests/test_citation.py` or `stamp_citation` reads it. |
| The README DOI line sits outside the `<!-- attribution:start/end -->` markers. | `tests/test_citation.py` holds the marked string equal to what `CITATION.cff` derives, and the derivation reads no DOI; a DOI inside the markers fails that test. |
| No DOI is reserved before upload. | The archive is uploaded unchanged as `release-build` verified it, so a reserved DOI could not be written into it. |
| A test pins: no workflow names Zenodo, and neither `CITATION.cff` nor `README.md` carries a sandbox DOI (prefix `10.5072/`); the README links the procedure. | The orchestrator asked for a cheap automated pin where possible; the story's own "Tests it needs" is "none automated", and these checks add no production code. The GitHub-to-Zenodo toggle itself lives in the owner's Zenodo account and cannot be tested from the repository; the procedure gives the manual check. |
| The procedure's deposit log records "no real deposit, no venue has asked" for the first release. | Acceptance asks that whether the first release took a real DOI be recorded; as of 2026-10-03 none did. |
