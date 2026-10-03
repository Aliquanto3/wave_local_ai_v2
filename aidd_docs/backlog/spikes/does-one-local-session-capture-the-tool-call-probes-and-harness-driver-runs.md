---
type: spike
status: open
source: aidd_docs/backlog/spikes/does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it.md
parents:
  - aidd_docs/backlog/stories/a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md
  - aidd_docs/backlog/stories/the-same-tool-calling-items-run-under-each-compared-harness.md
  - aidd_docs/backlog/stories/an-agentic-plan-is-scored-against-its-authored-step-set.md
related_to:
  - aidd_docs/backlog/stories/a-rag-answer-is-scored-over-a-local-corpus-under-a-named-harness.md
---

# Spike: Does one local session capture the tool-call probes and harness driver runs?

## Question

Can one sitting on the reference laptop, with the pinned `llama-server` b10537 and the four roster GGUFs already on disk, produce every capture the blocked spike `does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it.md` names in its Bounds, using only the commands and scripts below?

## Decision

Whether the blocked spike can be concluded from this session's captures. Its own Decision then follows: whether agentic tool calling and agentic planning are built as suites or marked `out-of-scope-this-release`; per roster model, whether its rows are evidence of the model or of its template; and which candidate frameworks are comparable. This spike only collects the evidence. It decides none of those.

## Bounds

- Evidence needed: the files listed under "Capture checklist", written by the procedure below into `aidd_docs/tasks/<yyyy_mm>/<yyyy_mm_dd>_tool-call-probes/` of the main checkout.
- Stop when: every file in the capture checklist exists. Two things stop the session early, and each one still writes its file. (1) `llama-server --version` does not report build 10537: stop before step 3. (2) The `harness-probe` group does not resolve: that framework's verdict is "cannot be installed under the lockfile", recorded in `harness-probe-resolution.txt`, and its driver runs are skipped.
- Tags: `install + local run`.
- Closes: the blocked spike above (its Follow-up runs 1-4, all of whose live captures this produces). Through it, it unblocks the stories it blocks: orders 6 (`a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md`, runs 1-3), 7 (`the-same-tool-calling-items-run-under-each-compared-harness.md`, run 4) and 8 (`an-agentic-plan-is-scored-against-its-authored-step-set.md`, runs 1-4). Order 5 (`a-rag-answer-is-scored-over-a-local-corpus-under-a-named-harness.md`) is not blocked by that spike; its Blocked line names only the judge stories. Its `llamaindex` adapter keeps LlamaIndex's streaming and `parallel_tool_calls: true` defaults (owner answer Q109 (a)), and this session's `llamaindex` `default` runs on the MoE are the first evidence of whether those defaults meet llama.cpp #24807 or #22684.
- Prerequisites:
  - GPU free. `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv` lists no process. No other `llama-server` is running, and ports 8080 and 8081 are free (`Get-NetTCPConnection -LocalPort 8080,8081 -State Listen -ErrorAction SilentlyContinue` returns nothing).
  - Weights: no new download. The four roster files already sit under `SLM_MODELS_DIR`: 639 446 688 + 1 834 426 016 + 2 497 280 256 + 17 730 509 792 bytes = 22.7 GB (`aidd_docs/roster/models.json` `bytes_on_disk`). The only Hub reads are two chat templates, about 20 KB together (step 2).
  - `.env` in the main checkout sets `SLM_MODELS_DIR` and `LLAMA_SERVER_PATH` (b10537).
  - Network for PyPI, for the `harness-probe` dependency group installed in the throwaway worktree (step 1). Its size on disk was not measured from the desk. Assumption: a few GB free on the worktree drive covers the worktree `.venv` (default groups plus `harness-probe`) and the uv cache.
  - Captures: proxy and verdict files are small. `server.log` at `-lv 5` grows with every token. Size not measured.
- Time: about 2.5 h; up to 4 h if many probes need attribution relaunches. This is an estimate, not a measurement. Setup takes about 30 min (worktree, `uv add`, saving the scripts). The three dense entries take about 10 min each. The MoE takes about 45 min: roughly 55 chat calls at its measured ~272 prompt tok/s and ~25 gen tok/s (`aidd_docs/results/runtime-reference.jsonl`), at most about 20 s per call at `max_tokens` 512. Its load time is not recorded in the repo. Reading verdicts and cleanup take about 20 min.
- Cost: local only (laptop electricity). No provider is called and no API key is used. Network reads: PyPI packages and about 20 KB from huggingface.co.

### Method notes the session depends on

- **Attribution (a) uses `--skip-chat-parsing`, not `parse_tool_calls: false`.** At b10537, `tools/server/server-common.cpp` lines 1288-1293 set `llama_params["parse_tool_calls"] = true` whenever `tools` is non-empty and `tool_choice` is not `none`. The request-body copy at lines 1383-1388 only fills keys that are still absent, so a client's `"parse_tool_calls": false` is dropped. `common/chat.h` line 294 declares the field, and no b10537 `common/chat*` or `peg*` source reads it. The server flag `--skip-chat-parsing` (`common/arg.cpp` lines 3714-3724) goes through `common/chat.cpp` lines 3690-3704. That path renders the same template with the request's tools, sets no tool grammar, and returns everything as `content`. The log line is "Forcing pure content template". Attribution (a) is therefore a relaunch with that flag, followed by resending the identical captured body (`resend.py`). One difference from the normal path: no lazy grammar constrains the output after the trigger. Under greedy decoding, the raw output shows what the model emits unconstrained.
- **`--jinja` must precede `--chat-template-file`.** README line 234: "only commonly used templates are accepted (unless --jinja is set before this flag)". `launch.py` appends extra flags after the `build_flags` list, which already holds `--jinja`.
- **Known-good control templates are pinned.** Qwen's HF originals, read 2026-10-03:
  - `Qwen/Qwen3-0.6B` at `c1899de289a04d12100db370d81485cdf75e47ca`, `Qwen/Qwen3-1.7B` at `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` and `Qwen/Qwen3-4B` at `1cfa9a7208912126459214e8b04321603b3df60c` carry one byte-identical `tokenizer_config.json` `chat_template` (4168 chars, sha256 `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`). One file serves the three dense entries.
  - `Qwen/Qwen3.6-35B-A3B` at `995ad96eacd98c81ed38be0c5b274b04031597b0`: `chat_template.jinja` (7764 bytes, sha256 `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`, no BOM), equal to that revision's `tokenizer_config.json` `chat_template`.
  - `fetch_templates.py` refuses if either hash moves.
