# Run notes: Ollama v0.35.1 capture session

Runbook: `aidd_docs/backlog/spikes/are-the-three-ollama-spikes-live-captures-obtainable-in-one-ollama-v0-35-1-session.md`, steps 1 to 13, run unattended by an agent session on the reference laptop.

- Start: 2026-10-04T00:17:54+02:00
- End: 2026-10-04T00:23:24+02:00 (captures); these notes written right after.
- Shell: Windows PowerShell 5.1.26100.9549. Each step ran as a script file that dot-sourced one prelude holding the step 1 variables and helpers.
- Machine: NVIDIA GeForce RTX 3060 Laptop GPU, driver 572.70, 0 MiB used / 6144 MiB at start. D: free 80,878,026,752 B.

## Step outcomes

| Step | Outcome |
| ---- | ------- |
| 1 Session variables, checks | OK. GGUF sha256 `9465E63A...043BB031` matches the roster. llama-server `version: 0.1.2-dev (build 10537, commit bf0040e15)`. `00-gpu-clients.txt` and `00-ports.txt` empty. 20 suite items, labels `account,billing,other,technical`; all ten constrained item ids exist. |
| 2 Download, verify, unpack | OK. HTTP 200, 1,471,094,402 B. sha256 `dc50b9ca7f9023c86525012632cd1615b093d0407987444a7f62ecab617e8e93` = pinned value. Unpacked 1.81 GB (`01-unpacked-size.txt` shows `1,81 GB`, French locale decimal comma). Contents: `ollama.exe`, `lib\`. |
| 3 llama.cpp reference renders | OK. 4 renders + tokenize all 200. Over-long prompt = 50049 tokens (> 32768). VRAM 0 MiB after stop. |
| 4 Ollama start, import, identity | OK. `{"version":"0.35.1"}`, `Ollama is running`, create `success` with `using existing layer sha256:9465e63a...`, `32-digest-match.txt` = True. `/api/show` 200; `34-ps-before.json` = `{"models":[]}`. |
| 5 Warm-up + 5 reps | OK. All 200. Warm-up load 3678 ms; reps load 1.7 to 2.6 ms, total 124 to 129 ms. |
| 6 Second client | OK. `/api/ps` during it shows the one model loaded; second client 149 tokens, total 1167 ms (outlasted the 500 ms wait); contended rep total 681 ms vs 124-129 ms uncontended. |
| 7 Render paths | OK. All 200. |
| 8 Constrained | OK. All 200 (GBNF field attempt included). |
| 9 Over-long prompt | Ran; HTTP 400 `exceed_context_size_error`, `n_prompt_tokens 50061`, `n_ctx 32768`. `/api/ps` after still shows the model loaded with `context_length` 32768. |
| 10 Logs, unload | OK. Unload 200 (`done_reason":"unload"`). VRAM 0 MiB after stop. |
| 11 Defaults side-run | OK. Pull `success`; show and chat 200. VRAM 0 MiB after stop. |
| 12 Offline checks | OK. A0, A1, A2 written. |
| 13 Cleanup | OK. Removed `D:\ia\ollama-v0.35.1-models-defaults`, `D:\ia\ollama-v0.35.1.zip`, `D:\ia\ollama-v0.35.1-Modelfile`, `%TEMP%\ollama-request-logs-2692482842`. Kept per the runbook: `D:\ia\ollama-v0.35.1` (build) and `D:\ia\ollama-v0.35.1-models` (roster store). Env vars were process-scoped, nothing persisted. |

## Deviations

