---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
related_to:
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
  - aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
---

# Epic: A clean machine runs it, and nothing reaches main unchecked

Given only the repository or its published image, a client-side engineer reaches one completed runtime benchmark and one completed quality benchmark by following the documented setup alone — and every commit behind those numbers arrived on `main` through a check suite that could have refused it, under a release tag the numbers can name.

## Context and Value

Two audiences, both named in the PRD's user stories. The client-side developer who wants "to read the repo and its test suite, so that I can independently judge the engineering quality behind the numbers" and "to clone the repo (or pull its container image) and reproduce the published results on my own machine". And the consultant who wants "every code change to pass automated checks, including dependency and security scans, before I rely on it, so that a broken or vulnerable benchmark never reaches a client demo", and "releases tagged with a changelog, so that I can tell a client exactly which version produced the numbers they're looking at".

The epic `quality-scored-comparison-first-three-use-cases` excludes this work in its own Boundaries and points at "a separate, parallel epic" that was never written. This is that epic.

Verified current state, at `a2ffe37`:

- **`README.md` is 0 bytes.** The entry point for the audience whose entire job is to judge the repo is empty. The audit records the repo as "hosted, not presentable" (`2026_08_21_expectations-gap-audit/audit-and-plan.md`, E7).
- **Nothing checks a change.** Zero GitHub Actions workflows, `main` unprotected, no `.pre-commit-config.yaml` and no active hook in `.git/hooks`. `pre-commit` and `detect-secrets` are installed dev dependencies, unwired; `.secrets.baseline` exists. The fast gate in `coding-assertions.md` is run by hand, by discipline — the audit's E12, spec-only and not implemented.
- **No `Dockerfile`, no compose.** The container half of the PRD's reproduction story does not exist.
- **No `CHANGELOG.md`, no git tag.** `pyproject.toml` declares `version = "0.1.0"`, which no commit is bound to and no result row can cite.
- **The runtime is an undocumented external download.** The `llama-server` binary is fetched by hand from outside the repo with no named build, source or checksum — the audit's E11, alongside the machine-fitted constants `N_CPU_MOE = 37`, `THREADS = 8`, the model filename and `LLAMA_CPP_BUILD = "b10537"`.

One correction to the audit's picture, measured rather than assumed: the test suite is **not** stubbed. 99 tests pass in 4.8s at **98% line coverage** (443 statements, 11 missed — `uv run --with pytest-cov pytest --cov=src/wave_local_ai_v2`). The PRD's 80% floor is met before this epic starts a single story. What is missing is not tests: it is that nothing recomputes that number on a change, so today it is nobody's evidence. This epic makes the floor enforced, not the coverage higher. (Audit E15's "no coverage tooling" is accurate; its "99 stubbed tests" is not, and `pyproject`'s description is no longer a placeholder either.)

The value is the PRD's Overview claim that the results are "defensible under a client engineer's scrutiny of the repo itself". Every other epic in this backlog produces numbers. This one produces the repository that a sceptic can check those numbers against — and the sibling epic states plainly that its own "credible artifact" evidence is not fully achievable until this one ships.

## Boundaries

- Includes: `README.md` and a fresh-machine setup path — prerequisites, `llama-server` acquisition by named build tag with its download source (PRD Dependencies), model-weight download by pinned repository revision with checksum verification, environment configuration from `.env.example`, and the two commands that produce one runtime benchmark and one quality benchmark.
- Includes: `pre-commit` wired to the fast gate that already exists in `coding-assertions.md` (ruff check, ruff format check, mypy, detect-secrets against the baseline), turning a manual discipline into a local refusal.
- Includes: GitHub Actions CI on push and on pull request — ruff, ruff format, mypy, pytest with line coverage measured and failing below the PRD's 80% floor, detect-secrets, and a dependency/security audit — on Ubuntu and Windows for the pure-Python tests.
- Includes: the enforcement levels, decided rather than deferred. Lint, format, type-check, tests, the coverage floor and the secret scan are blocking with no waiver path. A dependency or security finding at or above a declared severity is blocking too, but a dated, reasoned, expiring entry in a tracked exception file can unblock it, and that file is published where a client engineer reads it. This settles the PRD's Open Question on whether such findings block a merge or are only logged, for this release.
- Includes: branch protection on `main` requiring the check suite, with no maintainer bypass — an unchecked merge is refused, not discouraged.
- Includes: scoping `.secrets.baseline` to the repository rather than the virtualenv it was generated against. A blocking secret gate whose baseline is an inventory of third-party noise is not a gate (`backlog/tech-debt.md`, 2026-08-21).
- Includes: a `Dockerfile` and a compose definition that run the CLI benchmark, CPU inference path at minimum, with the NVIDIA path documented rather than shipped. The image carries no model weights; its documented first run downloads the pinned GGUF by revision and verifies its checksum (PRD Acceptance Criteria).
- Includes: publishing that image where the audience can pull it. The outcome is "clone **or** pull"; an image that only builds locally does not satisfy it.
- Includes: release tagging with a `CHANGELOG.md` entry per release, and the release version and commit sha exposed to the running code so a row can record them.
- Excludes: the read-only results service, its API key, TLS and the dashboard — their own epic.
- Excludes: every benchmark methodology rule and every task suite. Criterion 19 is the single seam: this epic makes a release version and commit sha exist and be readable at run time; `every-published-row-explains-and-reproduces-itself` writes them into rows and owns the row schema.
- Excludes: unhardcoding `N_CPU_MOE`, `THREADS`, the model filename and `LLAMA_CPP_BUILD`. The row epic claims that work in its own Boundaries; this epic consumes the result rather than duplicating it.
- Excludes: raising test coverage. It is 98%. This epic measures it and holds a floor; it writes tests only for the code it adds.
- Excludes: the `CONTRIBUTING.md` and `aidd_docs/GUIDELINES.md` template placeholders (audit E15). Named below as a decision, not silently dropped.

