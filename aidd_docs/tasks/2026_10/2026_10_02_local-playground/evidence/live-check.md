# Live check: playground on loopback, qwen3-0.6b-q8 (2026-10-03)

Machine: this laptop (`MACHINE_ID=laptop-mobile-gpu`), pinned build
`llama-b10537-bin-win-cuda-12.4-x64`, models in `D:\ia\models`. Service on
`https://127.0.0.1:8443` with a throwaway self-signed cert generated into a
temp dir (`scripts/generate_dev_cert.py --out-dir <temp>`), `SERVICE_DEMO_MODE=true`,
every store path (`RUNTIME_RESULTS_PATH`, `QUALITY_RESULTS_PATH`,
`FICHE_REGISTRY_DIR`) pointed into the same temp dir. Service stopped by its
PID; every llama-server it launched was stopped by the playground itself.

| Step | Request | Answer |
| ---- | ------- | ------ |
| Keyless from loopback | `GET /api/playground/options` | `401 {"detail":"missing or invalid X-API-Key"}` |
| Options | `GET /api/playground/options` (key) | `200`, four roster ids, `["allowed","disabled"]`, caps 4000/512, `loaded: null`, `holder: null` |
| Start | `POST /api/playground/session {"roster_entry_id":"qwen3-0.6b-q8"}` | `200 {"roster_entry_id":"qwen3-0.6b-q8","profile_id":"qwen3-0.6b-q8@laptop-mobile-gpu/gpu"}`; one `llama-server.exe` (PID 36500) |
| Run refused while the playground holds | `POST /api/console/runs` (runtime, same entry, gpu) | `409 {"message":"the playground holds a local model","holder":{"session":"playground",...}}` |
| Chat, `disabled` | `POST /api/playground/chat` | `200`, 19 `{"delta"}` lines, no `{"reasoning"}`, final `{"thinking_policy":"disabled","finish_reason":"stop","error":null}` ([`chat-disabled.ndjson`](./chat-disabled.ndjson)) |
| Chat, `allowed` | `POST /api/playground/chat` | `200`, 119 `{"reasoning"}` lines then 8 `{"delta"}` lines, final policy `allowed` ([excerpt](./chat-allowed-excerpt.ndjson)) |
| No timing forwarded | `grep -c timings chat-*.ndjson` | `0` in both |
| Switch | `POST /api/playground/session {"roster_entry_id":"qwen3-1.7b-q8"}` | `200`; PID 36500 gone, one new `llama-server.exe` (PID 26960) |
| Stop | `DELETE /api/playground/session` | `200 {"stopped":true}`; no `llama-server.exe` left; options `loaded: null`, `holder: null` |

Nothing recorded: after the service stopped, a search for the prompt marker
`quokka-amber-7731` across the service's stdout and stderr logs, the temp store
directory and `aidd_docs/results/` returned 0 files; the temp store directory
held only the empty fiche directory (no store file was created); `git status
aidd_docs/results` was clean.

Not covered here (operator, second laptop): the `aidd-dev:11-browser-qa`
videos and the browser-side search of the prompt used in them.