- **Streamed prompt counts.** b10537 sends `usage` in a stream only when `stream_options.include_usage` is set (`server-task.cpp` lines 504-516, `server-schema.cpp` lines 26-29). The last chunk carries `timings` (line 518). README lines 1388-1414: prompt tokens = `prompt_n + cache_n`. `replay.py` uses `usage.prompt_tokens` when present, else that sum, and names which one it used.
- **Second count.** `POST /v1/chat/completions/input_tokens` takes a chat-completion body and returns `input_tokens` (README lines 1546-1557). `replay.py` records it beside the `/apply-template` + `/tokenize` count. The latter stays the decisive one: it is the method `local_client.py` verified live on b10537 (2026-10-02), tools included.
- **Variants per framework.** `default` keeps the framework's request defaults (owner answer Q109 (a)). `aligned` is the attribution control from the blocked spike's run 4: smolagents `tool_choice: "auto"` instead of its default `"required"`; LlamaIndex `streaming=False` and `allow_parallel_tool_calls=False` instead of its defaults `True` / `True`. LangGraph (`bind_tools` sends neither `tool_choice` nor `parallel_tool_calls` by default, `langchain-openai` 1.6.7 `base.py` lines 2532-2560) and pydantic-ai (`output_type=str` sends `tool_choice: "auto"`, `models/_tool_choice.py` line 31) run `default` only.
- **Tool schemas a framework re-serialises are recorded, not normalised.** LangGraph receives `direct`'s dicts unchanged (`langchain-core` 1.4.7 `utils/function_calling.py` lines 562-564). smolagents, pydantic-ai and LlamaIndex build schemas from the Python functions. LlamaIndex adds `strict: false` and `additionalProperties: false` when `is_function_calling_model=True`. The Q33 reading (wrap or rewrite) is made from the proxy capture.
- **P1 closes its sequence.** `probes.py` answers P1's call with the canned tool result and records the final text turn, so P1 is also `direct`'s reference sequence for the harness comparison. The P1 verdict defined by the blocked spike is `turns[0]` of its `verdicts.jsonl` line. P4's verdict is all its turns.

### Capture checklist

`$Cap` = `aidd_docs/tasks/<yyyy_mm>/<yyyy_mm_dd>_tool-call-probes/` in the main checkout. `<E>` ranges over the four roster ids. `<H>` ranges over the six harness configurations `smolagents__*__default`, `smolagents__*__aligned`, `langgraph__*__default`, `pydantic-ai__*__default`, `llamaindex__*__default` and `llamaindex__*__aligned`, with `*` = `P1`, `P4`.

| Blocked spike's Bounds item | File |
| --- | --- |
| pinned build | `versions.txt` (`llama-server --version`), `<E>/base/props.json` `build_info` |
| template in force per entry | `<E>/base/props.json` (`chat_template`, its sha256, `chat_template_caps`) |
| parser path per entry | `<E>/base/parser-path.txt` ("Using specialized template: Qwen3-Coder", "using differential autoparser" or "Unable to generate parser") |
| raw response per probe | `proxy/<E>__direct__{P1,P2,P3,P4,P1R}__base.jsonl`, plus `P5` for `qwen3.6-35b-a3b-ud-iq4xs` |
| `tool_calls` populated, per probe | `<E>/base/verdicts.jsonl` |
| #27767 at b10537 (run 3 (c)) | the `P1R` lines of `<E>/base/verdicts.jsonl` |
| failure attribution, per failing probe | `<E>/skipparse/attribution.jsonl` (run 3 (a)) and `<E>/hftemplate/verdicts.jsonl` + `props.json` (run 3 (b)) |
| framework installs under the lockfile | `harness-probe-resolution.txt`, `harness-probe-pyproject.diff` |
| framework version, endpoint driven, own call record | `harness/<E>__<H>.txt` for `<E>` in {`qwen3-0.6b-q8`, `qwen3.6-35b-a3b-ud-iq4xs`} |
| call sequence in one shape | `proxy/<E>__<H>.jsonl` for the same two entries |
| prompt readable, overhead | `replay/<E>.jsonl` for the same two entries (`replay_matches_engine`, `q33_overhead_first_call`, `sent`) |

A probe with no FAIL needs no attribution files. When the stop condition is met, the blocked spike is concluded from these files with `aidd-pm:05-spike` `conclude`, which is not part of this spike.

### Procedure

All commands are Windows PowerShell 5.1 and run from the throwaway worktree. Open three PowerShell windows: A (server), B (proxy), C (everything else). Paste the session header into each, on the same calendar day so `$Day` agrees. If the sitting crosses midnight, set `$Day` by hand to the first day's value in any window opened later.

**Session header (A, B, C):**

```powershell
$Repo = "C:\Users\Anael\dev\wave_local_ai_v2"   # main checkout that holds .env; adjust if elsewhere
$W    = "$Repo-spike-tool-calls"                # throwaway worktree, never pushed
$Day  = Get-Date -Format "yyyy_MM_dd"
$Cap  = "$Repo\aidd_docs\tasks\$(Get-Date -Format 'yyyy_MM')\${Day}_tool-call-probes"
Get-Content "$Repo\.env" | ForEach-Object {
  if ($_ -match '^\s*(SLM_MODELS_DIR|LLAMA_SERVER_PATH)\s*=\s*(.+?)\s*$') { Set-Item "env:$($Matches[1])" $Matches[2] }
}
function Py { uv run --group harness-probe python @args }   # one environment for every script
if (Test-Path $W) { Set-Location $W }
```

**Step 0, window C: preconditions.**

```powershell
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
Get-NetTCPConnection -LocalPort 8080,8081 -State Listen -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Cap | Out-Null
& $env:LLAMA_SERVER_PATH --version 2>&1 | Out-File -Encoding utf8 "$Cap\versions.txt"
Get-Content "$Cap\versions.txt"   # must name build 10537 (bf0040e); otherwise stop here
```

**Step 1, window C: throwaway branch and the `harness-probe` group.**

```powershell
git -C $Repo worktree add -b spike/tool-call-probes $W main
Set-Location $W
New-Item -ItemType Directory -Force "$W\spike" | Out-Null
```

Save the eight scripts under "Scripts" below as `$W\spike\<name>` (UTF-8). Then, in `$W`, run the blocked spike's Follow-up run 4 `uv add --group harness-probe ...` command verbatim, with ` 2>&1 | Out-File -Encoding utf8 "$Cap\harness-probe-resolution.txt"` appended. In Windows PowerShell 5.1, `2>&1` wraps uv's stderr progress lines as error records. The text still lands in the file. Then:

