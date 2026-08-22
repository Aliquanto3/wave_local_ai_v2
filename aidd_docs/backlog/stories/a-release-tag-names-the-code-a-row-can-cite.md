---
type: story
status: ready
source: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
parent: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
depends_on:
  - aidd_docs/backlog/stories/every-push-and-pull-request-runs-a-check-suite-that-can-refuse-it.md
  - aidd_docs/backlog/stories/the-published-image-runs-the-benchmark-without-a-clone.md
order: 6
---

# Story: A release tag names the code a row can cite

**As** a consultant asked which version produced a number
**I want** each release to carry a semver tag, a changelog entry, and a version and commit sha the running code can read
**So that** I can name the exact code behind a client's table, including from a container that has no git checkout

## Acceptance

- `CHANGELOG.md` exists and carries one entry per release naming what changed, not a list of commit subjects.
- A release is an annotated semver tag `vX.Y.Z`. The first tag binds the `0.1.0` that `pyproject.toml` has declared since the repository started and that no commit has ever been bound to.
- The packaged version is read at run time from installed metadata, with no second hardcoded copy that can drift, and a check refuses a tag whose name and packaged version disagree.
- The commit sha is readable where there is no git checkout — inside the published image and from an installed distribution — because it is injected at build time and exposed through the same surface as the version.
- The exposure degrades explicitly: with no injected build information and no git available, the sha reads as an explicit null rather than a stale, fabricated or last-known value.
- The image label of order 5 and the sha the code reports name the same commit; a mismatch is a defect, not a rounding.
- This story exposes the two values and writes nothing into a result row. The row fields, the dirty-tree flag and the row-level fallback belong to `rows-name-the-code-and-the-tree-that-produced-them.md`, which consumes this surface — the seam the epic names as Criterion 19's single boundary. No row schema changes here.
- `README.md` states which release the committed `*-reference.jsonl` evidence was produced under, or states plainly that it predates the first tag rather than implying a version it never carried.
- The first tag's release checklist includes the one-time GHCR visibility switch: a package first pushed by `GITHUB_TOKEN` is private whatever the repository's visibility, and no API pre-creates a public user package, so the owner sets it to public once under the package settings and the checklist records that an anonymous `docker pull` was tried afterwards and succeeded. Order 5 documents the step; this story is where it is actually performed.

## Files it creates or changes

- `CHANGELOG.md` (new) — one entry per release.
- `src/wave_local_ai_v2/build_info.py` (new) — the version from installed metadata, the sha from injected build information, an explicit null when neither is available.
- `tests/test_build_info.py` (new) — the resolution order and the degradation.
- `.github/workflows/ci.yml` — the tag-versus-packaged-version check, and the sha injected into the built distribution and the image.
- `Dockerfile` — the injected build argument feeding both the label and the readable value.
- `README.md` — the provenance of the committed reference evidence.

## How it is verified without a GPU

- Pure unit tests with installed metadata and the injected environment stubbed: version present, sha injected, sha absent, both absent. No inference, no network, no model.
- The tag-versus-version agreement is a string comparison inside the workflow, run on the tag itself.
- The image half is verified on the Ubuntu runner: build with the sha injected, then read the value back out of the running container and compare it against the OCI label and against the sha the workflow was triggered on.

## Cancellation

n/a — not cancelled.
