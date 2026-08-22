---
type: story
status: ready
source: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
parent: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
depends_on: aidd_docs/backlog/stories/the-fast-gate-refuses-a-bad-commit-before-it-is-written.md
order: 3
---

# Story: Every push and pull request runs a check suite that can refuse it

**As** a consultant who relies on the benchmark before a client demo
**I want** every change checked automatically on Ubuntu and Windows, with dependency findings blocking at a declared severity
**So that** a broken, untyped, untested or vulnerable benchmark is refused by the platform rather than by someone's memory

## Acceptance

- One workflow runs on push and on pull request, on `ubuntu-latest` and `windows-latest`, Python 3.12, installing with `uv sync --locked` so CI resolves the committed lockfile instead of a fresh solve.
- Blocking with no waiver path: `ruff check .`, `ruff format --check .`, `mypy src/`, `pytest` with line coverage over `src/wave_local_ai_v2` failing below 80%, and `detect-secrets` against the repository-scoped baseline of order 2.
- The 80% floor is a floor, not a target: the suite measures 98% today (443 statements, 11 missed), so a drop to 81% passes. Whether the floor ratchets is left to the PRD's own open question on thresholds.
- The coverage report is uploaded as a build artifact per operating system, so the number is retrievable from the run rather than only asserted by an exit code.
- `pytest-cov` is a declared dev dependency and coverage is configured in `pyproject.toml`, so the local command and the CI command measure the same thing; the current `uv run --with pytest-cov` invocation stops being the only way to get a number.
- A dependency and security audit runs on every push and pull request and blocks the merge on any finding of high severity or above. This settles, for this release, the PRD's open question on whether such findings block or are only logged.
- A high or critical finding is unblocked only by an entry in a tracked waiver file naming the advisory id, the affected package, the reason, the date it was opened, its expiry date and its owner. The audit fails when a blocking finding has no matching entry, when a matching entry has expired, and when an entry's expiry is more than 90 days after the date it was opened.
- The waiver file is linked from the README, so the declared severity and every open exception are readable by the client engineer the epic is written for, not buried in workflow YAML.
- No job starts `llama-server`, downloads model weights, or requires a GPU or a cloud credential. CI proves the code; the fresh-machine walk proves the benchmark.
- The matrix is fronted by one summary job with a stable name that succeeds only when every matrix leg succeeded, so branch protection has a single check to require as the matrix grows.
- A pull request that breaks lint, drops coverage below the floor, or plants a secret is red and cannot be argued green — verified by opening one, not by reading the workflow file.
- A waiver entry backdated past 90 days turns the audit red again, and the run names which entry expired.
- Coverage output (`.coverage`, any XML or HTML report) is gitignored; the stray `.coverage` currently sitting untracked in the working tree stops being a candidate for accidental commit.

## Files it creates or changes

- `.github/workflows/ci.yml` (new) — the matrix, the five blocking checks, the coverage artifact, the summary job.
- `scripts/audit_dependencies.py` (new) — runs the audit, applies the waiver file, exits non-zero on an unwaived, expired or over-long waiver.
- `docs/dependency-waivers.yml` (new) — the waiver entries, empty at first, with the declared blocking severity and the 90-day maximum stated in its header.
- `tests/test_audit_dependencies.py` (new) — the waiver logic under test, since it is code that decides a merge.
- `pyproject.toml` — `pytest-cov` in the dev group, coverage configuration.
- `.gitignore` — coverage output.
- `README.md` — the link to the waiver file and one line on what blocks a merge.

## How it is verified without a GPU

- Every check is pure Python over the repository. The test suite already stubs HTTP and never starts `llama-server` (`aidd_docs/GUIDELINES.md`), which is what makes a GPU-free two-OS matrix possible at all.
- GitHub-hosted runners carry no GPU and no model weights; nothing in the workflow assumes either.
- The waiver rules are verified by unit test rather than by waiting for a real advisory: an unwaived high finding fails, a current waiver passes, an expired one fails, and one whose lifetime exceeds 90 days fails.
- The suite's ability to refuse is verified by one deliberately failing pull request per blocking check, kept as the evidence this story publishes.

## Cancellation

n/a — not cancelled.
