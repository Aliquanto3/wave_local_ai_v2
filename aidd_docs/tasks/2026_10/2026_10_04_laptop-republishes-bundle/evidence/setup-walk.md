# Fresh-clone setup walk (2026-10-04, laptop-mobile-gpu)

The walk follows `docs/setup.md` alone from a new directory. The clone was
throwaway: `git clone C:\Users\Anael\dev\wave_local_ai_v2-night <scratch dir>\clone-walk`,
branch `feat/night-run-2026-10-02` at `32da6f9`, deleted at the end. The models
directory `D:\ia\models` and the pinned build were reused: the walk under test
is the setup, not the download.

| Step (setup.md) | What happened | Gap? |
| --- | --- | --- |
| 1 `git clone`, `uv sync` | `uv sync` resolved Python 3.12.13 (the host default is 3.14.4) and installed in 3 s | no |
| 1 `uv run pre-commit install` | Not run: setup.md marks it the contributor step, not needed to run the benchmarks | no |
| 2 `llama-server` `b10537` | Reused `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\`, which holds both the build and the `cudart` DLLs, as setup.md asks | no |
| 3 weights + checksum | `sha256sum` matched both roster checksums (`649d7508...` flagship, `9465e63a...` Qwen3-0.6B) | no |
| 4 `.env` from `.env.example` | `SLM_MODELS_DIR`, `LLAMA_SERVER_PATH`, `MACHINE_ID=laptop-mobile-gpu`, `COMPUTE_MODE=gpu` filled. `.env.example` ships `MISTRAL_API_KEY=sk-replace-me` and `GOOGLE_API_KEY=AIza-replace-me`; the CLIs read any non-empty value as a key, so a key-less walk that keeps them sends the placeholders to both providers. Emptied both lines | **G1** |
| 4 `MACHINE_ID`, `COMPUTE_MODE` | Set in `.env` to `laptop-mobile-gpu` / `gpu`; each bench command set `COMPUTE_MODE` and `ROSTER_ENTRY_ID` in its own environment, which wins over `.env` as section 4 states | no |
| 4 run profiles | Every run resolved its declared profile with no operator override: `qwen3.6-35b-a3b-ud-iq4xs@laptop-mobile-gpu/gpu`, `qwen3-0.6b-q8@laptop-mobile-gpu/gpu`, `qwen3-0.6b-q8@laptop-mobile-gpu/cpu_only` | no |
| 4.2 / 4.3 verdicts | A second run decided against its own first needs the reference path pointed at a file holding only the first run's rows, and the first run at an empty file; setup.md named only the opt-out (an empty file) and the committed-bundle default | **G2** |
| 4.3 cloud key | `MISTRAL_API_KEY` injected into the two quality commands' environment only (owner decision D6), `QUALITY_PROVIDERS=local,mistral`, `GOOGLE_API_KEY` empty; `google skipped: not enabled in QUALITY_PROVIDERS` | no |
| 6.1 promote, merge, check | Run from the worktree against the clone's live stores (`RUNTIME_RESULTS_PATH`, `QUALITY_RESULTS_PATH`, `FICHE_REGISTRY_DIR`), as section 6.1 step 3 names them | no |

Rows carry `commit_sha` `32da6f9709738426f3a7d34abdcf79275c4091ec` and
`tree_dirty: false`: the clone's tree was clean (its `.env` is ignored).

## Gaps found, and the fix in `docs/setup.md`

- **G1**: `.env.example`'s placeholder keys are read as keys. Section 4 now says to
  empty both key lines until real keys are set at step 4.3.
- **G2**: deciding a second run against its own first. Section 4.2 now says how to
  point the reference path at the first run's rows, and the first run at an empty
  file.

No regression in code surfaced from the walk itself. The republication surfaced two
in the export (`bundle_export.py`): a cloud row's `retry_budget` keyed by provider and
a suite definition's `level` / `divergence_tolerance` had no column-dictionary entry,
so the export refused the current-schema bundle; both are covered by
`tests/test_bundle_export.py::test_the_current_bundle_exports`.
