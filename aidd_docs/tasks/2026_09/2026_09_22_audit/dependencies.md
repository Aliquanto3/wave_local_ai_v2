# Codebase Audit: dependencies

Both halves are locked and reproducible (`uv.lock` with hashes, synced with `--locked`; exact-pinned `package.json` with integrity on all 271 lock entries, installed with `npm ci`), and no known CVE shows up. The one real problem is that the project's own vulnerability gate crashes when OSV degrades, and it did so today.

- **Date**: 2026_09_22
- **Scope**: `pyproject.toml`, `uv.lock`, `frontend/package.json`, `frontend/package-lock.json`, `Dockerfile`, `scripts/audit_dependencies.py`, `.github/workflows/ci.yml`
- **Health**: good
- **Findings**: 0 critical, 1 warning, 4 minor

Health: `good` = no critical findings; `fair` = critical findings exist but are isolated and addressable; `poor` = systemic or widespread critical findings.

## Findings

| Sev | Category | Location | Issue | Suggested fix | Effort |
| --- | -------- | -------- | ----- | ------------- | ------ |
| 🟡 | dependencies | `scripts/audit_dependencies.py:72-77` | When pip-audit's OSV backend fails, pip-audit crashes with `ServiceError` and exits **1**, the same code it uses for "vulnerabilities found". The script accepts that code (`not in (0, 1)`) and then runs `json.loads("")`, which ends in a `JSONDecodeError` traceback. This happened today: OSV answered `501 Not Implemented` for 19 of 91 locked packages (starlette, httpx, numpy, psutil, certifi…). The CI "Dependency audit" step on both legs therefore goes red for a reason unrelated to the code, and it reads as a script bug. The gate fails closed, so nothing slips through, but it blocks every merge while OSV is degraded. This is a different code path from logged `tech-debt.md:32` (the script's own `requests.get` at `:83`). | Treat empty or unparseable stdout as a tool failure: raise `RuntimeError("pip-audit failed: " + stderr tail)`. Optionally retry once with `-s pypi`, which succeeded today. | S |
| 🟢 | dependencies | `.github/workflows/ci.yml:50-77` | The `frontend` job runs lint, format, typecheck and tests but no `npm audit`. The Python half blocks on HIGH/CRITICAL (`ci.yml:46-47`), while the dashboard's dependencies, which are shipped to the demo browser, are never scanned in CI. | Add `npm audit --omit=dev --audit-level=high` to the `frontend` job. | S |
| 🟢 | dependencies | `Dockerfile:6,8,24,26,37,39` | All three stages use `FROM python:3.12-slim` (a floating tag), uv is copied from `ghcr.io/astral-sh/uv:0.11.7` (a tag, not a digest), and `libgomp1`/`curl` come from apt unpinned. Rebuilding the same commit later gives a different image under the same `org.opencontainers.image.revision` label. `libgomp1` is llama-server's OpenMP runtime, and the fiche does not record it. A pushed `v*` image is immutable, so this only matters on a rebuild. | Pin both images by `@sha256:` digest, with the tag kept as a comment, as `ci.yml` already does for actions. | S |
| 🟢 | dependencies | `uv.lock`, `frontend/package-lock.json` | Behind latest, all patch or minor: codecarbon 3.3.0 → 3.3.1, cryptography 50.0.0 → 50.0.1, uvicorn 0.52.4 → 0.53.0, react/react-dom 19.2.8 → 19.3.0, typescript-eslint 8.70.0 → 8.70.1, ruff 0.16.4 → 0.16.8. The one major is typescript 6.0.2 → 7.0.2 (dev only). No bump fixes a known advisory. | Bump in one batch. Bump codecarbon on its own with a CHANGELOG note, because it supplies the estimated CPU/RAM energy figures and a version change can shift published estimates. | S |
| 🟢 | dependencies | `pyproject.toml:1-9` | There is no `license` field, although `LICENSE` is MIT, so the package metadata and the GHCR image declare no license. The image also redistributes `pycountry` 26.2.16 (LGPL-2.1-only, pulled in transitively by `codecarbon`) and MPL-2.0 `certifi`. Both are compatible with unmodified library use, and their license files ship in their `dist-info`. | Add `license = "MIT"` and `license-files = ["LICENSE"]`. No action is needed for the LGPL/MPL transitives. | S |

