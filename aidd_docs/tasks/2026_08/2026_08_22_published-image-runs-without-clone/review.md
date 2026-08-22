# Review: The published image runs the benchmark without a clone

- **Verdict**: approve
- **Diff**: `main...working-tree`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 2 critical, 4 warning, 5 minor — every critical and warning fixed in-branch; of the minors, four were fixed alongside them and one is filed in `aidd_docs/backlog/tech-debt.md`

## Phases

### Phase 1 — Dockerfile and build context

- [x] `.dockerignore` keeps `.env`, weights and result stores out of the context, and the image can hold none of them — `.dockerignore:16-20`; the build stage copies only `pyproject.toml uv.lock README.md src/` (`Dockerfile:31-32`)
- [x] `llama-server --version` exits 0 inside the image with no missing-`.so` error — run locally against the compose-built image: `version: 0.1.2-dev (build 10537, commit bf0040e15)`, exit 0; now also a CI step (`.github/workflows/ci.yml:77-79`)
- [x] `/app/.venv` importable with no source tree present — `uv sync --locked --no-dev --no-editable` (`Dockerfile:34`), runtime copies only `.venv` (`Dockerfile:44`)
- [x] Entry point exits 1 with `error: SLM_MODELS_DIR is not set`; non-root `User`; both OCI labels in `Config.Labels` — run locally: stderr exactly that line, exit 1; `docker inspect` reports `User: app`, `id` reports `uid=999(app)`; a build with both build-args reports both labels back verbatim. All three are CI steps now (`.github/workflows/ci.yml:77-112`)

### Phase 2 — Compose definition

- [x] One image shared by both services — `compose.yaml:7,32`; the build overlay tags it under the same name (`compose.build.yaml`)
- [x] `SLM_MODELS_DIR` / `LLAMA_SERVER_PATH` overridden in `environment:` while `MISTRAL_API_KEY` flows from `env_file` — verified with `docker compose config`: both services render `SLM_MODELS_DIR: /data/models`, `LLAMA_SERVER_PATH: /opt/llama-cpp/llama-server`, and the `.env`'s `MISTRAL_API_KEY` verbatim
- [ ] A real run finds the model at `/data/models/...` and the row lands in the host's results dir — needs a populated host models dir and a live inference run; static review cannot execute. The mount renders correctly (`D:\ia\models` → `/data/models:ro`, `./results` → `/results`)
- [x] `quality` invokes the second console script in the same image — `entrypoint: ["wave-local-ai-v2-quality"]` (`compose.yaml:34`)

### Phase 3 — CI build and publish jobs

- [x] Trigger config lists a tags condition alongside branch and PR — `.github/workflows/ci.yml:4-7`
- [x] `build` runs without any push/write step, `permissions: contents: read` — `.github/workflows/ci.yml:50-112`; it now also runs on a `v*` tag, so `publish` has a real dependency to gate on
- [ ] A `v*` tag produces a `publish` run whose image is pullable anonymously from GHCR — needs a real tag push, and the one-time visibility switch it depends on is now documented (`docs/setup.md`) and carried as an acceptance line on the release story
- [x] `required` needs `[test, build]` and treats `skipped` as passing, `publish` absent from its graph — `.github/workflows/ci.yml:145-161`

### Phase 4 — Pull-and-run docs

