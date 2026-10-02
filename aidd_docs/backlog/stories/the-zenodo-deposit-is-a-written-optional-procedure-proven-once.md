---
type: story
status: ready
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
depends_on:
  - aidd_docs/backlog/stories/one-citation-names-the-release-and-is-the-attribution-a-reuser-copies.md
  - aidd_docs/backlog/stories/each-release-attaches-one-archive-that-needs-no-clone.md
order: 6
---

# Story: The Zenodo deposit is a written, optional procedure, proven once

**As** the owner deciding whether a release gets an archival DOI
**I want** a written procedure for depositing a release archive on Zenodo and recording the returned DOI, proven by performing it once
**So that** a DOI costs ten minutes when a venue asks for one, without a token in CI and without every tag becoming a permanent public archival act

Maps to: PRD Open Question "Whether each release also receives an archival DOI (Zenodo or equivalent). Desirable for citation, deliberately optional for this release, and not an acceptance criterion"; epic Boundaries "a Zenodo deposit written as a manual, optional procedure"; epic decision "A DOI is optional and manual for this release"; epic Dependencies row "Zenodo's own metadata and licence vocabulary"; owner answer to Q40 (option a, 2026-10-01): the proving run is a deposit on the Zenodo sandbox, and the real deposit is left to the day a venue asks for a DOI.

Needs: an operator. The owner, with a Zenodo sandbox account, performs the deposit once on the sandbox against a release archive from order 4. No model run, API key or hardware is required.

## Acceptance

- A procedure under `docs/` states what to upload (the release archive, unchanged), which metadata to enter and where each value comes from in `CITATION.cff`, which licence to select for the deposit, and how the archive's mixed terms (the parts `LICENSE-DATA` names as not granted, and any drawn item's own terms) are stated in the deposit's description.
- It states how to record the returned DOI back into `CITATION.cff` and `README.md`, and that the `CITATION.cff` version check of order 2 still holds after that edit.
- No token is added to CI, no automated deposit exists, and the GitHub-to-Zenodo release integration stays disabled; the procedure says why. No release is blocked on a deposit.
- The procedure is performed once, on the Zenodo sandbox with a release archive, and every step that did not match what the form actually asked is corrected in the document before this story closes. This story makes no real deposit, and the sandbox DOI is never written into `CITATION.cff` or `README.md`; the procedure states that the first real deposit may still need one correction where the sandbox differs from production. Whether the first release took a real DOI (only if a venue asked for one) or skipped it is recorded.

## Code it changes

- `docs/` (new procedure page), linked from `README.md`. No production module, no workflow change.

## Tests it needs

- None automated: the procedure's proof is the one deposit performed against it.

## Evidence it publishes

- The sandbox deposit record and the corrections it caused, filed with the delivery. `CITATION.cff` and `README.md` carry no DOI until a real deposit is made.

## Cancellation

n/a: not cancelled.
