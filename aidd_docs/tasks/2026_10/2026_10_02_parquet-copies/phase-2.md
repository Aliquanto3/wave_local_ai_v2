---
status: done
---

# Instruction: the release jobs' on-demand trigger and Parquet step

## Architecture projection

```txt
.
├── .github/workflows/ci.yml               ✅ workflow_dispatch; release-build + release-publish; publish push-only
└── tests/test_ci_workflow.py              ✅ trigger, no Release, write token only in release-publish
```

## Steps

1. `on: workflow_dispatch`.
2. Story 15's `release` job splits in two.
   - `release-build` (`contents: read`): `if` = test succeeded and not cancelled, and either a `v*` tag push with build and verify-tag succeeded, or a dispatch. Checkout with `persist-credentials: false`, no uv cache, `uv sync --locked --group release`, "Name the release" (`RELEASE_TAG` = the pushed tag, or `v<packaged version>` on a dispatch), the Parquet tests (`--no-cov`), the assembly with `--parquet`, the archive's sha256 as a job output, the zip uploaded as the `release-archive` artifact (the `upload-artifact` pin the test job already uses).
   - `release-publish` (`contents: write`, `actions: read`): tag push only, needs test, build, verify-tag and release-build. No checkout and no action: `gh run download` fetches the artifact, `sha256sum -c` checks it against release-build's digest, then `gh release create --verify-tag --repo`.
3. `publish` only on a push event, so a dispatch on a tag ref pushes no image.
4. Workflow tests: release-build's `if` and needs, the dispatch trigger and the naming step, only `release-publish` creates a Release and it is push-only, `publish` push-only, only `release-publish` holds `contents: write` and it runs no project code, the digest handoff, pyarrow installed only in release-build (and absent from the Dockerfile), pinned in the `release` group only, no `default-groups` override; the coverage-gate test admits release-build's one targeted pytest run.
