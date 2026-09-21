---
objective: "The service binds where configured and serves only over TLS; every /api/* request off loopback is answered or refused by an identical-shaped body that discloses nothing; a configurable store path can never resolve outside its own root; the browser's existing key custody is verified against the named refusal screen; the branch clears a threat-scoped security review before merge."
status: in-progress
---

# Plan: The demo address serves over TLS and refuses a keyless request

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | TLS-terminate `service.py` from configuration (self-signed generated or operator-provided), unify the key refusal into one undistinguishable body, guard the two pointer-resolved filesystem reads against traversal, and close the loop with the demo operator doc and the epic's second success check |
| **Source** | `aidd_docs/backlog/stories/the-demo-address-serves-over-tls-and-refuses-a-keyless-request.md` |

## Phases

| #   | Phase                                                    | File                          |
| --- | --------------------------------------------------------- | ------------------------------ |
| 1   | TLS enforcement, unified refusal, store-root guard         | [`phase-1.md`](./phase-1.md)  |
| 2   | Cert-generation script, docs, frontend closure, security review | [`phase-2.md`](./phase-2.md)  |
| 3   | Evidence: a real HTTPS run, a keyless transcript, a screenshot | [`phase-3.md`](./phase-3.md)  |

## Resources

<!-- External sources only (URLs, docs), not code files. Omit if none consulted. -->

## Decisions

| Decision   | Why   |
| ---------- | ----- |
| `cryptography` becomes a direct runtime dependency (already resolved at `50.0.0` in `uv.lock`, today reached only transitively through `pip-audit → authlib` in the dev group) | The cert-generation script must work for anyone who followed `docs/setup.md`'s `uv sync`, not only a contributor whose dev-group resolution happens to still pull `authlib`. Declaring it directly removes that transitive dependency on an unrelated dev tool's own tree, matches `scripts/audit_dependencies.py`'s existing pattern of a plain Python script (not a shell-out), and needs no new lock resolution since the version is already pinned. |
| TLS is unconditional, mirroring `SERVICE_API_KEY`'s "refuses to start without one" posture — `main()` no longer has a plain-HTTP path, on loopback included | The PRD AC ("the service binds only to a configured address over TLS") is stated without exception, the same way the epic's dependency table already reads the API key's own unconditional refusal. A dev-only plain-HTTP escape hatch would be the knob `settings.py`'s current comment explicitly refused to add for `SERVICE_API_KEY`, for the same reason: a convenience now is the default that ships later. |
| The refusal body is the same literal string for a missing key and a wrong one (`"missing or invalid X-API-Key"`), replacing the two distinct strings `_require_key` raises today | The story's acceptance is explicit that the response must not distinguish absent from wrong. Today's `service.py` already raises two different `detail` strings (`"missing X-API-Key"` vs `"invalid X-API-Key"`) — a real gap `tests/test_service.py` currently asserts as correct and must be corrected alongside the code. |
| A new `path_guard.resolve_within_root(root, *parts)` helper, applied to `fiche_registry.read_fiche` (`fiche_registry_dir / f"{fiche_hash}.json"`) and `read_model.resolve_suite_definition` (`suite_definitions_dir / snapshot_filename(...)`), returning `None` on escape rather than raising | These are the two places a *configured root* is joined with a *pointer value read from a stored row* (`fiche_hash`, `suite_id`/`suite_version`) with no existing sanitization — `snapshot_filename` is a raw f-string today. Neither pointer is attacker-supplied through an HTTP parameter in the current four routes, but the epic's own security-review scope names "traversal on the configurable store path" unconditionally, and a row's provenance is not this story's boundary to assume. `None` matches the existing degrade-quietly contract both callers already have (`read_fiche` returns `None` on a missing file; `resolve_suite_definition` returns `_unresolved(...)` on a missing/unreadable one) — an escape is reported the same way a miss is, never a 500. |
| `serve_dashboard_entry`'s catch-all and the `/assets` `StaticFiles` mount need no change | `full_path` is never joined into a filesystem path — the entry document is always the fixed `index.html`; `StaticFiles` already resolves within its own directory. Verified, not assumed, during explore — recorded here so a reviewer does not re-derive it. |

