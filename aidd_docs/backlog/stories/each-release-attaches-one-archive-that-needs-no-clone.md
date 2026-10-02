---
type: story
status: ready
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
depends_on:
  - aidd_docs/backlog/stories/the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives.md
  - aidd_docs/backlog/stories/one-citation-names-the-release-and-is-the-attribution-a-reuser-copies.md
  - aidd_docs/backlog/stories/the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary.md
order: 4
---

# Story: Each release attaches one archive that needs no clone

**As** a third-party researcher given one URL and no access to the repository
**I want** each release to carry one download holding the tables, their dictionary, the bundle they came from, both licences and the citation
**So that** I can analyse, reuse and cite that exact release from what I downloaded, and trust that its tables are the published bundle rather than a second, hand-edited set of numbers

Maps to: PRD User Story "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself"; PRD AC "Given a published release, its suite items and reference result bundle carry CC-BY 4.0 while the code stays MIT, and the published results are also available as a tabular export readable outside the repo without running it"; epic Boundaries "one asset per release"; epic decisions "One asset, not several" and "The export is derived, never authoritative"; epic Dependencies rows "The tag, the CHANGELOG and the CI release flow" and "A GitHub Release with an attached asset needs a permission the workflow does not hold"; epic success checks 1, 4, 6 and 7.

Needs: an operator. The owner pushes a `v*` tag to prove the flow end to end, and someone on a machine with no clone opens the downloaded asset. No model run, API key or hardware is required.

Current state: on `v*`, `.github/workflows/ci.yml` runs `verify-tag` and `publish`, which pushes an image. No GitHub Release is created and nothing is attached. The workflow holds `permissions: contents: read`; `publish` adds only `packages: write`. The workflow belongs to `clean-machine-runs-it-and-nothing-reaches-main-unchecked`; this story is the single seam the epic names.

Scope: the first archive carrying open-ended model output (rewriting, document comparison) waits on the spike `aidd_docs/backlog/spikes/may-the-model-outputs-in-the-published-rows-be-redistributed-and-on-what-terms.md`; archives whose rows carry only `predicted_label`, as today's do, do not (owner answer to Q76, option a, 2026-10-01).

## Acceptance

- On a `v*` tag, once `test`, `build` and `verify-tag` succeed, CI builds the export from the bundle at the tagged commit and assembles one archive in a format the three desktop operating systems open without installing anything.
- The archive holds the four tables, the column dictionary, the reference bundle they were derived from (all five parts), `LICENSE`, `LICENSE-DATA`, `CITATION.cff` with the tagged commit stamped into it, and a README naming the release, the commit, the bundle schema version read, what each file is, and how to cite the release.
- The archive is self-describing: no file inside it points at a path that exists only in a clone, and a check fails the build when one does.
- CI creates the GitHub Release for the tag and attaches the archive. `contents: write` is granted only on the job that creates the Release; the workflow-level `contents: read`, `verify-tag` and the image `publish` are unchanged.
- The derivation is proven, not asserted: tables regenerated from the bundle at the tagged commit equal the ones in the archive, so a hand-edited table fails the build.
- The tag, the packaged version, the `CITATION.cff` version and the archive README name the same release, and the README's commit equals the tagged commit; any disagreement fails the build and no Release is created.
- The repository README names where the latest release's archive is and what it holds.

## Code it changes

- `.github/workflows/ci.yml`: a release job after `verify-tag`, with its own scoped permission.
- A small assembly script under `scripts/` (or the export command's own option) that builds the archive and its README and stamps the commit into the shipped `CITATION.cff`.
- `README.md`: where the download is.

## Tests it needs

- `tests/test_ci_workflow.py`: the release job runs only on `v*`, needs `verify-tag`, holds `contents: write` on that job alone, and leaves the workflow-level permission and `publish` unchanged.
- The assembly over the committed bundle: every listed file is present, the archive README and the stamped `CITATION.cff` name the given version and commit, no file references a clone-only path, and an edited table fails the derivation check.

## Evidence it publishes

- The first release carrying the asset: its URL, and a transcript of opening the four tables on a machine with no clone and no Python, filed with the delivery.

## Cancellation

n/a: not cancelled.
