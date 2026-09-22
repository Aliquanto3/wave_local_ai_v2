# Codebase Audit: security

The results service's gate is sound (constant-time compare, mandatory TLS, no proxy headers, no docs surface, path-guarded pointers); the one real gap is that the gate accepts the `.env.example` placeholder or any one-character key, with no attempt limiting.

- **Date**: 2026_09_22
- **Scope**: full codebase (`src/wave_local_ai_v2/`, `scripts/`, `frontend/src/`, `.github/workflows/ci.yml`, `Dockerfile`)
- **Health**: good
- **Findings**: 0 critical, 1 warning, 3 minor

Health: `good` = no critical findings; `fair` = critical findings exist but are isolated and addressable; `poor` = systemic or widespread critical findings.

## Findings

| Sev | Category | Location | Issue | Suggested fix | Effort |
| --- | -------- | -------- | ----- | ------------- | ------ |
| 🟡 | security | `src/wave_local_ai_v2/settings.py:251-253` | `load_service_settings` refuses only an empty `SERVICE_API_KEY`. The shipped placeholder (`.env.example:51`, `service-key-replace-me`) and a one-character key both start the service, and `setup.md`'s `cp .env.example .env` step puts that placeholder in place. `_require_key` (`service.py:73-104`) has no attempt limiting, so a short key is brute-forceable from the LAN. `docs/demo.md:13-17` tells the operator to generate a `token_urlsafe(32)` key, but nothing in the code enforces it. The data behind the gate is read-only benchmark output, so the impact is limited to the epic's claim that the pitch runs "only with the key". | Refuse the placeholder value and any key shorter than 32 characters in `load_service_settings`, with a `SettingsError` that quotes the `demo.md` generation command. This also covers brute force, so no rate limiter is needed. | S |
| 🟢 | security | `src/wave_local_ai_v2/service.py:133-285` | No security response headers: no `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`/`frame-ancestors`, `Referrer-Policy`, and no `Cache-Control: no-store` on `/api/*`. The key travels in a header rather than a cookie, and the dashboard performs no state-changing action, so clickjacking and CSRF have nothing to act on. | Add one small middleware that sets the five headers. Use `no-store` on `/api` so the second laptop's browser cache keeps no result JSON after the demo. | S |
| 🟢 | security | `frontend/vite.config.ts:12` | The dev proxy targets `http://127.0.0.1:8000` while the service is TLS-only (`service.py:292`), so `npm run dev` cannot reach the API. It also relays every request from `127.0.0.1`, so `is_loopback_client` (`service.py:85`) lets any client of the Vite dev server through without a key. This only becomes an exposure if someone runs `vite --host`. | Target `https://127.0.0.1:8000` with `secure: false` (the dev cert), and add a one-line comment that the dev server must never be bound off loopback because the proxy launders the key gate. | S |
| 🟢 | security | `scripts/generate_dev_cert.py:96-97` | The unencrypted private key is written with `write_bytes`, so it gets default permissions (0644 under a typical POSIX umask). Other local accounts on a shared demo laptop can read it. | Create `key.pem` with mode `0o600` (`os.open(..., 0o600)`, or `chmod` after the write). This is a no-op on Windows. | S |

## Top actions

1. Enforce key strength at startup: refuse the placeholder and keys under 32 characters (row 1, 🟡). This one change closes both the default-key and the brute-force paths. Hand off to `aidd-dev:07-refactor` (security axis).
2. Add a security-headers middleware with `no-store` on `/api` (row 2). This is the same small refactor pass as action 1.
3. Fix the Vite dev proxy target and document its loopback caveat, and tighten `key.pem` permissions (rows 3 and 4). Both are one-line changes.

## Coverage

- **Scanned**: security
  - Checked with no finding:
    - The key gate uses `hmac.compare_digest` on bytes and returns an identical 401 whether the key is absent or wrong (`service.py:87-104`).
    - `proxy_headers=False` (`service.py:336`).
    - `openapi_url`, `docs_url` and `redoc_url` are all `None` (`service.py:145-147`).
    - CORS is restricted to one origin, `GET` only (`service.py:255-260`).
    - TLS is mandatory and the cert/key pair is pre-loaded (`service.py:305-315`).
    - The SPA catch-all refuses `api/` and serves only a fixed `index.html` (`service.py:279-283`).
    - Row-derived pointers are resolved through `path_guard.resolve_within_root` (`read_model.py:482`, `fiche_registry.py:56`). `fiche_registry.py:82` is reached only after the guarded read succeeds.
    - Cloud keys travel in headers (`x-goog-api-key`, `Authorization: Bearer`), never in URLs (`google_client.py:150,266,293,337`, `mistral_client.py:127,234`). No `verify=False` anywhere.
    - The browser key is kept in `sessionStorage` only (`frontend/src/api/keyStore.ts`). There is no `dangerouslySetInnerHTML`, `innerHTML` or `console.*` in `frontend/src`.
    - CI: `permissions: contents: read` at the top, `packages: write` only in `publish`, every action pinned by SHA, no `pull_request_target`. `.dockerignore:30` excludes `.git/`, so the persisted checkout token cannot enter the image.
    - The Dockerfile runs as non-root `app` and verifies the llama-server tarball by sha256 (`Dockerfile:16`).
  - Commands run:
    - `grep -E "verify=False|shell=True|eval(|exec(|pickle|yaml.load(|os.system|dangerouslySetInnerHTML|innerHTML|Popen"` over the tree (excluding `node_modules`, `dist`, `.venv`) => only list-form `subprocess.run`/`Popen`, and `yaml.safe_load` (`audit_dependencies.py:94`).
    - `git grep -E "AIza…|sk-…|hf_…|ghp_…|BEGIN PRIVATE KEY"` over tracked files => no match. `git ls-files .env` => empty (`.env` exists locally, untracked). `dev-certs/` is gitignored (`.gitignore:17`). <!-- pragma: allowlist secret -->
    - `uvx bandit -q -r src scripts` => `5 B404, 7 B603, 4 B607`, all `Severity: Low`, all list-form subprocess with fixed argv. `HEAD:` prefixes the only path-bearing git argument (`fiche_registry.py:116`). Not reported as findings.
  - Stale debt noted but not re-filed:
    - `aidd_docs/backlog/tech-debt.md:9` (`mistral_api_key` repr leak) is fixed: `settings.py:144` carries `repr=False`, and so do `google_api_key` (`:146`) and `ServiceSettings.api_key` (`:214`).
    - `tech-debt.md:38` (actions on mutable tags) is fixed: every `uses:` in `ci.yml` is SHA-pinned.
    - Both rows should be closed.
  - Not a finding: a DNS-rebinding attack against the keyless loopback path would need a certificate for the attacker's hostname. TLS is unconditional and the SAN covers only `127.0.0.1`, `localhost` and the `--host` values (`generate_dev_cert.py:46`), so the browser refuses the handshake.
- **Skipped**: none for this pillar. There was no dynamic test against a running service; the analysis is static only.
