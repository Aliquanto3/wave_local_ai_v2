# Review: The demo address serves over TLS and refuses a keyless request

- **Verdict**: changes-requested (all 🟡 fixed in the review commit; 🟢 filed to `aidd_docs/backlog/tech-debt.md`)
- **Diff**: `main...feat/demo-tls-key`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_21
- **Findings**: 0 critical, 3 warning, 2 minor

## Phases

### Phase 1 — TLS enforcement, unified refusal, store-root guard

- [x] Traversal via `fiche_hash` resolves to `None`, planted escaped file never read — `tests/test_fiche_registry.py:47`, `src/wave_local_ai_v2/fiche_registry.py:56`
- [x] Traversal via `suite_id`/`suite_version` resolves to `pointer_unresolved`, planted well-formed snapshot never read — `tests/test_read_model.py:488`, `src/wave_local_ai_v2/read_model.py:427`
- [x] `..` and absolute-path parts both rejected — `tests/test_path_guard.py`; probed on Windows: `..\x.json`, `/etc/passwd`, `C:\Windows\win.ini`, `\\srv\share\x`, `a/../../x` all `None`
- [x] Missing and wrong key answer identical `detail` and byte-identical bodies — `src/wave_local_ai_v2/service.py:87-104`, `tests/test_service.py` (`test_a_missing_and_a_wrong_key_answer_byte_identical_bodies`)
- [x] Unset or non-existent `SERVICE_TLS_CERTFILE`/`SERVICE_TLS_KEYFILE` raises `SettingsError` naming the variable — `src/wave_local_ai_v2/settings.py:514-521`, `tests/test_settings.py` (`test_load_service_settings_requires_the_tls_pair_to_exist`)
- [x] `uvicorn.run` receives `ssl_certfile`/`ssl_keyfile`; `dashboard_origin` default is `https://` — `src/wave_local_ai_v2/service.py` `main()`, `src/wave_local_ai_v2/settings.py:291`
- [x] Key absent from `capsys` and `caplog` across settings load, startup print, served and refused requests — `tests/test_service.py` (`test_the_key_appears_in_no_logged_or_printed_record`); see 🟢 on what `caplog` can observe

### Phase 2 — Cert-generation script, docs, frontend closure, security review

- [x] Generated pair: SAN holds `127.0.0.1`, `localhost`, the passed host; loads into a real `ssl.SSLContext` — `tests/test_generate_dev_cert.py`
- [x] `localStorage` empty after a key is stored — `frontend/src/api/keyStore.test.ts:17`; confirmed live (`localStorage.length: 0` in the browser capture)
- [x] `evidence/security-review.md` covers every scope item with a resolution per row — `evidence/security-review.md`; two missed gaps added in its post-review addendum

### Phase 3 — Evidence: a real HTTPS run, a keyless transcript, a screenshot

- [x] `serving https://` line and zero-match key search — `evidence/https-run-output.txt`, `evidence/https-run-key-search.txt`
- [x] Two `401`s with identical bodies, no path, store or key fragment — `evidence/keyless-curl-refusal.txt`
- [x] Named refusal screenshot from a real browser — `evidence/browser-refusal-screenshot.png` (was blocked; captured during this review, headless Edge over CDP against the TLS service on `10.42.47.37:8443`)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | code (error-handling) | 1 | `src/wave_local_ai_v2/path_guard.py:24` | `Path.resolve()` raises `ValueError` on a NUL byte, so a stored pointer carrying one turned `read_fiche`/`resolve_suite_definition` into a 500; on `main`, `Path.exists()` swallowed it and degraded to absent. Regression against the plan's "never a 500" decision. | Fixed: catch `ValueError`/`OSError` around the resolve, return `None`; test `test_a_part_carrying_a_nul_byte_returns_none_not_raising`. |
| 🟡 | code (error-handling) | 1 | `src/wave_local_ai_v2/service.py` `main()` | An existing but unloadable pair (swapped cert/key, a directory, not PEM) passes the existence check, `main()` prints `serving https://...`, then uvicorn fails in `Config.load()` with a bare `ssl.SSLError` traceback: the startup line lies and the error is unnamed. | Fixed: load the pair into `ssl.SSLContext` before announcing, refuse naming both variables, exit 1, no bind; tests parametrized over swapped and non-PEM pairs; test fixtures now write a real generated pair. |
| 🟡 | functional | 3 | `evidence/browser-refusal-screenshot.png` | Criterion 3 unmet: screenshot absent, phase and plan `blocked`. | Fixed: captured in this review; phase 3, plan and story set `done`. |
| 🟢 | code (standards) | 1 | `tests/test_service.py` (`test_the_key_appears_in_no_logged_or_printed_record`) | `caplog` cannot see uvicorn's loggers (`uvicorn.run` stubbed, `TestClient` bypasses uvicorn); uvicorn output is covered only by the real-run evidence. | Filed to `tech-debt.md`. |
| 🟢 | rot | 2 | `tests/test_service.py:20`, `tests/test_generate_dev_cert.py:5` | Two hand-rolled `sys.path` inserts for `scripts/`. | Filed to `tech-debt.md`: `pythonpath = ["scripts"]` in pytest config. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (13/13) after fixes; 92% (12/13) before |
| Files checked | `src/wave_local_ai_v2/{service,settings,path_guard,fiche_registry,read_model}.py`, `scripts/generate_dev_cert.py`, `frontend/src/components/KeyGate.tsx`, `frontend/src/api/keyStore.test.ts`, `tests/test_{service,settings,path_guard,fiche_registry,read_model,generate_dev_cert}.py`, `docs/demo.md`, `docs/setup.md`, `.env.example`, `.gitignore`, `pyproject.toml`, `evidence/*` |
| Unchecked     | Phase 3 browser screenshot — fixed |
| Unplanned     | none |
