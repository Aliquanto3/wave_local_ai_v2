---
type: spike
status: open
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parents:
  - aidd_docs/backlog/stories/ollama-runtime-rows-stand-beside-llama-cpp-rows-on-the-same-artifact.md
  - aidd_docs/backlog/stories/ollama-quality-rows-pass-a-prompt-parity-gate-or-publish-as-observations.md
  - aidd_docs/backlog/stories/the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md
  - aidd_docs/backlog/stories/what-a-default-ollama-install-costs-is-published-as-its-own-figure.md
related_to:
  - aidd_docs/backlog/spikes/can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md
  - aidd_docs/backlog/spikes/does-ollama-expose-the-prompt-it-finally-rendered.md
  - aidd_docs/backlog/spikes/which-constrained-decoding-mechanism-does-ollama-expose.md
---

# Spike: Are the three Ollama spikes' live captures obtainable in one Ollama v0.35.1 session

## Question

Can one operator sitting on the reference laptop, following one runbook against a pinned Ollama v0.35.1 build and the reference llama.cpp b10537 server, produce every live capture that the Bounds of the three blocked Ollama spikes name, saved to one named folder, with no placeholder left to fill?

## Decision

Whether the three spikes `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`, `does-ollama-expose-the-prompt-it-finally-rendered.md` and `which-constrained-decoding-mechanism-does-ollama-expose.md` can each be concluded from one session's captures, and so whether their parent stories (engine epic orders 6, 7, 8 and 11, and through them order 12) can leave `Blocked:`, or which capture fails and keeps which spike blocked. This spike decides nothing about Ollama itself: the three spikes keep their own questions, and their findings are written there.

## Bounds

- Evidence needed: the capture folder `D:\ia\ollama-v0.35.1-captures` holding every file in the capture map below, produced by the runbook below on the reference laptop in one sitting; `http-status.txt` listing an HTTP status for every API call.
- Stop when: every capture each of the three spikes' Bounds names is produced (each row of the capture map has its file), or a step fails in a way the runbook cannot continue past, which is recorded with its captured output as the finding that keeps the dependent spikes `blocked`.
- Execution tag: `install + local run`. Desk research on 2026-10-03 only fixed the commands; nothing was installed, downloaded or run.
- Closes:
  - `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`: unblocks order 6 (`ollama-runtime-rows-stand-beside-llama-cpp-rows-on-the-same-artifact.md`) and, with order 6, order 11 (`what-a-default-ollama-install-costs-is-published-as-its-own-figure.md`).
  - `does-ollama-expose-the-prompt-it-finally-rendered.md`: unblocks order 7 (`ollama-quality-rows-pass-a-prompt-parity-gate-or-publish-as-observations.md`), which also needs order 6.
  - `which-constrained-decoding-mechanism-does-ollama-expose.md`: unblocks order 8 (`the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md`), which also needs orders 7 and 6 and order 5 (`ready`).
  - Order 12 (`the-campaign-answers-whether-each-variant-helps-or-hurts-a-small-model.md`) is reached through order 8; it stays blocked through order 9 by the compressor spike `which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement.md`, which this session does not cover.
