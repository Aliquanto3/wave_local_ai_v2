---
type: story
status: ready
source: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
parent: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
depends_on: aidd_docs/backlog/stories/every-push-and-pull-request-runs-a-check-suite-that-can-refuse-it.md
order: 5
---

# Story: The published image runs the benchmark without a clone

**As** a client-side developer who would rather pull an image than rebuild a toolchain
**I want** a published container image that runs the CLI benchmark on the CPU path and carries no model weights
**So that** the "clone **or** pull" half of the reproduction promise holds, instead of an image that only its author can build

## Acceptance

- A `Dockerfile` builds an image that installs the project from the committed lockfile and carries the `llama-server` CPU build pinned to the same release tag the setup path of order 1 names, fetched at build time with its checksum verified.
- The image ships no model weights and no `.env`. Its documented first run downloads the pinned GGUF by revision and verifies its checksum, per the PRD acceptance criterion on the published image.
- A compose definition runs both CLIs with the models directory and the results directory mounted from the host and the environment supplied from the host's own `.env`, so weights are downloaded once and result rows survive the container.
- The NVIDIA path is documented, not shipped: the base image, the runtime flag and the server flags that change are written down, and stated as untested in CI because no runner has a GPU.
- The image runs the declared configuration with documented overrides, and says plainly that the machine-fitted constants (`N_CPU_MOE`, `THREADS`, the model file name, the llama.cpp build) are fitted to the development laptop and that a genuinely machine-portable container arrives with `every-published-row-explains-and-reproduces-itself`, not here.
- The image is built on every pull request, build only, so a change that breaks the image is caught before the tag that would publish it.
- On a version tag the image is published to GHCR under that version, pullable by a reader with nothing but a public pull.
- The image carries OCI labels naming the source repository and the commit it was built from.
- The README documents the pull-and-run path beside the clone path, at the same level of detail, including the first-run weight download.

## Files it creates or changes

- `Dockerfile` (new) — CPU path, no weights, pinned `llama-server` with checksum.
- `compose.yaml` (new) — both CLIs, models and results volumes, `.env` from the host.
- `.dockerignore` (new) — keeps `.venv`, caches, `.env` and result stores out of the build context.
- `.github/workflows/ci.yml` — the build-on-pull-request job and the publish-on-tag job, reusing the summary check of order 3.
- `docs/setup.md`, `README.md` — the pull path and the documented NVIDIA section.

## How it is verified without a GPU

- The image builds on the Ubuntu CI runner, which has no GPU and no model weights.
- Configuration smoke test: running the entry point in the image with `SLM_MODELS_DIR` unset exits 1 and prints `error: SLM_MODELS_DIR is not set`, which proves the package, its console script and its settings path are wired without starting `llama-server` (`src/wave_local_ai_v2/__init__.py:154`).
- Binary smoke test: `llama-server --version` inside the image succeeds on CPU, proving the pinned runtime is present and executable with no model and no GPU.
- Label check: `docker inspect` on the built image reports the source repository and the commit it was built from.
- The full CPU inference run through the image belongs to the epic's fresh-machine walk, not to CI, and is recorded there.

## Cancellation

n/a — not cancelled.
