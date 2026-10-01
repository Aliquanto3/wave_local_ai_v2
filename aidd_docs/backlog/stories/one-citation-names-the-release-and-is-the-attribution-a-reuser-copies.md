---
type: story
status: ready
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
depends_on:
  - aidd_docs/backlog/stories/the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives.md
order: 2
---

# Story: One citation names the release and is the attribution a reuser copies

**As** an academic or technical reviewer citing the published results
**I want** a machine-readable citation naming the work, its release version and its author, and the same form stated as the attribution CC-BY 4.0 requires
**So that** I can cite the exact release I used and comply with the licence by copying one string, instead of choosing between two descriptions of the same work

Maps to: PRD User Story "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself"; PRD context "an academic or technical reviewer of a published write-up ... expects ... licensing to hold up on their own"; epic Boundaries "`CITATION.cff` at the repository root"; epic decision "Attribution and citation are one string, stated once"; epic Dependencies row "The attribution string and the `CITATION.cff` author identity"; epic success checks 3 (attribution string), 4 (citation) and 7 (version agreement, the citation half).

Needs: an operator. The owner supplies the author identity (pseudonym, real name, ORCID, affiliation) before this story closes; the epic defers that choice to the owner at release and this story does not make it. No model run, API key or hardware is required.

Current state: no `CITATION.cff`, no attribution string. Tags `v0.1.0` and `v0.2.0` exist; `verify-tag` refuses a tag whose name and packaged version disagree.

## Acceptance

- `CITATION.cff` at the repository root validates against the published Citation File Format schema and names the work's title, the packaged version, the author identity the owner supplied, the repository URL, and both licences (MIT for the code, CC-BY 4.0 for the data).
- The repository copy names no commit: a committed file cannot name the commit that contains it. The commit is stamped into the copy shipped in the release archive (order 4), and the repository copy says so in a comment.
- The `CITATION.cff` version equals the packaged version, held by a test on every push. Since `verify-tag` already refuses a tag that disagrees with the packaged version, a tag whose name disagrees with `CITATION.cff` cannot publish, without this story touching `verify-tag`.
- The attribution string in `README.md`'s licence section is derived from `CITATION.cff` (work, author, version, licence, link), and a check fails when the two disagree, so the attribution and the citation cannot drift apart.
- A reader holding only `CITATION.cff` and the README produces a citation for a given release, version, author and year, without asking anyone.

## Code it changes

- `CITATION.cff` (new), `README.md` (attribution string in the licence section), a test module for the version and attribution agreement. No workflow change.

## Tests it needs

- `CITATION.cff` parses and its version equals `build_info.version()`; a fixture with a mismatched version fails.
- The README attribution string equals the one derived from `CITATION.cff`; an edited README string fails.

## Evidence it publishes

- The citation GitHub renders from `CITATION.cff` on the repository page ("Cite this repository"), screenshot or transcript filed with the delivery.

## Cancellation

n/a: not cancelled.