- Prerequisites:
  - Machine: the reference laptop (RTX 3060 Laptop 6 GB, Windows 11), on mains power, with the GPU free: no Ollama app, no `llama-server`, no other GPU workload. The runbook runs one engine at a time and checks VRAM after each stop.
  - Disk: at least 8 GB free on `D:`. Known sizes: release zip 1.47 GB (1,471,094,402 B), the imported roster blob 0.64 GB (a copy of the 639,446,688 B GGUF), the default `qwen3:0.6b` pull 0.52 GB (523 MB on the library page). The unpacked build's size is not published; step 1 records it, and 4 GB is budgeted for it.
  - Ports: 11500 (Ollama, off its default 11434 so an installed Ollama app and its store are untouched) and 8080 (the reference engine's `default_port` in `aidd_docs/roster/engines.json`) both free.
  - Versions: Ollama `v0.35.1` (commit `b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce`, `ollama-windows-amd64.zip`); llama.cpp `b10537` at `LLAMA_SERVER_PATH` from the repo's `.env`; roster `qwen3-0.6b-q8` (`aidd_docs/roster/models.json`, file `Qwen3-0.6B/Qwen3-0.6B-Q8_0.gguf` under `SLM_MODELS_DIR`, sha256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`); suite `classification-support-routing` version 4.
  - Tools: Windows PowerShell 5.1 or PowerShell 7, with the built-in `curl.exe`, `Expand-Archive` and `nvidia-smi`. No Python, `uv`, API key or account is needed. Network for about 2 GB of downloads (the zip and the default pull).
- Time: about 60 to 90 minutes in one sitting. Download of the zip and unpack 10 to 25 min (network bound); llama.cpp reference renders 3 min; Ollama start, import and identity captures 5 min; warm-up plus five counted repetitions with 10 s cooldowns 2 min; second client, renders, raw mode and the 21 constrained/unconstrained generations 5 min; over-long prompt 2 min; defaults side-run including the 0.52 GB pull 5 to 10 min; offline checks 2 min; recording the findings in the three spikes 20 to 30 min.
- Cost: electricity only. No paid provider, no API key, no account. Assumption, not measured: about 0.1 to 0.2 kWh at a 100 to 150 W laptop draw for about an hour.

### Runbook

Run every block in one PowerShell window opened at the main repo root `C:\Users\Anael\dev\wave_local_ai_v2`, in order. Each block's variables carry into the next. Request bodies go through UTF-8 files (`--data-binary "@file"`) rather than inline `-d '{...}'`: Windows PowerShell 5.1 strips embedded double quotes from native-command arguments, which PowerShell 7.3 changed (`https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing`, read 2026-10-03), so the inline JSON in the three spikes' Outcome commands would reach the server unquoted on this laptop's default shell. The FR prompt's accents also survive only through a file.

Request values, all from the repo:

- Items (`src/wave_local_ai_v2/suite_data/classification-support-routing.json`): renders on `billing-01` (first EN item) and `billing-fr-01` (first FR item), as the order 7 story's `Blocked:` line names; runtime repetitions, second client, raw mode and over-long prompt on `billing-01`; the ten constrained/unconstrained pairs on `billing-01`, `technical-01`, `account-01`, `other-01`, `billing-fr-01`, `technical-fr-01`, `other-fr-01`, `billing-de-01`, `technical-de-01`, `account-de-01` (all four labels, three languages).
- Label set: the suite's `expected_label` values, `account`, `billing`, `other`, `technical`, the categories each prompt names. Order 5 has not landed (`src/wave_local_ai_v2/prompt_variants.py` holds `baseline` only), so the label set stands in for the `constrained_output` variant's declared format, the substitution spike `which-constrained-decoding-mechanism-does-ollama-expose.md` Bounds already allow; record it.
- Quality sampling (renders, raw mode, constrained, second client): `quality_cli.LOCAL_SAMPLING` (`src/wave_local_ai_v2/quality_cli.py` lines 101-112): `seed` 20260821, `temperature` 0, `top_k` 0, `top_p` 1.0, `presence_penalty` 0; plus the roster's `min_p` 0; `num_predict` 32 = the suite's `max_output_tokens`; `think: false` = the suite's `thinking_policy: disabled`.
- Runtime sampling (warm-up and counted repetitions): `RUNTIME_SEED` 20260822 (`src/wave_local_ai_v2/__init__.py` line 49) and the roster entry's `server_flags.sampler` (`temperature` 0.6, `top_p` 0.95, `top_k` 20, `min_p` 0, `presence_penalty` 1.5); `num_predict` 32.
- Runner options, identical on every Ollama request (a differing `num_ctx`, `num_batch`, `num_gpu` or context-shift setting reloads the model, per spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`): `num_ctx` 32768 (`server_flags.context_size`), `num_batch` 512, `num_gpu` 99 (`n_gpu_layers`), plus `shift: false`, `truncate: false`, `keep_alive: -1`.

Ollama API fields used, each read at tag `v0.35.1` on 2026-10-03: `model`, `messages`, `stream`, `think`, `format`, `options`, `keep_alive` on `POST /api/chat`, and `prompt`, `raw` on `POST /api/generate` (`https://github.com/ollama/ollama/blob/v0.35.1/docs/api.md`, chat parameters lines 494-515, generate lines 42-59); option names `seed`, `num_predict`, `top_k`, `top_p`, `min_p`, `temperature`, `presence_penalty`, `num_ctx`, `num_batch`, `num_gpu` (same file, lines 377-410); `keep_alive: -1` and `0` (`docs/faq.mdx` lines 297-318); `shift`, `truncate`, `_debug_render_only` and the response's `_debug_info.rendered_template` (`api/types.go` lines 109-121, 158-170, 541-553: in source, not in the docs); `GET /`, `GET /api/version`, `POST /api/show` (`model`, `verbose`), `GET /api/ps` (`docs/api.md` lines 1409-1430, 1735-1760, 1822-1850; `server/routes.go` lines 2038-2073); `ollama serve`, `ollama create MODEL -f FILE`, `ollama pull MODEL` (`docs/cli.mdx` lines 112-145; `cmd/cmd.go` lines 2420-2490); `FROM /path/to/file.gguf` (`docs/import.mdx` lines 36-52); the standalone zip (`docs/windows.mdx` lines 82-104); `OLLAMA_HOST`, `OLLAMA_MODELS`, `OLLAMA_DEBUG`, `OLLAMA_DEBUG_LOG_REQUESTS`, `OLLAMA_FLASH_ATTENTION` (`envconfig/config.go` lines 315-338); the request-log directory `%TEMP%\ollama-request-logs-*` (`server/inference_request_log.go` lines 25, 107-108). llama.cpp b10537: `GET /health` (200 `{"status":"ok"}` once loaded, 503 while loading) and `POST /apply-template` (`messages`, returns `prompt`) (`https://github.com/ggml-org/llama.cpp/blob/b10537/tools/server/README.md` lines 463-475, 721-731, read 2026-10-03); `chat_template_kwargs` on `/apply-template` and `POST /tokenize` (`content`, `add_special`) as the repo already uses them (`src/wave_local_ai_v2/local_client.py` lines 315-365). Release hash: the GitHub release API asset `digest` and the release's `sha256sum.txt` both give `dc50b9ca7f9023c86525012632cd1615b093d0407987444a7f62ecab617e8e93` for `ollama-windows-amd64.zip` (`https://api.github.com/repos/ollama/ollama/releases/tags/v0.35.1`, `https://github.com/ollama/ollama/releases/download/v0.35.1/sha256sum.txt`, read 2026-10-03).

1. Session variables, prerequisite checks and helpers:

```powershell
Set-Location C:\Users\Anael\dev\wave_local_ai_v2
$v = 'v0.35.1'; $d = "D:\ia\ollama-$v"; $cap = "$d-captures"
$h = 'http://127.0.0.1:11500'; $l = 'http://127.0.0.1:8080'
$dotenv = Get-Content .env
$llama  = ($dotenv | Select-String '^LLAMA_SERVER_PATH=(.+)$').Matches[0].Groups[1].Value.Trim()
$models = ($dotenv | Select-String '^SLM_MODELS_DIR=(.+)$').Matches[0].Groups[1].Value.Trim()
$gguf = Join-Path $models 'Qwen3-0.6B\Qwen3-0.6B-Q8_0.gguf'
New-Item -ItemType Directory -Force $cap | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding $false

(Get-FileHash $gguf -Algorithm SHA256).Hash | Out-File -Encoding ascii "$cap\00-gguf-sha256.txt"      # expect 9465E63A22ADD5354D9BB4B99E90117043C7124007664907259BD16D043BB031
& $llama --version *>&1 | Out-File -Encoding utf8 "$cap\00-llama-server-version.txt"                  # expect b10537
Get-PSDrive D | Select-Object Free | Out-File "$cap\00-disk-free.txt"                                    # expect >= 8 GB
Get-Process | Where-Object { $_.ProcessName -match '^(ollama|llama-server)' } | Out-File "$cap\00-gpu-clients.txt"   # expect empty
Get-NetTCPConnection -State Listen -LocalPort 11500,8080 -ErrorAction SilentlyContinue | Out-File "$cap\00-ports.txt" # expect empty
nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total --format=csv | Out-File "$cap\00-gpu.txt"

$suite = Get-Content -Raw -Encoding UTF8 src\wave_local_ai_v2\suite_data\classification-support-routing.json | ConvertFrom-Json
$item = @{}; foreach ($i in $suite.items) { $item[$i.item_id] = $i }
$labels = @($suite.items.expected_label | Sort-Object -Unique)       # account, billing, other, technical
$overText = $item['billing-01'].prompt + (' billing' * 50000)       # meant to exceed 32768 tokens; step 2 counts it

$runner  = @{ num_ctx = 32768; num_batch = 512; num_gpu = 99 }
$quality = @{ seed = 20260821; temperature = 0; top_k = 0; top_p = 1.0; min_p = 0; presence_penalty = 0; num_predict = 32 }
$runtime = @{ seed = 20260822; temperature = 0.6; top_k = 20; top_p = 0.95; min_p = 0; presence_penalty = 1.5; num_predict = 32 }

function Invoke-Capture([string]$base, [string]$route, $body, [string]$name) {
  $f = "$cap\$name.body.json"
  [IO.File]::WriteAllText($f, ($body | ConvertTo-Json -Depth 10 -Compress), $utf8)
  $code = curl.exe -s --data-binary "@$f" -o "$cap\$name.json" -w '%{http_code}' "$base$route"
  "$name $code" | Tee-Object -Append -FilePath "$cap\http-status.txt"
}
function Get-Capture([string]$url, [string]$name) { curl.exe -s $url -o "$cap\$name" }
function New-ChatBody([string]$prompt, [hashtable]$sampling, [bool]$think = $false) {
  [ordered]@{ model = 'wla-qwen3-0.6b-q8'; stream = $false; think = $think; keep_alive = -1; shift = $false; truncate = $false
              messages = @(@{ role = 'user'; content = $prompt }); options = $runner + $sampling }
}
function Stop-Engine {
  Get-Process | Where-Object { $_.Path -like "$d\*" -or $_.Path -eq $llama } | Stop-Process -Force
  Start-Sleep 3; nvidia-smi --query-gpu=memory.used --format=csv,noheader
}
```

2. Download, verify and unpack the pinned build (can run ahead of the session):

```powershell
curl.exe -L -o "$d.zip" "https://github.com/ollama/ollama/releases/download/$v/ollama-windows-amd64.zip"
$zh = (Get-FileHash "$d.zip" -Algorithm SHA256).Hash.ToLower(); $zh | Out-File -Encoding ascii "$cap\01-zip-sha256.txt"
if ($zh -ne 'dc50b9ca7f9023c86525012632cd1615b093d0407987444a7f62ecab617e8e93') { throw "ollama-windows-amd64.zip sha256 mismatch: $zh" }  # pragma: allowlist secret
Expand-Archive -Path "$d.zip" -DestinationPath $d
"{0:N2} GB" -f ((Get-ChildItem -Recurse -File $d | Measure-Object Length -Sum).Sum / 1GB) | Out-File "$cap\01-unpacked-size.txt"
```

3. Reference renders on llama.cpp b10537, launched with the roster entry's validated flags (`src/wave_local_ai_v2/server.py` `build_flags`), then stopped before Ollama starts:

```powershell
Start-Process $llama -NoNewWindow -RedirectStandardError "$cap\20-llamacpp-serve.log" -RedirectStandardOutput "$cap\20-llamacpp-serve.out" -ArgumentList `
  '-m',$gguf,'-ngl','99','-c','32768','-fa','on','-t','8','--jinja','-np','1','--load-mode','auto',
  '--temp','0.6','--top-p','0.95','--top-k','20','--min-p','0','--presence-penalty','1.5','--host','127.0.0.1','--port','8080'
do { Start-Sleep 2 } until ((curl.exe -s -o NUL -w '%{http_code}' "$l/health") -eq '200')
foreach ($id in 'billing-01','billing-fr-01') { foreach ($t in $false,$true) {
  Invoke-Capture $l '/apply-template' @{ messages = @(@{ role = 'user'; content = $item[$id].prompt }); chat_template_kwargs = @{ enable_thinking = $t } } "21-llamacpp-render-$id-think-$("$t".ToLower())"
}}
Invoke-Capture $l '/tokenize' @{ content = $overText; add_special = $true } '22-llamacpp-tokenize-over-long'
"over-long prompt tokens: " + (Get-Content -Raw "$cap\22-llamacpp-tokenize-over-long.json" | ConvertFrom-Json).tokens.Count | Out-File "$cap\22-over-long-token-count.txt"   # must exceed 32768
Stop-Engine
```

4. Start Ollama on its own port and store, import the roster file, capture identity:

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11500'; $env:OLLAMA_MODELS = "$d-models"; $env:OLLAMA_DEBUG = '1'
$env:OLLAMA_FLASH_ATTENTION = '1'; $env:OLLAMA_DEBUG_LOG_REQUESTS = '1'
Start-Process "$d\ollama.exe" -ArgumentList 'serve' -NoNewWindow -RedirectStandardError "$cap\30-serve-roster.log" -RedirectStandardOutput "$cap\30-serve-roster.out"
do { Start-Sleep 1 } until ((curl.exe -s "$h/") -eq 'Ollama is running')
Get-Capture "$h/api/version" '31-version.json'
Get-Capture "$h/" '31-root.txt'
[IO.File]::WriteAllText("$d-Modelfile", "FROM $gguf`n", $utf8)
& "$d\ollama.exe" create wla-qwen3-0.6b-q8 -f "$d-Modelfile" *>&1 | Out-File -Encoding utf8 "$cap\32-create.txt"
$man = Get-ChildItem -Recurse -File "$d-models\manifests" | Where-Object { $_.FullName -like '*\wla-qwen3-0.6b-q8\latest' }
Copy-Item $man.FullName "$cap\32-manifest.json"
Select-String -Path "$cap\32-manifest.json" -SimpleMatch 'sha256:9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031' -Quiet | Out-File "$cap\32-digest-match.txt"   # must hold True
Invoke-Capture $h '/api/show' @{ model = 'wla-qwen3-0.6b-q8'; verbose = $true } '33-show'   # expect empty template, renderer, parser
Get-Capture "$h/api/ps" '34-ps-before.json'                                                  # expect no model loaded
```

5. Runtime protocol: one warm-up, then five counted repetitions each after the 10 s default cooldown (`RUNTIME_COOLDOWN_S`), `/api/ps` after each:

```powershell
$rt = New-ChatBody $item['billing-01'].prompt $runtime
Invoke-Capture $h '/api/chat' $rt '40-warmup'; Get-Capture "$h/api/ps" '40-ps-after-warmup.json'
foreach ($r in 1..5) { Start-Sleep 10; Invoke-Capture $h '/api/chat' $rt "41-rep-$r"; Get-Capture "$h/api/ps" "41-ps-after-rep-$r.json" }
```

6. Second client: a long generation (`think: true`, 1024 tokens, same runner options) started from a separate process, `/api/ps` while it runs, then one extra repetition labelled `contended` (outside the five counted):

```powershell
$sc = $quality.Clone(); $sc['num_predict'] = 1024
[IO.File]::WriteAllText("$cap\42-second-client.body.json", ((New-ChatBody $item['billing-01'].prompt $sc $true) | ConvertTo-Json -Depth 10 -Compress), $utf8)
$p2 = Start-Process curl.exe -PassThru -NoNewWindow -ArgumentList '-s','--data-binary',"@$cap\42-second-client.body.json",'-o',"$cap\42-second-client.json","$h/api/chat"
Start-Sleep -Milliseconds 500
Get-Capture "$h/api/ps" '42-ps-during-second-client.json'
Invoke-Capture $h '/api/chat' $rt '42-rep-contended'
$p2.WaitForExit()
```

7. Rendered-prompt paths (spike `does-ollama-expose-the-prompt-it-finally-rendered.md`): `_debug_render_only` on `/api/chat` for both items and both `think` values, on `/api/generate` (templated), and the raw pre-templated mode fed llama.cpp's own render:

```powershell
foreach ($id in 'billing-01','billing-fr-01') { foreach ($t in $false,$true) {
  $b = New-ChatBody $item[$id].prompt $quality $t; $b['_debug_render_only'] = $true
  Invoke-Capture $h '/api/chat' $b "50-ollama-render-$id-think-$("$t".ToLower())"
}}
$g = [ordered]@{ model = 'wla-qwen3-0.6b-q8'; prompt = $item['billing-01'].prompt; stream = $false; think = $false; keep_alive = -1
                 shift = $false; truncate = $false; _debug_render_only = $true; options = $runner + $quality }
Invoke-Capture $h '/api/generate' $g '51-ollama-generate-render-billing-01-think-false'
$pre = (Get-Content -Raw -Encoding UTF8 "$cap\21-llamacpp-render-billing-01-think-false.json" | ConvertFrom-Json).prompt
$g2 = [ordered]@{ model = 'wla-qwen3-0.6b-q8'; prompt = $pre; raw = $true; stream = $false; keep_alive = -1
                  shift = $false; truncate = $false; options = $runner + $quality }
Invoke-Capture $h '/api/generate' $g2 '52-ollama-raw-billing-01'
```

8. Constrained decoding (spike `which-constrained-decoding-mechanism-does-ollama-expose.md`): the GBNF-field attempt, then ten constrained and ten unconstrained generations, then one constrained with `think: true` (2048 tokens so the thinking block can close):

```powershell
$gb = New-ChatBody $item['billing-01'].prompt $quality
$gb['grammar'] = 'root ::= "account" | "billing" | "other" | "technical"'
Invoke-Capture $h '/api/chat' $gb '60-gbnf-field-attempt'
$ten = 'billing-01','technical-01','account-01','other-01','billing-fr-01','technical-fr-01','other-fr-01','billing-de-01','technical-de-01','account-de-01'
foreach ($id in $ten) {
  $c = New-ChatBody $item[$id].prompt $quality; $c['format'] = @{ type = 'string'; enum = $labels }
  Invoke-Capture $h '/api/chat' $c "61-constrained-$id"
  Invoke-Capture $h '/api/chat' (New-ChatBody $item[$id].prompt $quality) "62-unconstrained-$id"
}
$tk = $quality.Clone(); $tk['num_predict'] = 2048
$ct = New-ChatBody $item['billing-01'].prompt $tk $true; $ct['format'] = @{ type = 'string'; enum = $labels }
Invoke-Capture $h '/api/chat' $ct '63-constrained-think-true-billing-01'
```

9. Over-long prompt, last on this server because it may stop the runner:

```powershell
Invoke-Capture $h '/api/chat' (New-ChatBody $overText $quality) '70-over-long-prompt'
Get-Capture "$h/api/ps" '70-ps-after-over-long.json'
```

10. Server logs: the bundled `llama-server` argument line, and whether either log holds a rendered prompt (`<|im_start|>` is the Qwen3 template's turn marker):

```powershell
Select-String -Path "$cap\30-serve-roster.log" -Pattern '--model' -SimpleMatch | Select-Object -First 3 | Out-File -Encoding utf8 "$cap\80-runner-args.txt"
Select-String -Path "$cap\30-serve-roster.log" -Pattern '<|im_start|>' -SimpleMatch | Select-Object -First 3 | Out-File -Encoding utf8 "$cap\80-log-rendered-prompt.txt"
$rl = Get-ChildItem $env:TEMP -Directory -Filter 'ollama-request-logs-*' | Sort-Object LastWriteTime | Select-Object -Last 1
$rl.FullName | Out-File -Encoding utf8 "$cap\80-request-logs.txt"
Select-String -Path "$($rl.FullName)\*_body.json" -Pattern '<|im_start|>' -SimpleMatch -List | Out-File -Append -Encoding utf8 "$cap\80-request-logs.txt"
Invoke-Capture $h '/api/chat' @{ model = 'wla-qwen3-0.6b-q8'; messages = @(); keep_alive = 0 } '81-unload'
Stop-Engine
```

11. Defaults side-run in a fresh store, without the run's own environment settings except the port and debug log:

```powershell
Remove-Item Env:OLLAMA_FLASH_ATTENTION, Env:OLLAMA_DEBUG_LOG_REQUESTS
$env:OLLAMA_MODELS = "$d-models-defaults"
Start-Process "$d\ollama.exe" -ArgumentList 'serve' -NoNewWindow -RedirectStandardError "$cap\90-serve-defaults.log" -RedirectStandardOutput "$cap\90-serve-defaults.out"
do { Start-Sleep 1 } until ((curl.exe -s "$h/") -eq 'Ollama is running')
& "$d\ollama.exe" pull qwen3:0.6b *>&1 | Out-File -Encoding utf8 "$cap\91-pull.txt"
Invoke-Capture $h '/api/show' @{ model = 'qwen3:0.6b' } '92-defaults-show'                  # details.quantization_level
Invoke-Capture $h '/api/chat' ([ordered]@{ model = 'qwen3:0.6b'; stream = $false; think = $false
  messages = @(@{ role = 'user'; content = $item['billing-01'].prompt }) }) '93-defaults-chat'   # no options, no keep_alive
Get-Capture "$h/api/ps" '94-defaults-ps.json'                                                  # context_length
Select-String -Path "$cap\90-serve-defaults.log" -Pattern '--model' -SimpleMatch | Select-Object -First 3 | Out-File -Encoding utf8 "$cap\95-defaults-runner-args.txt"
curl.exe -sL https://ollama.com/library/qwen3.6/tags -o "$cap\96-library-qwen3.6-tags.html"   # MoE flagship tags, same day (input to Q21)
Stop-Engine
```

12. Offline checks: render byte diff and think on/off, raw versus templated, format check, timings:

```powershell
function Get-Render([string]$name) {
  $j = Get-Content -Raw -Encoding UTF8 "$cap\$name.json" | ConvertFrom-Json
  if ($name -like '50-*') { $j._debug_info.rendered_template } else { $j.prompt }
}
$diff = foreach ($id in 'billing-01','billing-fr-01') {
  foreach ($t in 'false','true') {
    $ob = $utf8.GetBytes((Get-Render "50-ollama-render-$id-think-$t")); $rb = $utf8.GetBytes((Get-Render "21-llamacpp-render-$id-think-$t"))
    $n = [Math]::Min($ob.Length, $rb.Length); $i = 0; while ($i -lt $n -and $ob[$i] -eq $rb[$i]) { $i++ }
    $first = if ($ob.Length -eq $rb.Length -and $i -eq $n) { 'identical' } else { "byte $i" }
    "$id think=$t ollama_bytes=$($ob.Length) llamacpp_bytes=$($rb.Length) first_difference=$first"
  }
  "$id think on/off renders differ: ollama=$((Get-Render "50-ollama-render-$id-think-false") -cne (Get-Render "50-ollama-render-$id-think-true")) llamacpp=$((Get-Render "21-llamacpp-render-$id-think-false") -cne (Get-Render "21-llamacpp-render-$id-think-true"))"
}
$raw = Get-Content -Raw -Encoding UTF8 "$cap\52-ollama-raw-billing-01.json" | ConvertFrom-Json
$chat = Get-Content -Raw -Encoding UTF8 "$cap\62-unconstrained-billing-01.json" | ConvertFrom-Json
$diff += "raw vs templated billing-01: prompt_eval_count raw=$($raw.prompt_eval_count) chat=$($chat.prompt_eval_count); output raw=[$($raw.response)] chat=[$($chat.message.content)]"
$diff | Out-File -Encoding utf8 "$cap\A0-render-diff.txt"

$quoted = '^\s*"(' + ($labels -join '|') + ')"\s*$'; $bare = '^\s*(' + ($labels -join '|') + ')\s*$'
Get-ChildItem "$cap\6*.json" | Where-Object { $_.Name -notlike '*.body.json' } | ForEach-Object {
  $c = (Get-Content -Raw -Encoding UTF8 $_.FullName | ConvertFrom-Json).message.content
  [pscustomobject]@{ file = $_.Name; content = $c; json_string_in_label_set = ($c -match $quoted); bare_label = ($c -match $bare) }
} | Export-Csv -NoTypeInformation -Encoding UTF8 "$cap\A1-format-check.csv"

Get-ChildItem "$cap\4*.json" | Where-Object { $_.Name -notlike '*.body.json' -and $_.Name -notlike '*-ps-*' } | ForEach-Object {
  $j = Get-Content -Raw -Encoding UTF8 $_.FullName | ConvertFrom-Json
  [pscustomobject]@{ file = $_.Name; load_ms = $j.load_duration / 1e6; prompt_eval_count = $j.prompt_eval_count
    prompt_eval_ms = $j.prompt_eval_duration / 1e6; eval_count = $j.eval_count; eval_ms = $j.eval_duration / 1e6
    total_ms = $j.total_duration / 1e6; gen_tok_per_s = $j.eval_count / ($j.eval_duration / 1e9) }
} | Export-Csv -NoTypeInformation -Encoding UTF8 "$cap\A2-runtime-timings.csv"
```

13. Cleanup. Keep the capture folder. Orders 6 to 8 reuse the pinned build `$d` and the roster store `$d-models`; remove them too (last line) when that work is not next:

```powershell
Stop-Engine
Remove-Item Env:OLLAMA_HOST, Env:OLLAMA_MODELS, Env:OLLAMA_DEBUG -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$d-models-defaults"; Remove-Item -Force "$d.zip", "$d-Modelfile"
Get-ChildItem $env:TEMP -Directory -Filter 'ollama-request-logs-*' | Remove-Item -Recurse -Force
# Remove-Item -Recurse -Force $d, "$d-models"
```

### Capture map

Spike column: `runtime` = `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`, `render` = `does-ollama-expose-the-prompt-it-finally-rendered.md`, `constrained` = `which-constrained-decoding-mechanism-does-ollama-expose.md`.

| Spike | Bounds capture | Files in `D:\ia\ollama-v0.35.1-captures` |
| ----- | -------------- | ----- |
| runtime | model created from the roster file, checksum the engine reads | `00-gguf-sha256.txt`, `32-create.txt`, `32-manifest.json`, `32-digest-match.txt` |
| runtime | version endpoint | `31-version.json`, `31-root.txt` |
| runtime | loaded models before, during, after | `34-ps-before.json`, `42-ps-during-second-client.json`, `40-ps-after-warmup.json`, `41-ps-after-rep-1..5.json` |
| runtime | second client visible from the harness side | `42-second-client.json`, `42-rep-contended.json`, `42-ps-during-second-client.json` |
| runtime | warm-up plus five counted, 10 s cooldown, load duration per repetition | `40-warmup.json`, `41-rep-1..5.json`, `A2-runtime-timings.csv` |
| runtime | configured and reported context, over-long prompt result | `41-rep-1.body.json` (`num_ctx`), `context_length` in `4*-ps-*.json`, `22-over-long-token-count.txt`, `70-over-long-prompt.json`, `http-status.txt` |
| runtime | configuration defaults, engine-reported or not | `33-show.json` (`parameters`, `model_info`), `80-runner-args.txt` |
| runtime | thinking control forwarded, spelled, or absent | `50-ollama-render-*-think-*.json`, the think line of `A0-render-diff.txt` |
| runtime | default install's quant and context; MoE flagship tag | `91-pull.txt`, `92-defaults-show.json`, `93-defaults-chat.json`, `94-defaults-ps.json`, `95-defaults-runner-args.txt`, `96-library-qwen3.6-tags.html` |
| render | every candidate path and its string | `50-*.json` (chat render), `51-*.json` (generate render), `33-show.json` (template, renderer, parser), `52-ollama-raw-billing-01.json` (raw), `80-log-rendered-prompt.txt`, `80-request-logs.txt` (debug logs and where they live) |
| render | llama.cpp `/apply-template` on the same GGUF and items | `21-llamacpp-render-*.json`, `00-llama-server-version.txt` |
| render | byte diff, thinking switch reflected | `A0-render-diff.txt` |
| constrained | GBNF accepted, ignored or rejected | `60-gbnf-field-attempt.json`, its line in `http-status.txt` |
| constrained | schema constraint accepted, how expressed | `61-constrained-*.body.json`, `61-constrained-*.json` |
| constrained | ten constrained and ten unconstrained, any output outside the format | `61-*.json`, `62-*.json`, `A1-format-check.csv` |
| constrained | format after the thinking block | `63-constrained-think-true-billing-01.json` |

Assumptions the run checks rather than relies on: the `--model` and `<|im_start|>` log searches assume the debug log prints the runner's argument list and that a rendered prompt, if logged, carries the template's turn marker (an empty file is itself the finding); `' billing' * 50000` is assumed to exceed 32768 tokens, which `22-over-long-token-count.txt` confirms; the second client's 1024-token generation is assumed to outlast the 500 ms wait, which `42-ps-during-second-client.json` and the two responses' `total_duration` show.