## Success Evidence

Hand the repository URL to an engineer who has never seen the project, on a machine that is not the development laptop. They follow the README and nothing else. They reach a completed runtime benchmark row and a completed quality benchmark row without asking a question and without applying a fix that is not written down. Then they discard the clone and do the same from the published image.

Five checks, each able to fail:

- A pull request whose lint, format, type, test, coverage or secret check fails cannot be merged — verified by opening one that fails on purpose, not by reading the workflow file.
- A dependency finding above the declared severity blocks the same merge, and is unblocked only by a dated entry in the exception file — verified by letting one expire and watching the check go red again.
- A push straight to `main` that has not been checked is refused, including one from the maintainer.
- Every step of the fresh-machine walk that needed an undocumented fix counts as a failure of this epic, not of the person walking it.
- A release tag exists, its changelog entry names what changed, and a benchmark run at that tag emits a version and commit sha that match it.

Once `done`, record here what the fresh-machine walk actually needed that the README did not say, and whether any dependency waiver was still open at the release.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| GitHub as both CI execution environment and the distribution point clients use | dependency | Named in the PRD's Dependencies. Free-tier Actions minutes on a public repository are assumed sufficient for a two-OS matrix over pure-Python tests; no inference runs in CI. |
| A container registry for the release image | dependency | Named in the PRD's Dependencies. GHCR is the assumed default because it needs no account the project does not already have; not fixed at epic level. |
| The machine-fitted constants and the undocumented runtime binary (audit E11) | dependency | Owned by `every-published-row-explains-and-reproduces-itself`, which makes them roster- and settings-driven. Until it lands, the image runs the declared configuration with documented overrides; a genuinely machine-portable container arrives with that epic, not this one. This epic does own documenting the binary's acquisition. |
| Criterion 19 needs a release identifier to record | dependency | The reverse seam of the same neighbour: this epic provides the tag, version and sha; that epic writes them into rows and degrades explicitly when there is none. Neither blocks the other's start. |
| A prebuilt `llama-server` may not exist for every platform the setup path claims | assumption | Assumed obtainable by release tag for Linux x86_64 (the container's CPU path) and Windows. Where no prebuilt binary exists, that platform's setup path documents building from source rather than silently omitting the platform. |
| CI runs the pure-Python tests only; no runner executes a real inference run | assumption | Accepted. CI proves the code, not the benchmark. The fresh-machine walk, not CI, is what proves a run reproduces. |
| An 80% coverage floor against a suite already at 98% | decision | The PRD's stated initial value is taken as a floor, not a target: a drop from 98 to 81 passes. Whether the floor ratchets upward is deferred to the PRD's own Open Question on thresholds. |
| The declared blocking severity, and a waiver's maximum lifetime | decision | Not fixed at epic level. Both are set during delivery and published alongside the exception file, so the level itself is auditable. |
| Versioning scheme and release cadence | decision | Not decided here. `pyproject` declares `0.1.0` bound to no commit; the first tag binds one. |
| `CONTRIBUTING.md` and `aidd_docs/GUIDELINES.md` still hold template placeholders (audit E15) | decision | Left outside this epic. An empty README is the larger gap and this epic closes it, but a repository whose hooks and CI are documented nowhere else is a real remainder — pull it in or carry it as its own item. |
| `main` is unprotected and the maintainer is currently the only committer | assumption | Protection is accepted as applying to the maintainer too. A gate its owner can wave through is not evidence to a client engineer, and the PRD's acceptance criterion says the platform blocks the merge. |

## Cancellation

n/a — not cancelled.
