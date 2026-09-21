# Security review: the demo address serves over TLS and refuses a keyless request

Scope, per the epic's Dependencies table: key handling and leakage, TLS
configuration, bind address, CORS, traversal on the configurable store path,
and what a refusal discloses. Reviewed against the LAN-demo threat model this
epic states (the PRD's Non-Goals exclude a public-internet posture) — not
against an internet-facing model.

A dedicated agent ran a broader automated pass over the full branch diff
(`main...feat/demo-tls-key`, including the untracked phase-2 files) across
the OWASP-style categories (injection, auth bypass, crypto, RCE, data
exposure) beyond this scope table; it reported no findings meeting the
>80%-confidence exploitability bar. Its conclusions are folded into the
per-item rows below.

| Scope item | Finding | Resolution |
| --- | --- | --- |
| **Key handling and leakage** | `_require_key` (`service.py`) uses `hmac.compare_digest`, and now raises one identical `HTTPException` object for both the absent-key and wrong-key branches — closing the prior two-string disclosure. `capsys`/`caplog` are asserted key-free across settings load, the startup print, a served request and a refused one (`tests/test_service.py::test_the_key_appears_in_no_logged_or_printed_record`). The one residual timing signal — an immediate raise with no header vs. a `compare_digest` call with a wrong one — discloses nothing an attacker doesn't already know (whether they sent a header at all). | Accepted as-is: no code change needed beyond phase 1's unification, which is this branch's own fix. |
| **TLS configuration** | `load_service_settings` requires and existence-checks `SERVICE_TLS_CERTFILE`/`SERVICE_TLS_KEYFILE` before the app is built, mirroring `SERVICE_API_KEY`'s unconditional-refusal posture; `main()` has no plain-HTTP path and wires both into `uvicorn.run`. `scripts/generate_dev_cert.py`'s generated key is unencrypted on disk, but private-key-at-rest protection is out of this review's scope (secrets/sensitive data on disk are handled by other processes per this review's own exclusions) and this is a single-operator local demo tool, not a shared host. | Accepted as-is. |
| **Bind address** | `DEFAULT_SERVICE_HOST` stays loopback; `SERVICE_HOST` is an explicit operator opt-in to a LAN bind, unchanged by this branch. `is_loopback_client` keys off the actual TCP peer address (`request.client.host`), never off `SERVICE_HOST` or a header, so binding to a LAN IP for the demo does not weaken or bypass the loopback carve-out — a non-loopback peer still needs the key regardless of what address the service is bound to. | Accepted as-is: no change in this branch's scope. |
| **CORS** | `CORSMiddleware`'s `allow_origins` stays pinned to the single configured `dashboard_origin`, now computed as `https://<host>:<port>` by default (phase 1) so it cannot drift from the address the service actually serves TLS on. No wildcard, no credential-bearing cross-origin surface added. | Accepted as-is. |
| **Traversal on the configurable store path** | Both pointer-resolved reads (`fiche_registry.read_fiche`'s `fiche_hash`, `read_model.resolve_suite_definition`'s `suite_id`/`suite_version`-derived filename) previously joined a configured root with a stored-row value via a raw `Path.joinpath`/f-string with no sanitization — a `fiche_hash` or `suite_id` containing `../` or an absolute path could resolve outside the configured directory. `path_guard.resolve_within_root` (new) now confirms the resolved candidate via `Path.is_relative_to(root.resolve())` before either caller touches the filesystem, returning `None` on any escape (relative `../..` traversal and absolute-path injection both verified in `tests/test_path_guard.py` and the two callers' own traversal tests) — degrading to the existing "not found"/"unresolved" absence, never a read outside the root and never a 500. | **Fixed in phase 1** (this branch, `path_guard.py` + its two call sites) — not a new finding from this review, but the traversal gap this epic named is closed by this branch. |
| **What a refusal discloses** | The unified 401 body (`"missing or invalid X-API-Key"`) carries no path, no store name, no key fragment, and no signal distinguishing absent from wrong (`tests/test_service.py::test_a_missing_and_a_wrong_key_answer_byte_identical_bodies`). The browser-side refusal (`KeyGate.tsx`) states only "This dashboard needs the service's API key" / "The service refused that key. Enter it again." — no path, no store location, no key fragment, no absent-vs-wrong distinction. Re-inspected against the acceptance during phase 2 task 5; no change needed. | Accepted as-is. |

## Summary

One traversal gap (the scope table's own named item) existed before this
branch and is fixed by it (phase 1). Every other scope item was already
compliant or is closed by this branch's own changes; the broader automated
pass found no additional high-confidence finding. No open finding remains.

## Post-review addendum

The branch's `aidd-dev:05-review` found two gaps this report missed, both
fixed in the review commit:

| Scope item | Finding | Resolution |
| --- | --- | --- |
| **Traversal on the configurable store path** | `path_guard.resolve_within_root` raised `ValueError` on a pointer carrying a NUL byte (`Path.resolve()` refuses it), turning a malformed stored `fiche_hash`/`suite_id` into a 500 where `main`'s plain `Path.exists()` had degraded to "absent". | Fixed: the resolve is guarded and returns `None`, the same absence an escape reports. |
| **TLS configuration** | A cert/key pair that exists but cannot be loaded (swapped files, a directory, not PEM) passed the existence check and failed only inside `uvicorn.run`, after `main()` had already printed `serving https://...`, with a bare traceback. | Fixed: `main()` loads the pair into an `ssl.SSLContext` before announcing and refuses with a message naming both variables, exit 1, no socket bound. |
