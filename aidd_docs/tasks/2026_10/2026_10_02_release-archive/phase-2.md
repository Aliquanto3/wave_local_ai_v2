---
status: done
---

# Instruction: the `release` job and the README pointer

## Architecture projection

```txt
.
├── .github/workflows/ci.yml       ✅ release job
├── README.md                      ✅ "Release archive" subsection
└── tests/
    └── test_ci_workflow.py        ✅ release job assertions
```

## Steps

1. `release` job: `needs: [test, build, verify-tag]`, `if: startsWith(github.ref, 'refs/tags/v')`, `permissions: contents: write`; checkout, setup-uv, `uv sync --locked`, run the build (which verifies), then `gh release create`.
2. Tests: the job runs only on `v*`, needs the three jobs, is the only job holding `contents: write`, the workflow-level permission stays `contents: read`, `publish` keeps its needs and permissions, and the job's build step runs before the Release step.
3. README: where the latest release's archive is and what it holds; the stale "Once releases ship an archive" sentence updated.
4. Evidence: one local build into a temp dir, listing and verify output in `evidence/`.