```powershell
git -C $W diff -- pyproject.toml | Out-File -Encoding utf8 "$Cap\harness-probe-pyproject.diff"
Get-Content "$Cap\harness-probe-resolution.txt" -Tail 5
```

If resolution fails, find the framework that cannot resolve by adding the pins one framework at a time. Append each attempt to the same file:

```powershell
foreach ($set in @(@('smolagents[openai]==1.26.0'), @('langgraph==1.2.12','langchain-openai==1.6.7'), @('pydantic-ai-slim[openai]==2.53.0'), @('llama-index-core==0.14.25','llama-index-llms-openai-like==0.8.1'))) {
  "### uv add --group harness-probe $set" | Out-File -Append -Encoding utf8 "$Cap\harness-probe-resolution.txt"
  uv add --group harness-probe @set 2>&1 | Out-File -Append -Encoding utf8 "$Cap\harness-probe-resolution.txt"
}
```

A framework whose set fails is recorded as "cannot be installed under the lockfile", and its `drive.py` runs are skipped.

**Step 2, window C: control templates.**

```powershell
Py spike\fetch_templates.py $Cap
```

**Step 3, window B: logging proxy, left running for the whole session.**

```powershell
Py spike\proxy.py $Cap
```

**Step 4: per roster entry, in this order: `qwen3-0.6b-q8`, `qwen3-1.7b-q8`, `qwen3-4b-q4km`, `qwen3.6-35b-a3b-ud-iq4xs`.** Set `$E` in windows A and C first, for example `$E = "qwen3-0.6b-q8"`.

4a, window A: launch. These are the blocked spike's run-1 flags, built by `server.build_flags`, plus `-lv 5 --log-file`. The exact command line is written to `$Cap\$E\base\command.txt`.

```powershell
Py spike\launch.py $Cap $E base
```

4b, window C: direct probes and the parser path. `probes.py` waits for `/health`. The MoE adds `P5`.

```powershell
$Probes = if ($E -like "qwen3.6-*") { "P1,P2,P3,P4,P5,P1R" } else { "P1,P2,P3,P4,P1R" }
Py spike\probes.py $Cap $E base $Probes
Select-String -Path "$Cap\$E\base\server.log" -Pattern "Using specialized template|using differential autoparser|Unable to generate parser" |
  ForEach-Object { $_.Line } | Out-File -Encoding utf8 "$Cap\$E\base\parser-path.txt"
Get-Content "$Cap\$E\base\parser-path.txt"
```

4c, window C, only for `qwen3-0.6b-q8` and `qwen3.6-35b-a3b-ud-iq4xs`: framework drivers, then the replay. The replay needs the same base server still up.

```powershell
$Runs = @(@('smolagents','default'), @('smolagents','aligned'), @('langgraph','default'),
          @('pydantic-ai','default'), @('llamaindex','default'), @('llamaindex','aligned'))
foreach ($r in $Runs) { foreach ($p in 'P1','P4') { Py spike\drive.py $Cap $r[0] $E $p $r[1] } }
Py spike\replay.py $Cap $E
```

For the two dense entries without driver runs, `replay.py` is optional. Run it if `direct`'s own replay match is wanted for every entry.

4d: attribution, only if 4b printed a FAIL. Read `$Cap\$E\base\verdicts.jsonl` and the failing probe's `proxy\${E}__direct__<probe>__base.jsonl`. The exchange index is the 0-based line of the first failing turn. A streamed `P5` failure is attributed through `P1`.

- Run 3 (a). In window A, Ctrl+C, then `Py spike\launch.py $Cap $E skipparse --skip-chat-parsing`. In window C, for each failing probe, run `Py spike\resend.py $Cap "${E}__direct__<probe>__base" <index> skipparse`. It writes `failing-template` when the raw content holds a well-formed call in the documented format, else `failing-model`. Check that `$Cap\$E\skipparse\server.log` contains "Forcing pure content template".
- Run 3 (b). In window A, Ctrl+C, then `Py spike\launch.py $Cap $E hftemplate --chat-template-file "$Cap\templates\qwen3-dense.hf.jinja"`, or `qwen3.6-moe.hf.jinja` for the MoE. In window C, run `Py spike\probes.py $Cap $E hftemplate <failing probes, comma-separated>`. Check that `$Cap\$E\hftemplate\props.json` `chat_template_sha256` equals the template file's sha256 printed in step 2. If it differs, `/props` did not report the override; record that, and take the `server.log` template lines as the evidence.

4e, window A: Ctrl+C before the next entry.

**Step 5: cleanup.**

```powershell
# Windows A and B: Ctrl+C.
Set-Location $Repo
git -C $Repo worktree remove --force $W
git -C $Repo branch -D spike/tool-call-probes
git -C $Repo worktree list   # $W no longer listed
```

`--force` is needed because the worktree holds untracked `spike\`, `.venv` and a modified `pyproject.toml` / `uv.lock`. The branch was never pushed. The captures stay uncommitted in `$Cap`. Before committing, leave out any `server.log` too large to review: `parser-path.txt` is its committed extract, and the conclude step decides the rest.

### Scripts

Save each block as `$W\spike\<name>`. All but `drive.py` use only the standard library and the project package. `drive.py` imports only the `harness-probe` group. All eight parse. On 2026-10-03, `proxy.py`, `probes.py`, `resend.py` and `replay.py` were smoke-tested against a local stdlib mock of the chat, `/apply-template`, `/tokenize` and `/props` endpoints, streaming included, with no model and no `llama-server`. `launch.py`, `drive.py` and `fetch_templates.py` were only parsed. The two template hashes were computed with `fetch_templates.py`'s method. None of the scripts has run against b10537 or a framework install.

#### `spike/probe_tools.py`

```python
"""The probe tools: OpenAI definitions sent by `direct`, Python callables the frameworks wrap."""

import json

