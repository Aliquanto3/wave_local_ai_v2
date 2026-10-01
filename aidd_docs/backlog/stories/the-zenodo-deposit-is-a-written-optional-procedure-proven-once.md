---
type: story
status: proposed
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

Maps to: PRD Open Question "Whether each release also receives an archival DOI (Zenodo or equivalent). Desirable for citation, deliberately optional for this release, and not an acceptance criterion"; epic Boundaries "a Zenodo deposit written as a manual, optional procedure"; epic decision "A DOI is optional and manual for this release"; epic Dependencies row "Zenodo's own metadata and licence vocabulary".

Needs: an operator. The owner, with a Zenodo account, performs the deposit once against a release archive from order 4. No model run, API key or hardware is required.

Blocked: owner question Q40 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` (whether the procedure is proven against the Zenodo sandbox or by a real, permanent deposit of a release).

## Acceptance

- A procedure under `docs/` states what to upload (the release archive, unchanged), which metadata to enter and where each value comes from in `CITATION.cff`, which licence to select for the deposit, and how the archive's mixed terms (the parts `LICENSE-DATA` names as not granted, and any drawn item's own terms) are stated in the deposit's description.
- It states how to record the returned DOI back into `CITATION.cff` and `README.md`, and that the `CITATION.cff` version check of order 2 still holds after that edit.
- No token is added to CI, no automated deposit exists, and the GitHub-to-Zenodo release integration stays disabled; the procedure says why. No release is blocked on a deposit.
- The procedure is performed once, on the target Q40 settles, and every step that did not match what the form actually asked is corrected in the document before this story closes. Whether the first release took a DOI or skipped it is recorded.

## Code it changes

- `docs/` (new procedure page), linked from `README.md`. No production module, no workflow change.

## Tests it needs

- None automated: the procedure's proof is the one deposit performed against it.

## Evidence it publishes

- The deposit record (sandbox or real, per Q40) and the corrections it caused, filed with the delivery; the DOI, if one was taken, in `CITATION.cff` and `README.md`.

## Cancellation

n/a: not cancelled.