## Top actions

1. Make `audit_dependencies.py` tell "pip-audit crashed" apart from "findings" (row 1, 🟡). This is the only thing that turned today's dependency gate red. Hand off to `aidd-dev:08-debug` (reproducible now) or fold it into the next CI chore together with logged `tech-debt.md:29,32`.
2. Add `npm audit --omit=dev --audit-level=high` to the CI `frontend` job (row 2).
3. Digest-pin the Dockerfile base images and do the batched version bump, with codecarbon bumped separately (rows 3 and 4).

## Coverage

- **Scanned**: dependencies
  - Commands run (shortest decisive output line each):
    - `uv run --frozen python scripts/audit_dependencies.py` => `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` (row 1).
    - `uv run --frozen pip-audit --format json --locked -s osv <exported pylock>` => `pip_audit._service.interface.ServiceError`, `pip-audit exit=1`, stdout 0 bytes. Isolated with a scratch per-package OSV probe => `non200 [('cachecontrol','0.14.4',501), …, ('starlette','1.6.0',501)]` (19/91). No package returned a vuln.
    - `uv run --frozen pip-audit --locked -s pypi <exported pylock>` => `No known vulnerabilities found` (the only skip was the project itself, `no version specified`).
    - `npm audit --omit=dev` (frontend) => `found 0 vulnerabilities`. `npm audit` => `found 0 vulnerabilities`.
    - `npm outdated` and `uv tree --outdated --frozen --depth 1` => row 4.
    - A license survey via `importlib.metadata` over the venv, and via `package-lock.json` `license` fields => Python: only `certifi`/`pathspec` MPL-2.0 and `pycountry` LGPL-2.1-only, plus `detect-secrets` metadata `UNKNOWN` but classifier Apache (dev). npm: `MIT 212, Apache-2.0 18, ISC 12, MPL-2.0 12, BSD 11, BlueOak 2, MIT-0 2, CC-BY-4.0 1, CC0 1`. No GPL/AGPL anywhere.
  - Lockfiles and supply chain:
    - `git ls-files` => `uv.lock` and `frontend/package-lock.json` are tracked.
    - `uv.lock` has no `source = { git | url | path }` entries.
    - `package-lock.json` has 271 `resolved` and 271 `integrity`.
    - CI uses `uv sync --locked` and `npm ci`, the Dockerfile uses `uv sync --locked --no-dev`, and `.python-version` (3.12) and `frontend/.nvmrc` (22.17.1) are tracked.
  - Reproducibility across the three machines holds on the dependency side:
    - Rows carry `commit_sha` and `tree_dirty` (`row_contract.py:105-106`), and the commit pins `uv.lock`.
    - `uv run` re-syncs the venv to the lock before every CLI run, so an installed set that drifts from the lock is not a realistic path.
  - Unused declared dependencies: none.
    - Every runtime dependency is imported (`codecarbon`, `fastapi`, `pynvml`, `psutil`, `dotenv`, `requests`, `uvicorn` in `src/`).
    - `cryptography` is imported only by `scripts/generate_dev_cert.py`, but `codecarbon` → `authlib`/`joserfc` pulls it transitively anyway, so moving it would not shrink the installed set.
    - `httpx` (dev) is needed by FastAPI's `TestClient`.
    - `pyyaml` (dev) is used by `scripts/audit_dependencies.py`.
  - Logged debt not re-filed: `tech-debt.md:29` (PYSEC ids resolve `UNKNOWN`), `:30` (both matrix legs audit the same set), `:32` (the OSV `requests` error escapes as a traceback), `:41` (Dockerfile tag string duplicated).
- **Skipped**: none for this pillar. The OSV-backed pip-audit run could not complete today (OSV returned 501). CVE coverage for Python therefore rests on pip-audit's PyPI advisory source, plus a per-package OSV query in which 72 of 91 packages returned 200 with no vulns and 19 are unverified against OSV.