GET_WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}
SET_ALARM = {
    "type": "function",
    "function": {
        "name": "set_alarm",
        "description": "Set a recurring alarm.",
        "parameters": {
            "type": "object",
            "properties": {
                "hour": {"type": "integer", "minimum": 0, "maximum": 23},
                "minute": {"type": "integer"},
                "days": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                    },
                },
                "enabled": {"type": "boolean"},
            },
            "required": ["hour", "minute", "days", "enabled"],
        },
    },
}
FIND_USER_ID = {
    "type": "function",
    "function": {
        "name": "find_user_id",
        "description": "Look up a customer's user id from their full name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The customer's full name."}
            },
            "required": ["name"],
        },
    },
}
GET_ORDERS = {
    "type": "function",
    "function": {
        "name": "get_orders",
        "description": "List the order ids of a customer.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user id returned by find_user_id.",
                }
            },
            "required": ["user_id"],
        },
    },
}

# Canned tool results, identical for every harness, keyed by tool name.
RESULTS = {
    "get_weather": {"city": "Paris", "condition": "sunny", "temperature_c": 18},
    "set_alarm": {"status": "set"},
    "find_user_id": {"user_id": "u-17"},
    "get_orders": {"orders": ["o-301", "o-302"]},
}

PROMPTS = {
    "P1": "What is the weather in Paris right now?",
    "P4": "List the orders of the customer named Ada Lovelace.",
}
TOOLS_FOR = {"P1": [GET_WEATHER], "P4": [FIND_USER_ID, GET_ORDERS]}


def get_weather(city: str) -> str:
    """Current weather for a city.

    Args:
        city (str): The city name.
    """
    return json.dumps(RESULTS["get_weather"])


def find_user_id(name: str) -> str:
    """Look up a customer's user id from their full name.

    Args:
        name (str): The customer's full name.
    """
    return json.dumps(RESULTS["find_user_id"])


def get_orders(user_id: str) -> str:
    """List the order ids of a customer.

    Args:
        user_id (str): The user id returned by find_user_id.
    """
    return json.dumps(RESULTS["get_orders"])


CALLABLES_FOR = {"P1": [get_weather], "P4": [find_user_id, get_orders]}
```

#### `spike/proxy.py`

```python
"""Logging reverse proxy: 127.0.0.1:8081/<label>/<path> -> 127.0.0.1:8080/<path>.

Every exchange is appended as one JSON line to <capture>/proxy/<label>.jsonl.
Usage: python proxy.py <capture-folder>
"""

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = "http://127.0.0.1:8080"
OUT = Path(sys.argv[1]) / "proxy"
LOCK = threading.Lock()


def _json_or_text(raw: bytes):
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text  # SSE stream or non-JSON body, kept verbatim


class Handler(BaseHTTPRequestHandler):
    # HTTP/1.0: the connection closes after each response, so a streamed
    # body is relayed as-is without re-encoding chunked transfer.
    protocol_version = "HTTP/1.0"

    def _relay(self) -> None:
        label, _, rest = self.path.lstrip("/").partition("/")
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        request = urllib.request.Request(
            f"{UPSTREAM}/{rest}",
            data=body or None,
            method=self.command,
            headers={
                "Content-Type": self.headers.get("Content-Type", "application/json")
            },
        )
        started = time.time()
        try:
            upstream = urllib.request.urlopen(request, timeout=900)
        except urllib.error.HTTPError as err:
            upstream = err
        status = getattr(upstream, "status", None) or upstream.code
        self.send_response(status)
        for key, value in upstream.headers.items():
            if key.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(key, value)
        self.end_headers()
        received = []
        for line in iter(upstream.readline, b""):
            received.append(line)
            self.wfile.write(line)
            self.wfile.flush()
        record = {
            "label": label,
            "started": started,
            "elapsed_s": round(time.time() - started, 3),
            "method": self.command,
            "path": "/" + rest,
            "status": status,
            "request": _json_or_text(body),
            "response": _json_or_text(b"".join(received)),
        }
        with LOCK, (OUT / f"{label}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    do_GET = do_POST = _relay

    def log_message(self, fmt, *args):  # one short line per exchange on the console
        sys.stderr.write(f"{self.path} {args[1] if len(args) > 1 else ''}\n")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"proxy :8081 -> {UPSTREAM}, captures in {OUT}")
    ThreadingHTTPServer(("127.0.0.1", 8081), Handler).serve_forever()
```

#### `spike/launch.py`

```python
"""Start llama-server for one roster entry with the flags `server.build_flags` produces, plus -lv 5.

Usage: uv run python launch.py <capture-folder> <entry-id> <variant> [extra llama-server flags...]
Runs in the foreground; Ctrl+C stops it. The server log goes to <capture>/<entry>/<variant>/server.log.
"""

import os
import subprocess
import sys
from pathlib import Path

from wave_local_ai_v2 import roster, server

cap, entry_id, variant, *extra = sys.argv[1:]
entry = roster.resolve_entry(
    roster.load_roster(Path("aidd_docs/roster/models.json")), entry_id
)
model = Path(os.environ["SLM_MODELS_DIR"]) / entry.file
# host_n_cpu_moe=None -> the entry's own validated value (37 on the MoE, none on a dense entry).
flags = server.build_flags(entry, None, entry.validated_host["threads"], model)
log_dir = Path(cap) / entry_id / variant
log_dir.mkdir(parents=True, exist_ok=True)
command = [
    os.environ["LLAMA_SERVER_PATH"],
    *flags,
    "-lv",
    "5",
    "--log-file",
    str(log_dir / "server.log"),
    *extra,
]
(log_dir / "command.txt").write_text(
    subprocess.list2cmdline(command) + "\n", encoding="utf-8"
)
print(subprocess.list2cmdline(command))
subprocess.run(command, check=False)
```

#### `spike/probes.py`

```python
"""Direct probes P1-P5 and P1R (P1 with tool_choice "required") through the logging proxy.

Usage: python probes.py <capture-folder> <entry-id> <variant> [P1,P2,P3,P4,P5,P1R]
Writes <capture>/<entry>/<variant>/props.json and verdicts.jsonl; the proxy writes the exchanges.
"""

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from probe_tools import (
    FIND_USER_ID,
    GET_ORDERS,
    GET_WEATHER,
    PROMPTS,
    RESULTS,
    SET_ALARM,
)

ENGINE, PROXY = "http://127.0.0.1:8080", "http://127.0.0.1:8081"
# Follow-up defaults of the blocked spike: auto, no parallel calls, no stream, quality_cli overrides.
COMMON = {
    "tool_choice": "auto",
    "parallel_tool_calls": False,
    "stream": False,
    "chat_template_kwargs": {"enable_thinking": False},
    "temperature": 0,
    "top_k": 0,
    "top_p": 1.0,
    "seed": 42,
    "max_tokens": 512,
}
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]


