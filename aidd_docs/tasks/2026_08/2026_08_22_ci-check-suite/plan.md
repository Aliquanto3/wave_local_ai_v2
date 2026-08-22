---
objective: "A CI workflow runs the fast gate, coverage-gated tests, and a waiver-checked dependency audit on every push and pull request, on Ubuntu and Windows, behind one stable required check."
status: in-progress
---

# Plan: Every push and pull request runs a check suite that can refuse it

## Overview

| Field      | Value                                                                                                                   |
| ---------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Goal**   | Server-side CI mirrors the local fast gate, adds coverage-gated tests and a severity-blocked dependency audit, on a two-OS matrix behind one required check |
| **Source** | `aidd_docs/backlog/stories/every-push-and-pull-request-runs-a-check-suite-that-can-refuse-it.md`                        |

## Phases

| #   | Phase                          | File                          |
| --- | ------------------------------- | ----------------------------- |
| 1   | Coverage plumbing               | [`phase-1.md`](./phase-1.md)  |
| 2   | Dependency audit tool           | [`phase-2.md`](./phase-2.md)  |
| 3   | CI workflow                     | [`phase-3.md`](./phase-3.md)  |
| 4   | Docs and enforcement evidence   | [`phase-4.md`](./phase-4.md)  |

## Resources

| Source                                                                 | Verified                                                                                                                              |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| `uv audit --help`, `uv audit` (installed `uv 0.11.7`)                    | Native, but marked experimental (`--preview-features audit` needed to silence the warning) and has no `--format`/JSON option in this version — can't drive machine-readable severity gating. |
| `pip-audit --help` (installed via `uv tool run`, resolves to `pip-audit 2.10.1`) | Has a stable `--format json` and an `-s osv` service option.                                                                          |
| `pip_audit._format.json` source (read from the installed package)        | JSON schema per finding is `{id, fix_versions, aliases, description}` — no severity field anywhere in the output.                     |
| `pip_audit._service.interface.VulnerabilityResult` source                | Confirms the dataclass never carries severity, at any stage of the pipeline, not just the formatter.                                  |
| `https://github.com/astral-sh/setup-uv`                                  | Inputs: `version`, `enable-cache`, `cache-dependency-glob`, `restore-cache`, `save-cache`; current major tag is `v10`.                 |
| `https://docs.astral.sh/uv/guides/integration/github/`                   | Confirms the `uv sync --locked` + `python-version` matrix pattern Astral recommends for CI.                                           |

## Decisions

| Decision                                                                                                   | Why                                                                                                                                                                                                 |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Use `pip-audit`, not `uv audit`, for the dependency scan                                                    | `uv audit` is experimental with no JSON output in the installed version; `pip-audit --format json` is stable and scriptable. Verified by reading both tools' `--help` output and running them.       |
| `scripts/audit_dependencies.py` resolves severity itself via the OSV API (`database_specific.severity`), not from `pip-audit`'s output | `pip-audit` never reports severity (verified from its source). A finding whose severity can't be resolved is treated as blocking (fails closed) rather than silently passing.                        |
| CI's fast-gate step is `uv run pre-commit run --all-files`, not four separate ruff/mypy/detect-secrets commands | Guarantees CI runs the exact same command set as the local hook — the story's own constraint ("not a different set") — since both read the one `.pre-commit-config.yaml`.                            |
| Coverage is configured in `pyproject.toml` (pytest addopts), so plain `uv run pytest` — the existing pre-push hook command — measures coverage too | The local command and the CI command become the same invocation, satisfying the acceptance criterion directly instead of duplicating flags only in the workflow file.                                |
| The dependency audit runs on every matrix leg, not only `ubuntu-latest`                                     | The lock file has platform-marker-only dependencies (e.g. `colorama; sys_platform == 'win32'`); `pip-audit`'s marker evaluation would silently skip them on the OS where they aren't installed. Running per-leg costs one extra network round trip, not correctness. |
