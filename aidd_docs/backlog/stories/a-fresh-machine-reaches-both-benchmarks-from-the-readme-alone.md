---
type: story
status: ready
source: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
parent: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
order: 1
---

# Story: A fresh machine reaches both benchmarks from the README alone

**As** a client-side developer who has just been handed the repository URL
**I want** the README and the setup path it links to name every prerequisite, download and command
**So that** I reach one runtime row and one quality row without asking a question or applying a fix that is not written down

## Acceptance

- `README.md` is no longer empty (it is 0 bytes today): it states what the benchmark is, the two audiences it serves, the rule that the quality table and the runtime table are never merged, and links the methodology it is measured against.
- The setup path names the `llama-server` build by its release tag and its download source, per platform. Linux x86_64 (the container's CPU path) and Windows are covered; where no prebuilt binary exists for a platform the setup path documents building from source rather than omitting the platform silently.
- The build tag the committed reference evidence was produced under (`b10537`) is named as such, so a reader can tell the pinned build from the build they happen to download.
- Model weights are named by source repository, revision, file name and checksum, with the command that verifies the checksum before the first run.
- Every key of `.env.example` is documented with what it holds and which command needs it. A key that no command currently reads — `GOOGLE_API_KEY` is read by nothing in `src/` — is either removed or documented as reserved for the second judge, never left ambiguous.
- The runtime CLI is documented as running with no cloud credential at all, and the quality CLI as the only one requiring `MISTRAL_API_KEY`, so the local half can be reproduced without buying API access (PRD user story: reproduce the local half without cloud provider credentials).
- Both commands are documented with what each produces: `wave-local-ai-v2` appends one runtime row with its hardware fiche, `wave-local-ai-v2-quality` appends one row per (item, model).
- The results layout is documented: `aidd_docs/results/runtime.jsonl` and `quality.jsonl` are per-machine append targets and untracked, the two `*-reference.jsonl` files are curated committed evidence that no CLI ever writes to, and the reader is linked to `aidd_docs/results/README.md`, which states what each reference row supports and what was deliberately excluded from it.
- The energy caveat appears on the page a client engineer reads first, not only in internal memory: energy and carbon figures are estimates unless a row's per-channel method label says otherwise, GPU draw via NVML is a real measurement, and CPU on Windows is TDP-estimated with no RAPL access and can be off by a factor of 2 to 3 under thermal throttling.
- The declared minimum hardware for the roster model behind the committed evidence is stated before the download steps, so a reader knows whether the machine can run it before fetching several gigabytes.
- `CONTRIBUTING.md` exists and holds no template placeholder: it states the fast gate, the before-push test command, and points at `aidd_docs/GUIDELINES.md`.
- Every command in the setup path is copy-pasteable and labelled with the platform it is for; no step reads "adapt as needed".

## Files it creates or changes

- `README.md` — currently 0 bytes; becomes the entry point and links everything below.
- `docs/setup.md` (new) — the fresh-machine walk: prerequisites, `llama-server` acquisition, weight download and checksum, `.env`, first runtime run, first quality run.
- `CONTRIBUTING.md` (new) — the gate and the review rules a contributor needs; the epic left this file outside its scope as a decision, and it is pulled in here rather than carried as a separate story.
- `.env.example` — only if a key is removed or annotated under the acceptance rule above.

## How it is verified without a GPU

- Documentation only: no code path, no `llama-server`, no model download in any automated check.
- Three checks that run anywhere: every relative link in the new pages resolves to a file that exists; the documented key set and `.env.example` agree exactly; the two documented command names match `[project.scripts]` in `pyproject.toml`.
- Every step before generation — clone, `uv sync`, `.env` from the example, binary download, weight download and checksum verification — completes on a machine with no NVIDIA GPU. Only the two benchmark commands need the runtime, and they are labelled as the point where the GPU-bearing machine is required.
- The epic's fresh-machine walk, not CI, is what proves this story. Each step of that walk that needed an undocumented fix is recorded against this story as a failure of the documentation.

## Cancellation

n/a — not cancelled.