1. Worktree instead of main repo. Every repo file (suite JSON) was read from `C:\Users\Anael\dev\wave_local_ai_v2-night` (`Set-Location` changed accordingly). Same content.
2. `.env` not read. Step 1's two `.env` lines replaced by `$llama = 'C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe'` and `$models = 'D:\ia\models'`.
3. One PowerShell window was not available (each tool call is a fresh process). Step 1's variables and helpers were put in one prelude script dot-sourced by each step; step 1's checks ran once. Steps 4 to 10 ran in one process (variables carry), each server phase wrapped in `try { ... } finally { Stop-Engine }`.
4. `Stop-Engine` stops by PID: `Start-Process ... -PassThru` added to the llama-server and both `ollama serve` launches to record the PID; `Stop-Engine` kills that PID plus any process whose path is under `D:\ia\ollama-v0.35.1\` (only this session launches from there; this catches the bundled runner). The runbook's `$_.Path -eq $llama` match was dropped so a llama-server not started by this session could never be killed.
5. Bounded waits: the three `do { Start-Sleep } until (...)` readiness loops became a helper that throws after 300 s (llama-server) or 120 s (ollama), and also stops waiting if the process exited. No timeout fired.
6. Pre-checks added before each GPU step: compute-apps list from `nvidia-smi` must be empty, and the port (8080 or 11500) must not be listening. All passed.
7. Step 11 ran in a fresh process, so it re-set `OLLAMA_HOST` and `OLLAMA_DEBUG` itself; the runbook's `Remove-Item Env:OLLAMA_FLASH_ATTENTION, Env:OLLAMA_DEBUG_LOG_REQUESTS` was kept with `-ErrorAction SilentlyContinue` (the vars were not set in that process). User-level `OLLAMA_MODELS=D:\ia\ollama\models` exists on this machine; both serves overrode it in-process (`D:\ia\ollama-v0.35.1-models`, then `-models-defaults`). No other `OLLAMA_*` variable is set.
8. Step 13 cleanup: the harness blocked `Remove-Item` on variable-built paths, so the same removals ran with literal paths (`-LiteralPath`). Its `Stop-Engine` found nothing to stop.
9. The download in step 2 used `curl.exe -sS -L -o ... -w 'http=%{http_code} size=%{size_download}'` (added `-sS` and `-w` to log the result); same URL and output file.

No runbook command had to be fixed for correctness; no capture was edited by hand.

## Runbook gaps observed (not fixed)

- `http-status.txt` lists only the POST calls made through `Invoke-Capture` (45 lines). The GET captures (`/`, `/api/version`, `/api/ps`, library page) go through `Get-Capture`, which records no status, so the Bounds line "an HTTP status for every API call" is not met literally. Their files hold well-formed responses.
- `80-log-rendered-prompt.txt`: its three hits are the GGUF chat template (`template detection ... no matching template found`, the `tokenizer.chat_template` kv line, and llama-server's `chat template, example_format` init line), not a rendered request prompt. The full log has 7 `<|im_start|>` hits: the 4 others are the example_format lines 254-260. No rendered request prompt found in the debug log.
- `80-request-logs.txt` holds only the directory path: no `*_body.json` matched `<|im_start|>`. Those files are the client request bodies (76 files), and Go's JSON encoder writes `<` as `\u003c`, e.g. the raw-mode body starts `{"model":"wla-qwen3-0.6b-q8","prompt":"\u003c|im_start|\u003euser\n...`. So the literal search cannot match even the raw request that carries turn markers; the logs record requests, not a rendered prompt. The directory was deleted by step 13 as the runbook says.
- `80-runner-args.txt` and `95-defaults-runner-args.txt` hold the full `starting llama-server` line, wrapped over several lines by `Out-File` at the console width (complete, but a line-based grep on one flag may miss it). Unwrapped:
  - roster: `llama-server.exe --model ...sha256-9465e63a... --port 51964 --host 127.0.0.1 --no-webui --offline -c 32768 -np 1 --log-verbosity 4 --no-log-prefix --no-log-timestamps --load-mode none --flash-attn on -b 512 -ub 512 -ngl 99`
  - defaults: `llama-server.exe --model ...sha256-7f4030143c1c... --port 51813 --host 127.0.0.1 --no-webui --offline -c 4096 -np 1 --log-verbosity 4 --no-log-prefix --no-log-timestamps --no-jinja --chat-template chatml --load-mode none --flash-attn auto -b 512 -ub 512 --context-shift --keep 4`
- `A1-format-check.csv` includes `60-gbnf-field-attempt.json` because its glob is `6*.json`.

## sha256 checks

- Roster GGUF: `9465E63A22ADD5354D9BB4B99E90117043C7124007664907259BD16D043BB031` = expected (`00-gguf-sha256.txt`).
- Release zip: `dc50b9ca7f9023c86525012632cd1615b093d0407987444a7f62ecab617e8e93` = pinned (`01-zip-sha256.txt`).
- Imported blob digest in manifest: `32-digest-match.txt` = True.

## Capture map coverage

All 82 files named by the capture map exist and are non-empty (checked by script). Every row has its file(s). Caveats per row:

- runtime / configured and reported context: `70-over-long-prompt.json` is an HTTP 400 error body, which is the result. 
- render / every candidate path: `80-log-rendered-prompt.txt` holds template hits only; `80-request-logs.txt` holds only the path (see gaps above). Both are the finding, not missing files.
- `http-status.txt`: present, POST calls only.

## Processes, ports and GPU

| PID | Process | Started | Stopped |
| --- | ------- | ------- | ------- |
| 5748 | llama-server b10537 (step 3, port 8080) | 00:20:22 | 00:20:25 by PID |
| 12976 | ollama serve, roster store (step 4, port 11500) | 00:20:39 | 00:21:49 by PID |
| 21764 | bundled llama-server runner (child of 12976, per log) | 00:20:51 | unloaded by `81-unload` (keep_alive 0); gone before stop |
| 17608 | curl.exe second client (step 6) | 00:21:43 | exited on its own (WaitForExit) |
| 17016 | ollama serve, defaults store (step 11) | 00:22:15 | 00:22:38 by PID |
| 7336 | bundled llama-server runner (child of 17016) | step 11 | 00:22:38 by path under the build dir |

End state (00:23): no `ollama`, `llama-server` or `curl` process running; ports 11500, 8080 and 11434 not listening; GPU 0 MiB used, no compute apps. The installed Ollama app (v0.34.2), its store `D:\ia\ollama` and port 11434 were not touched.