def wait_ready() -> dict:
    for _ in range(180):
        try:
            with urllib.request.urlopen(f"{ENGINE}/health", timeout=5):
                break
        except (urllib.error.URLError, ConnectionError):
            time.sleep(5)
    else:
        sys.exit("llama-server not ready after 15 minutes")
    with urllib.request.urlopen(f"{ENGINE}/props", timeout=30) as r:
        return json.load(r)


def post(label: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{PROXY}/{label}/v1/chat/completions",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        raw = r.read().decode()
    return json.loads(raw) if not body.get("stream") else merge_stream(raw)


def merge_stream(raw: str) -> dict:
    """Fold SSE chunks into one message; flag anything that arrived as reasoning."""
    calls, content, reasoning, finish = {}, "", "", None
    for line in raw.splitlines():
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        for choice in json.loads(line[6:]).get("choices", []):
            delta = choice.get("delta", {})
            content += delta.get("content") or ""
            reasoning += delta.get("reasoning_content") or ""
            for tc in delta.get("tool_calls") or []:
                slot = calls.setdefault(
                    tc.get("index", 0),
                    {
                        "id": None,
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )
                slot["id"] = tc.get("id") or slot["id"]
                fn = tc.get("function") or {}
                slot["function"]["name"] += fn.get("name") or ""
                slot["function"]["arguments"] += fn.get("arguments") or ""
            finish = choice.get("finish_reason") or finish
    message = {
        "role": "assistant",
        "content": content,
        "reasoning_content": reasoning,
        "tool_calls": [calls[i] for i in sorted(calls)] or None,
    }
    return {"choices": [{"message": message, "finish_reason": finish}]}


def call_checks(choice: dict, name: str, expected_args) -> dict:
    msg = choice["message"]
    calls = msg.get("tool_calls") or []
    args_raw = calls[0]["function"]["arguments"] if calls else None
    try:
        args = json.loads(args_raw) if isinstance(args_raw, str) else None
    except ValueError:
        args = None
    return {
        "finish_reason_tool_calls": choice.get("finish_reason") == "tool_calls",
        "one_call": len(calls) == 1,
        "name": bool(calls) and calls[0]["function"]["name"] == name,
        "arguments_is_json_string": isinstance(args_raw, str),
        "arguments": isinstance(args, dict) and expected_args(args),
        "content_empty": not (msg.get("content") or "").strip(),
        "no_reasoning_content": not (msg.get("reasoning_content") or "").strip(),
    }


def follow(label: str, body: dict, steps: list) -> list:
    """Run a call sequence: each step is (tool name, argument check); a final text turn closes it."""
    results, messages = [], list(body["messages"])
    for name, check in steps + [(None, None)]:
        choice = post(label, {**body, "messages": messages})["choices"][0]
        if name is None:
            results.append(
                {
                    "final_text": choice["message"].get("content"),
                    "finish_reason_stop": choice.get("finish_reason") == "stop",
                    "no_call": not choice["message"].get("tool_calls"),
                }
            )
            break
        checks = call_checks(choice, name, check)
        results.append(checks)
        if not (checks["one_call"] and checks["name"]):
            break  # the sequence diverged; later turns would not be comparable
        msg = choice["message"]
        call = msg["tool_calls"][0]
        messages += [
            {"role": "assistant", "content": msg.get("content"), "tool_calls": [call]},
            {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(RESULTS[name]),
            },
        ]
    return results


def run(entry: str, variant: str, probe: str) -> dict:
    label = f"{entry}__direct__{probe}__{variant}"
    user = lambda text: [{"role": "user", "content": text}]  # noqa: E731
    paris = lambda a: a == {"city": "Paris"}  # noqa: E731
    if probe in ("P1", "P1R", "P5"):
        body = {**COMMON, "messages": user(PROMPTS["P1"]), "tools": [GET_WEATHER]}
        if probe == "P1R":
            body["tool_choice"] = "required"
        if probe == "P5":
            body["stream"] = True
        return {"turns": follow(label, body, [("get_weather", paris)])}
    if probe == "P2":
        body = {
            **COMMON,
            "messages": user("Set an alarm for 7:30 on weekdays, enabled."),
            "tools": [SET_ALARM],
        }
        alarm = lambda a: (
            type(a.get("hour")) is int
            and a["hour"] == 7  # noqa: E731
            and type(a.get("minute")) is int
            and a["minute"] == 30
            and sorted(a.get("days", [])) == sorted(WEEKDAYS)
            and a.get("enabled") is True
        )
        return {
            "turns": [call_checks(post(label, body)["choices"][0], "set_alarm", alarm)]
        }
    if probe == "P3":
        body = {
            **COMMON,
            "messages": user("What is 2 + 3? Answer with the number only."),
            "tools": [GET_WEATHER],
        }
        choice = post(label, body)["choices"][0]
        return {
            "turns": [
                {
                    "finish_reason_stop": choice.get("finish_reason") == "stop",
                    "no_call": not choice["message"].get("tool_calls"),
                    "content_is_5": (choice["message"].get("content") or "").strip()
                    == "5",
                }
            ]
        }
    if probe == "P4":
        body = {
            **COMMON,
            "messages": user(PROMPTS["P4"]),
            "tools": [FIND_USER_ID, GET_ORDERS],
        }
        return {
            "turns": follow(
                label,
                body,
                [
                    ("find_user_id", lambda a: a == {"name": "Ada Lovelace"}),
                    ("get_orders", lambda a: a == {"user_id": "u-17"}),
                ],
            )
        }
    raise SystemExit(f"unknown probe {probe}")


if __name__ == "__main__":
    cap, entry, variant = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    probes = (sys.argv[4] if len(sys.argv) > 4 else "P1,P2,P3,P4,P1R").split(",")
    out = cap / entry / variant
    out.mkdir(parents=True, exist_ok=True)
    props = wait_ready()
    template = props.get("chat_template") or ""
    (out / "props.json").write_text(
        json.dumps(
            {
                "build_info": props.get("build_info"),
                "model_path": props.get("model_path"),
                "chat_template_sha256": hashlib.sha256(
                    template.encode("utf-8")
                ).hexdigest(),
                "chat_template_caps": props.get("chat_template_caps"),
                "chat_template": template,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with (out / "verdicts.jsonl").open("a", encoding="utf-8") as fh:
        for probe in probes:
            try:
                result = run(entry, variant, probe)
            except (
                urllib.error.HTTPError
            ) as err:  # e.g. the autoparser refusing the template
                result = {
                    "turns": [{"http_status_ok": False}],
                    "error": err.read().decode(),
                }
            passed = all(
                v is True
                for turn in result["turns"]
                for k, v in turn.items()
                if k != "final_text"
            )
            fh.write(
                json.dumps(
                    {
                        "entry": entry,
                        "variant": variant,
                        "probe": probe,
                        "pass": passed,
                        **result,
                    }
                )
                + "\n"
            )
            print(f"{entry} {variant} {probe}: {'PASS' if passed else 'FAIL'}")
```

#### `spike/resend.py`

```python
"""Attribution (a): resend one captured request body unchanged to the server relaunched
with --skip-chat-parsing, and classify the raw content it returns.

Usage: python resend.py <capture-folder> <base-label> <exchange-index> skipparse
<exchange-index> is the 0-based line of the failing turn in proxy/<base-label>.jsonl.
Appends one line to <capture>/<entry>/skipparse/attribution.jsonl.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

PROXY = "http://127.0.0.1:8081"
# The two documented call formats (blocked spike, Follow-up run 3 (a)).
DENSE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
MOE = re.compile(
    r"<tool_call>\s*<function=([\w.-]+)>(.*?)</function>\s*</tool_call>", re.S
)
PARAM = re.compile(r"<parameter=([\w.-]+)>\n?(.*?)\n?</parameter>", re.S)


def well_formed_calls(text: str) -> list:
    calls = []
    for raw in DENSE.findall(text):
        try:
            obj = json.loads(raw)
            if (
                isinstance(obj, dict)
                and "name" in obj
                and isinstance(obj.get("arguments"), dict)
            ):
                calls.append({"name": obj["name"], "arguments": obj["arguments"]})
        except ValueError:
            pass
    for name, inner in MOE.findall(text):
        calls.append({"name": name, "arguments": dict(PARAM.findall(inner))})
    return calls


if __name__ == "__main__":
    cap, base_label, index, variant = (
        Path(sys.argv[1]),
        sys.argv[2],
        int(sys.argv[3]),
        sys.argv[4],
    )
    lines = (
        (cap / "proxy" / f"{base_label}.jsonl").read_text(encoding="utf-8").splitlines()
    )
    body = json.loads(lines[index])["request"]
    entry, _, probe, _ = base_label.split("__")
    label = f"{entry}__direct__{probe}-x{index}__{variant}"
    req = urllib.request.Request(
        f"{PROXY}/{label}/v1/chat/completions",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        raw = r.read().decode()
    if body.get("stream"):
        sys.exit("resend a non-streamed exchange; P5 is attributed through P1")
    msg = json.loads(raw)["choices"][0]["message"]
    content = msg.get("content") or ""
    result = {
        "base_label": base_label,
        "exchange": index,
        "variant": variant,
        "label": label,
        "parsed_tool_calls": msg.get("tool_calls"),
        "raw_content": content,
        "well_formed_calls_in_content": well_formed_calls(content),
    }
    if variant == "skipparse":
        result["verdict"] = (
            "failing-template"
            if result["well_formed_calls_in_content"]
            else "failing-model"
        )
    out = cap / entry / variant
    out.mkdir(parents=True, exist_ok=True)
    with (out / "attribution.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("label", "parsed_tool_calls", "well_formed_calls_in_content")
            },
            indent=1,
        )
    )
    print(
        "verdict:",
        result.get("verdict", "read parsed_tool_calls against the probe's expectation"),
    )
```

#### `spike/replay.py`

```python
"""Overhead replay: every captured chat request of one entry -> /apply-template + /tokenize.

Usage: python replay.py <capture-folder> <entry-id>   (the entry's base server must be up)
Per exchange: the engine's prompt count (usage.prompt_tokens, else timings prompt_n + cache_n
on a stream), the replayed count, whether they match, and the Q33 overhead against the
`direct` render of the same probe's first request.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENGINE = "http://127.0.0.1:8080"


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{ENGINE}{path}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def engine_prompt_tokens(response) -> tuple:
    if isinstance(response, dict):
        return response.get("usage", {}).get("prompt_tokens"), "usage.prompt_tokens"
    last = None  # SSE: the final chunk carries timings; usage only with stream_options
    for line in str(response).splitlines():
        if line.startswith("data: ") and line != "data: [DONE]":
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                return chunk["usage"]["prompt_tokens"], "usage.prompt_tokens (stream)"
            last = chunk.get("timings") or last
    if last:
        return last["prompt_n"] + last["cache_n"], "timings.prompt_n+cache_n (stream)"
    return None, "absent"


def rendered_tokens(request: dict) -> int:
    template_body = {
        k: request[k]
        for k in ("messages", "tools", "chat_template_kwargs")
        if k in request
    }
    prompt = post("/apply-template", template_body)["prompt"]
    return len(post("/tokenize", {"content": prompt, "add_special": True})["tokens"])


if __name__ == "__main__":
    cap, entry = Path(sys.argv[1]), sys.argv[2]
    out = cap / "replay"
    out.mkdir(parents=True, exist_ok=True)
    baseline = {}
    rows = []
    for path in sorted((cap / "proxy").glob(f"{entry}__*.jsonl")):
        _, harness, probe, variant = path.stem.split("__")
        if variant in ("skipparse", "hftemplate"):
            continue  # another template or parser was in force; replay only base-server captures
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            ex = json.loads(line)
            if not ex["path"].endswith("/chat/completions") or not isinstance(
                ex["request"], dict
            ):
                continue
            engine, source = engine_prompt_tokens(ex["response"])
            replayed = rendered_tokens(ex["request"])
            try:  # second, independent count of the same body (b10537 README, Token Counting)
                check = post("/v1/chat/completions/input_tokens", ex["request"]).get(
                    "input_tokens"
                )
            except urllib.error.HTTPError as err:
                check = f"HTTP {err.code}"
            if harness == "direct" and variant == "base" and i == 0:
                baseline[probe] = replayed
            rows.append(
                {
                    "label": path.stem,
                    "exchange": i,
                    "harness": harness,
                    "probe": probe,
                    "variant": variant,
                    "engine_prompt_tokens": engine,
                    "engine_source": source,
                    "replayed_tokens": replayed,
                    "input_tokens_endpoint": check,
                    "replay_matches_engine": engine == replayed,
                    "sent": {
                        k: ex["request"].get(k, "not sent")
                        for k in ("tool_choice", "parallel_tool_calls", "stream")
                    },
                }
            )
    for row in rows:
        own = baseline.get(row["probe"])
        row["direct_first_request_tokens"] = own
        if (
            row["exchange"] == 0
            and own is not None
            and row["engine_prompt_tokens"] is not None
        ):
            row["q33_overhead_first_call"] = row["engine_prompt_tokens"] - own
    with (out / f"{entry}.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
            print(
                row["label"],
                row["exchange"],
                row["engine_prompt_tokens"],
                row["replayed_tokens"],
                "MATCH" if row["replay_matches_engine"] else "DIFF",
                row.get("q33_overhead_first_call", ""),
            )
```

#### `spike/drive.py`

```python
"""Drive one framework through the logging proxy on one probe, and dump its own call record.

Usage: uv run --group harness-probe python drive.py <capture-folder> <harness> <entry-id> <P1|P4> <default|aligned>
  default -> the framework's request defaults, kept (owner answer Q109 (a)).
  aligned -> smolagents tool_choice "auto"; llamaindex streaming=False, allow_parallel_tool_calls=False.
The proxy captures every request under <entry>__<harness>__<probe>__<variant>; this script
writes the framework's own record to <capture>/harness/<same label>.txt.
"""

import asyncio
import sys
from importlib.metadata import version
from pathlib import Path

from probe_tools import CALLABLES_FOR, PROMPTS, TOOLS_FOR

cap, harness, entry, probe, variant = Path(sys.argv[1]), *sys.argv[2:6]
label = f"{entry}__{harness}__{probe}__{variant}"
URL = f"http://127.0.0.1:8081/{label}/v1"
KEY = "no-key"  # llama-server is started without --api-key, so any string passes
PROMPT, FUNCS, DICTS = PROMPTS[probe], CALLABLES_FOR[probe], TOOLS_FOR[probe]
record: list[str] = []


def smolagents_run() -> None:
    from smolagents import OpenAIServerModel, ToolCallingAgent, tool
    from smolagents.memory import ActionStep

    extra = {"tool_choice": "auto"} if variant == "aligned" else {}
    model = OpenAIServerModel(
        model_id="local", api_base=URL, api_key=KEY, temperature=0, **extra
    )
    agent = ToolCallingAgent(tools=[tool(f) for f in FUNCS], model=model, max_steps=6)
    record.append(f"final: {agent.run(PROMPT)!r}")
    for step in agent.memory.steps:
        if isinstance(step, ActionStep):
            record.append(
                f"step {step.step_number}: tool_calls={step.tool_calls!r} "
                f"error={step.error!r} output={step.model_output_message!r}"
            )


def langgraph_run() -> None:
    from langchain_openai import ChatOpenAI
    from langgraph.graph import START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode, tools_condition

    llm = ChatOpenAI(
        model="local", base_url=URL, api_key=KEY, temperature=0, use_responses_api=False
    ).bind_tools(DICTS)  # direct's dicts, passed through
    graph = StateGraph(MessagesState)
    graph.add_node("agent", lambda state: {"messages": [llm.invoke(state["messages"])]})
    graph.add_node("tools", ToolNode(FUNCS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    state = graph.compile().invoke(
        {"messages": [("user", PROMPT)]}, {"recursion_limit": 12}
    )
    record.extend(repr(m) for m in state["messages"])


def pydantic_ai_run() -> None:
    from pydantic_ai import Agent, ModelSettings
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    model = OpenAIChatModel("local", provider=OpenAIProvider(base_url=URL, api_key=KEY))
    agent = Agent(
        model,
        output_type=str,
        tools=FUNCS,
        model_settings=ModelSettings(temperature=0.0),
    )
    result = agent.run_sync(PROMPT)
    record.append(f"final: {result.output!r}")
    record.append(f"usage: {result.usage!r}")  # a property at 2.53.0, not a method
    record.extend(repr(m) for m in result.all_messages())


def llamaindex_run() -> None:
    from llama_index.core.agent.workflow import (
        AgentOutput,
        FunctionAgent,
        ToolCall,
        ToolCallResult,
    )
    from llama_index.core.tools import FunctionTool
    from llama_index.llms.openai_like import OpenAILike

    llm = OpenAILike(
        model="local",
        api_base=URL,
        api_key=KEY,
        temperature=0,
        context_window=32768,
        is_chat_model=True,
        is_function_calling_model=True,
    )
    extra = (
        {"streaming": False, "allow_parallel_tool_calls": False}
        if variant == "aligned"
        else {}
    )
    agent = FunctionAgent(
        tools=[FunctionTool.from_defaults(f) for f in FUNCS], llm=llm, **extra
    )

    async def main() -> None:
        handler = agent.run(user_msg=PROMPT)
        async for event in handler.stream_events():
            if isinstance(event, (ToolCall, ToolCallResult, AgentOutput)):
                record.append(f"{type(event).__name__}: {event!r}")
        record.append(f"final: {await handler!r}")

    asyncio.run(main())


RUNNERS = {
    "smolagents": smolagents_run,
    "langgraph": langgraph_run,
    "pydantic-ai": pydantic_ai_run,
    "llamaindex": llamaindex_run,
}
DISTRIBUTIONS = {
    "smolagents": ["smolagents", "openai"],
    "langgraph": [
        "langgraph",
        "langgraph-prebuilt",
        "langchain-core",
        "langchain-openai",
        "openai",
    ],
    "pydantic-ai": ["pydantic-ai-slim", "openai"],
    "llamaindex": [
        "llama-index-core",
        "llama-index-llms-openai-like",
        "llama-index-llms-openai",
        "openai",
    ],
}

if __name__ == "__main__":
    record.append(
        "versions: " + ", ".join(f"{d}=={version(d)}" for d in DISTRIBUTIONS[harness])
    )
    try:
        RUNNERS[harness]()
        status = "completed"
    except Exception as exc:  # the failure is evidence; keep it in the record
        status = f"raised {type(exc).__name__}: {exc}"
    record.append(f"status: {status}")
    out = cap / "harness"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{label}.txt").write_text("\n".join(record) + "\n", encoding="utf-8")
    print(label, status)
```

#### `spike/fetch_templates.py`

```python
"""Write Qwen's own HF chat templates, at pinned revisions, as --chat-template-file controls.

Usage: python fetch_templates.py <capture-folder>  -> <capture>/templates/*.jinja (UTF-8, no BOM)
Refuses if a template's sha256 differs from the one read on 2026-10-03.
"""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HF = "https://huggingface.co"
SOURCES = {
    # Qwen3-0.6B, -1.7B and -4B carry the same chat_template at these revisions; one file serves the three.
    "qwen3-dense.hf.jinja": (
        f"{HF}/Qwen/Qwen3-0.6B/resolve/c1899de289a04d12100db370d81485cdf75e47ca/tokenizer_config.json",
        "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8",  # pragma: allowlist secret
    ),
    "qwen3.6-moe.hf.jinja": (
        f"{HF}/Qwen/Qwen3.6-35B-A3B/resolve/995ad96eacd98c81ed38be0c5b274b04031597b0/chat_template.jinja",
        "e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259",  # pragma: allowlist secret
    ),
}

out = Path(sys.argv[1]) / "templates"
out.mkdir(parents=True, exist_ok=True)
for name, (url, expected) in SOURCES.items():
    with urllib.request.urlopen(url, timeout=60) as r:
        raw = r.read().decode("utf-8")
    text = json.loads(raw)["chat_template"] if url.endswith(".json") else raw
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != expected:
        sys.exit(
            f"{name}: sha256 {digest} != {expected}; the pinned file changed, stop"
        )
    (out / name).write_bytes(text.encode("utf-8"))
    print(name, digest, url)
```

### Sources

All read 2026-10-03.

- llama.cpp b10537 = commit `bf0040e15fd5b716262658f4d652c9cee959cf91`:
  - `tools/server/README.md` (https://github.com/ggml-org/llama.cpp/blob/bf0040e15fd5b716262658f4d652c9cee959cf91/tools/server/README.md): lines 107 (`--log-file`), 111 (`-lv`), 207 (`--api-key`, default none), 234-235 (`--chat-template-file`, `--skip-chat-parsing`), 463-474 (`/health` 503 while loading), 670-684 (`/tokenize`), 721-731 (`/apply-template`), 823-918 (`/props`: `build_info`, `chat_template`, `chat_template_caps`), 1321-1323 (`parse_tool_calls`, `parallel_tool_calls`), 1388-1430 (`timings`, `usage`), 1546-1557 (`/v1/chat/completions/input_tokens`).
  - `tools/server/server-common.cpp` lines 1128-1150, 1288-1293, 1383-1388.
  - `tools/server/server-schema.cpp` lines 26-29, 314.
  - `tools/server/server-task.cpp` lines 504-518.
  - `common/chat.cpp` lines 3593, 3690-3704, 3739.
  - `common/chat.h` line 294.
  - `common/arg.cpp` lines 3700-3724, 3824.
- Hugging Face Hub API, `https://huggingface.co/api/models/Qwen/{Qwen3-0.6B,Qwen3-1.7B,Qwen3-4B,Qwen3.6-35B-A3B}/revision/main`, for the revision SHAs above. The files were read at `https://huggingface.co/<repo>/resolve/<sha>/<file>`.
- uv CLI reference (https://docs.astral.sh/uv/reference/cli/): `uv add --group` ("The lockfile and project environment will be updated"), `uv run --group`.
- smolagents `v1.26.0` (https://raw.githubusercontent.com/huggingface/smolagents/v1.26.0/src/smolagents/):
  - `models.py` lines 497, 510, 541-550 (precedence: `self.kwargs` overrides the `tool_choice="required"` default), 1672-1682, 1796.
  - `agents.py` lines 1233-1240, 1309-1313.
  - `tools.py` line 1061.
  - `_function_type_hints_utils.py` lines 204-243.
- LangGraph `1.2.12` (`libs/langgraph/langgraph/graph/__init__.py`: `StateGraph`, `MessagesState`, `START`) and `prebuilt==1.1.0` (`libs/prebuilt/langgraph/prebuilt/__init__.py`; `tool_node.py` lines 743-783, which accept callables, and 1582, `tools_condition`), at https://github.com/langchain-ai/langgraph.
- langchain-openai `1.6.7` (`libs/partners/openai/langchain_openai/chat_models/base.py` lines 801-934, 1551-1582, 1999-2016, 2494-2560) and langchain-core `1.4.7` (`utils/function_calling.py` lines 503-516, 562-564, 732-798), at https://github.com/langchain-ai/langchain.
- pydantic-ai `v2.53.0` (https://github.com/pydantic/pydantic-ai, `pydantic_ai_slim/pydantic_ai/`):
  - `agent/__init__.py` lines 597-610.
  - `tools.py` line 85.
  - `providers/openai.py` lines 102-107.
  - `models/openai.py` lines 997-1021, 1115-1116, 1215-1247.
  - `models/_tool_choice.py` line 31.
  - `run.py` lines 725, 854, 928-931 (`usage` is a property).
- LlamaIndex `v0.14.25` (https://github.com/run-llama/llama_index):
  - `llama-index-core/llama_index/core/agent/workflow/base_agent.py` lines 135-172, 751-793.
  - `core/tools/function_tool.py` lines 172-191, 440-481. The Google-style `Args:` regex requires `name (type): ...`, hence the docstrings in `probe_tools.py`.
  - `llama-index-llms-openai-like` 0.8.1 has no matching tag. It was read at commit `139761450a1e43c65042b10d01be6bb3605534ed` (`openai_like/base.py` lines 96-107; `llms/openai/base.py` lines 261-291, 458, 969-1018).
  - Streaming and events: https://developers.llamaindex.ai/python/framework/understanding/agent/streaming/.
- Project: `src/wave_local_ai_v2/server.py` (`build_flags`), `roster.py` (`load_roster`, `resolve_entry`), `local_client.py` lines 76-82 and 287-345, `engines.py` line 29 (registry path relative to the working directory), `quality_cli.py` lines 105-106, `aidd_docs/roster/models.json`, `.env.example`.

### Gaps left open (not invented)

- smolagents under `tool_choice: "auto"`, when the model answers in plain text: `ToolCallingAgent` falls back to `model.parse_tool_calls`. What it does on failure was not traced. The `aligned` run shows it.
- `llama-index-llms-openai`: the version uv resolves under `llama-index-llms-openai-like` 0.8.1 is not pinned here. `drive.py` records it in each LlamaIndex record.
- pydantic-ai's parsing of the `Args:` docstring section was not read. The tool descriptions it sends are in the proxy capture.
- The size of the `harness-probe` environment, the MoE's load time, and the size of a `-lv 5` log were not measured from the desk.
- Whether `/props` `chat_template` reports a `--chat-template-file` override is undocumented ("the model's original Jinja2 prompt template"). Step 4d (b) checks it by hash rather than assuming it.