- [x] A reader with no clone can pull, fetch `compose.yaml`, populate the weights, and run both CLIs — `compose.yaml` now runs `ghcr.io/aliquanto3/wave_local_ai_v2:${WAVE_IMAGE_TAG:-latest}` with no build section, so the pulled image is what runs; `README.md:119-131` adds the `mkdir -p results` step and names `WAVE_IMAGE_TAG` and `RESULTS_DIR`
- [x] NVIDIA section names a base image, a runtime flag, a changed `llama-server` flag, and the untested-in-CI phrase — `docs/setup.md:78-96`
- [x] The verification note matches what phases 1-3 actually implemented — the three named checks are now real CI steps (`.github/workflows/ci.yml:77-112`) and `README.md:168-183` describes them by the command each one runs

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | functional | 4 | `README.md:160-165`, `.github/workflows/ci.yml:50-68` | The README stated CI proves that `llama-server --version` runs in the built image, that the console script exits 1 with `error: SLM_MODELS_DIR is not set`, and that the OCI labels name source and commit. The `build` job ran `build-push-action` with `push: false` and no `load:`, then stopped — the image never entered the runner's daemon. These are the story's own three "How it is verified without a GPU" checks. | **Fixed.** `load: true` plus the three checks as CI steps (`ci.yml:67-112`): `docker run --entrypoint llama-server <img> --version`; a run with `SLM_MODELS_DIR=` asserting both exit 1 and the exact stderr line; `docker inspect` asserting `.source` equals the repo URL and `.revision` equals `github.sha`. All three verified locally against the built image. `README.md:168-183` now describes them by the command each one runs. |
| 🔴 | functional | 4 | `compose.yaml:2-6,23-27`, `README.md:115-124,143-146` | The pull-and-run path was broken end to end: both services pinned `image: wave-local-ai-v2:local` with `build: context: .`, and the pulled GHCR tag appeared nowhere. A reader holding only `compose.yaml` would fall through to a build with no context. | **Fixed.** `compose.yaml` runs `ghcr.io/aliquanto3/wave_local_ai_v2:${WAVE_IMAGE_TAG:-latest}` and carries no build section; the developer path moved to a tracked `compose.build.yaml` overlay (`docker compose -f compose.yaml -f compose.build.yaml build`), documented in `docs/setup.md`. `publish` pushes both the version tag and `latest`, so the default resolves. Verified: the overlay builds, and `docker compose config` renders both services on the GHCR image with no build stanza. |
| 🟡 | conform | 3 | `.github/workflows/ci.yml:70-76` | `publish` carried no `needs:`, so a `v*` tag pushed to GHCR in parallel with `test` and published even when the test matrix, the fast gate or the dependency audit failed on that commit. | **Fixed.** `publish` is `needs: [test, build]` (`ci.yml:116`). `build`'s `if:` was widened to `pull_request` or a `v*` tag (`ci.yml:55`), because a job that is skipped on the tag event cannot gate anything — the tag's image is now built and smoke-tested before `publish` pushes it. |
| 🟡 | fit | 2 | `compose.yaml` (untracked) | `compose.yaml` was in the working tree but never staged, so it would not reach the commit, the tag, or `raw.githubusercontent.com` — the URL `README.md:123` tells the pull-only reader to fetch. | **Fixed.** `compose.yaml` and `compose.build.yaml` are staged with this story; the README's raw URL is unchanged and resolves once the tag exists. |
| 🟡 | fit | 2 | `compose.yaml:21,36` | The results mount was `./aidd_docs/results`, a clone-shaped path: a pull-only reader got a daemon-created `aidd_docs/results/` that, on Linux, the container's non-root `app` user could not write into. | **Fixed.** The mount is `${RESULTS_DIR:-./results}:/results` with `RUNTIME_RESULTS_PATH` / `QUALITY_RESULTS_PATH` pointing inside it, and both services run `user: "${UID:-1000}:${GID:-1000}"` — still non-root, but the caller's uid, so rows come back owned by whoever made the directory. `README.md:125` adds `mkdir -p results`. `.gitignore` gains `results/*.jsonl` so container rows are not committable. Verified: the image starts and refuses correctly under `-u 1000:1000`. |
| 🟡 | fit | 3 | `.github/workflows/ci.yml:70-98` | A package first pushed by `GITHUB_TOKEN` is private whatever the repository's visibility, so the README's bare `docker pull` fails for a signed-out reader until an owner flips it once. Phase-3 criterion 3 and the story both require an anonymous pull. | **Fixed as documented, deferred as performed.** No API pre-creates a public user package, so the one-time switch is written down in `docs/setup.md` ("Publishing: the one-time GHCR visibility switch"), carried as an acceptance line on `a-release-tag-names-the-code-a-row-can-cite.md`, and named in this story's own evidence section as verified at the first tag. `README.md:178-183` no longer implies CI proves the pull. |
| 🟢 | rot | 1 | `.dockerignore:23,36` | `!aidd_docs/results/*-reference.jsonl` re-included a path that the blanket `aidd_docs/` removed again 13 lines later. | **Fixed** while rewriting the same block for the new results path: both lines dropped. |
| 🟢 | rot | 1 | `.dockerignore:13-14` | `.venv` and `.venv/` were duplicate patterns. | **Fixed** — one pattern. |
| 🟢 | code | 1 | `Dockerfile:12-13` | `LLAMA_SERVER_ASSET` hardcodes `llama-b10537-...` independently of `LLAMA_CPP_TAG`, so the tag appears twice and bumping one alone 404s. | **Filed** in `aidd_docs/backlog/tech-debt.md` — no fix in this branch, per the severity gate. |
| 🟢 | code | 3 | `.github/workflows/ci.yml:65` | `tags:` was inert with `push: false` and no `load:`. | **Fixed** as a side effect of the first critical: the tag now names the image the three smoke steps run against. |
| 🟢 | conform | 1 | `.dockerignore:32-36` | Phase-1 task 1.2 listed `Dockerfile` among the Docker/VCS entries; it was not excluded. | **Fixed** — `Dockerfile`, `compose.yaml` and `compose.build.yaml` added to that block. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 87% (13/15)                                       |
| Files checked | `Dockerfile`, `.dockerignore`, `.gitignore`, `compose.yaml`, `compose.build.yaml`, `.github/workflows/ci.yml`, `README.md`, `docs/setup.md`, `aidd_docs/backlog/stories/the-published-image-runs-the-benchmark-without-a-clone.md`, `aidd_docs/backlog/stories/a-release-tag-names-the-code-a-row-can-cite.md` |
| Unchecked     | P2 a real run writes a row to the host — not-applicable (needs real weights and a live inference run; the epic's fresh-machine walk); P3 anonymous GHCR pull after a tag — not-applicable (needs a tag push plus the one-time visibility switch, now documented and carried on the release story) |
| Unplanned     | `compose.build.yaml` (new, developer build overlay) and `.gitignore` (`results/*.jsonl`) — both consequences of the two critical fixes, not scope creep; the two backlog stories gained one line each for the GHCR visibility step |
