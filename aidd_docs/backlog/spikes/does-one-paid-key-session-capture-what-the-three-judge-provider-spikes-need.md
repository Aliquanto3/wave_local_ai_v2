---
type: spike
status: open
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parents:
  - aidd_docs/backlog/stories/a-glm-judge-answers-through-z-ai-under-the-pinning-discipline.md
  - aidd_docs/backlog/stories/a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline.md
  - aidd_docs/backlog/stories/a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md
related_to:
  - aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md
  - aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md
  - aidd_docs/backlog/spikes/which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms.md
---

# Spike: Does one paid-key session capture what the three judge-provider spikes need

## Question

Can one operator, in one sitting with paid keys for DeepSeek, Z.ai and OpenAI, capture every live request and response that the Bounds of the three judge-provider spikes name, under Methodology 12 as amended by owner answer Q102 (a), 2026-10-03, within a hard spend cap and without ever writing an API key to disk?

## Decision

Whether the owner funds the three accounts and schedules the sitting now. The captures are the only input the three blocked spikes still lack; each spike is then concluded from them (go or no-go per provider), and only then can its parent story be refined to `ready`.

Closes, once the captures exist and each spike is concluded from them:

- `aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md` => judge epic order 8, `a-glm-judge-answers-through-z-ai-under-the-pinning-discipline.md`.
- `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md` => judge epic order 9, `a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline.md`.
- `aidd_docs/backlog/spikes/which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms.md` => judge epic order 11, `a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md` (which also waits on order 10 through `depends_on`).
- Transitively, through orders 8 and 9 (each Blocked line read 2026-10-03), the judge-provider blocker leaves: judge epic order 10 (`glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md`) and order 6 (`the-judged-probe-runs-both-paths-in-three-languages.md`); quality epic order 2 (`judge-scoring-with-inter-judge-agreement-proves-judged-machinery.md`), order 5 (`the-rewriting-suite-scores-dense-and-moe-side-by-side-under-the-judge-pair.md`) and order 6 (`a-judged-re-run-receives-a-reproduction-verdict-that-separates-the-subject-from-its-judges.md`); use-case epic order 3 (`document-comparison-is-scored-against-a-reference-and-two-judges.md`), order 5 (`a-rag-answer-is-scored-over-a-local-corpus-under-a-named-harness.md`), order 9 (`a-web-research-score-recomputes-offline-from-its-archived-search-responses.md`, still blocked by its search-tool spike's SearXNG capture) and order 10 (`two-search-tools-answer-the-same-queries-and-each-row-names-its-tool.md`, still blocked by the Mojeek account and capture). Each of these still waits on the implementation of its predecessors; only the paid-key blocker goes.

## Bounds

- Evidence needed: every capture listed under "Stop-when checklist" below, written by the capture tool in this spike into one folder, plus the saved terms pages and the tally. The calls themselves are the three spikes' own Follow-up calls, referenced by number and never restated here; this spike adds only what they lack: a one-token probe per provider, a marker-stability repeat per provider (within the sitting and again at its end), scripted bursts with a hard request and spend cap, a placeholder-free Luna call 5 (and call 2), a prompt for GLM call 4, a scripted save of the terms pages, the capture folder and its redaction rule, and the cost and time estimates.
- Stop when: every capture in the checklist exists in the capture folder, the redaction check prints 0, and `tally.txt` is written. Conclusions (go or no-go, pin, markers) are not drawn here; they belong to each spike's conclude step.
- Spend cap: $0.50 per burst, enforced by the tool; the whole sitting is bounded at about $0.42, $0.64 if the Z.ai burst needs its full 600 requests (arithmetic below).
- Tags: paid key + operator.

### Prerequisites

1. Three accounts with prepaid credit (owner act): DeepSeek Open Platform; Z.ai international (`api.z.ai`, token-priced; not the Coding Plan endpoint, not bigmodel.cn); OpenAI API platform. OpenAI's tier follows the amount paid: $5 => Tier 1 (500 RPM for `gpt-5.6-luna`), $50 => Tier 2 (5,000 RPM) (https://developers.openai.com/api/docs/guides/rate-limits and https://developers.openai.com/api/docs/models/gpt-5.6-luna, read 2026-10-03). Tradeoff: a payment of $5 to $49 keeps the account on Tier 1, where the 600-request burst can reach the limit; at Tier 2 or above the burst records "no 429 within 600", which Luna call 7 accepts as its result.
2. The DeepSeek training opt-out email sent before the first paid DeepSeek call (owner act, owner answer Q103 (c), 2026-10-03): to privacy@deepseek.com from the account owner's address, requesting the opt-out for API inputs. Its date goes into `deepseek/d00-opt-out.txt` (step 3 of the run sheet); any reply is kept for the README.
3. Keys in the repo-root `.env` (gitignored, `.gitignore` line 20) as `DEEPSEEK_API_KEY`, `ZAI_API_KEY`, `OPENAI_API_KEY`, the names the three spikes and their stories use. `settings.py` and `.env.example` read none of the three today; orders 8, 9 and 11 add them.
4. The repo's virtual environment already synced (the tool runs with `uv run --no-sync` and uses the standard library only, so nothing is installed during the sitting); `curl.exe` as shipped with Windows 11; a logged-in browser on the Z.ai console for its concurrency figure.

### Capture folder and redaction

- One folder per sitting: `aidd_docs/tasks/<yyyy_mm>/<yyyy_mm_dd>_judge-provider-live-calls/`, with `deepseek/`, `zai/`, `openai/` and `terms/` beneath it, `live_calls.py` (the tool, extracted from this file) and `tally.txt`.
- Each capture is one write-once JSON file `<provider>/<label>.json` holding the UTC time, elapsed seconds, the request (method, URL, headers, body) and the response (status, every header, body). The tool refuses to overwrite a label.
- Redaction rule: an API key is never written anywhere. The tool reads keys only from the environment `uv run --env-file .env` builds, records `Authorization` as `Bearer <redacted>`, and refuses to write any capture whose text contains a key value. Keys never appear on a command line, so they are not in shell history either. Do not run `Start-Transcript` or a proxy during the sitting. The final redaction check (run sheet step 9) must print 0 before anything in the folder is committed. OpenAI response headers carry `openai-organization` and `openai-project` ids; they are not keys, and whether to keep them before a commit is the owner's choice.

### Capture tool

Saved into the capture folder by run sheet step 1. Standard library only. `call` sends one request; `repeat` sends the same request N times and reports which build markers changed (`model`, `system_fingerprint`, the pin's listing entry, and any response header whose name contains version, model, fingerprint or build); `compare` runs the same marker check across saved captures; `burst` sends N copies of one request either all at once (`wave`, for a concurrency limit) or through a worker pool that stops at the first 429 (`stream`, for a request-rate limit), refusing beyond 600 requests or a worst-case spend over `--max-usd` (itself capped at $0.50), and bounds input tokens by the body's byte count (a token covers at least one byte); `tally` prices every saved `usage` at the list prices below.

```python
"""Capture live judge-provider calls as write-once JSON, never writing an API key.

Run from the repo root (keys in .env), body as JSON on stdin for POST:
  call   PROVIDER LABEL METHOD PATH [--no-auth]
  repeat PROVIDER LABEL METHOD PATH --times N
  burst  PROVIDER LABEL PATH --count N --max-usd X --mode wave|stream
         [--workers W] [--dry-run]
  compare PROVIDER OUT_LABEL LABEL [LABEL ...]   (markers across saved captures)
  tally
Captures land in $JUDGE_CAPTURE_DIR/<provider>/<label>.json.
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

# List prices per 1M tokens as the three spikes recorded them (DeepSeek at its
# peak rate, an upper bound). A burst may only target the priced pin model.
PROVIDERS = {
    "deepseek": {
        "host": "https://api.deepseek.com",
        "key": "DEEPSEEK_API_KEY",
        "model": "deepseek-v4-pro",
        "in": 1.32,
        "out": 3.96,
        "cap_field": "max_tokens",
    },
    "zai": {
        "host": "https://api.z.ai",
        "key": "ZAI_API_KEY",
        "model": "glm-5.2",
        "in": 1.40,
        "out": 4.40,
        "cap_field": "max_tokens",
    },
    "openai": {
        "host": "https://api.openai.com",
        "key": "OPENAI_API_KEY",
        "model": "gpt-5.6-luna",
        "in": 0.20,
        "out": 1.20,
        "cap_field": "max_completion_tokens",
    },
}
MARKER_HINTS = ("version", "model", "fingerprint", "build")
# Hard ceilings no argument can lift.
MAX_BURST_REQUESTS = 600
MAX_BURST_USD = 0.50
CAPTURE_DIR = Path(os.environ.get("JUDGE_CAPTURE_DIR", ""))


def send(provider, method, path, body, auth=True, timeout=120):
    p = PROVIDERS[provider]
    key = os.environ.get(p["key"], "")
    if auth and not key:
        sys.exit(f"{p['key']} is not set")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(p["host"] + path, data=data, method=method)
    shown = {}
    if data is not None:
        req.add_header("Content-Type", "application/json")
        shown["Content-Type"] = "application/json"
    if auth:
        req.add_header("Authorization", f"Bearer {key}")
        shown["Authorization"] = "Bearer <redacted>"
    utc = datetime.now(UTC).isoformat()
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, headers, raw = resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as err:
        status, headers, raw = err.code, dict(err.headers.items()), err.read()
    except OSError as err:
        status, headers, raw = None, {}, repr(err).encode()
    text = raw.decode("utf-8", "replace")
    try:
        parsed = json.loads(text)  # tolerates DeepSeek's keep-alive blank lines
    except ValueError:
        parsed = text
    return {
        "utc": utc,
        "elapsed_s": round(time.monotonic() - started, 3),
        "request": {
            "method": method,
            "url": p["host"] + path,
            "headers": shown,
            "body": body,
        },
        "response": {"status": status, "headers": headers, "body": parsed},
    }


def write(provider, label, obj):
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    for p in PROVIDERS.values():
        key = os.environ.get(p["key"], "")
        if key and key in text:
            sys.exit("refused: an API key appears in the capture; nothing written")
    path = CAPTURE_DIR / provider / f"{label}.json"
    if path.exists():
        sys.exit(f"refused: {path} exists; captures are write-once")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {path}")


def same(values):
    return len({json.dumps(v, sort_keys=True) for v in values}) == 1


def body_of(capture):
    body = capture["response"]["body"]
    return body if isinstance(body, dict) else {}


def markers(provider, captures):
    out = {}
    for field in ("model", "system_fingerprint"):
        values = [body_of(c).get(field) for c in captures]
        out[field] = {"values": values, "stable": same(values)}
    if any("data" in body_of(c) for c in captures):
        pin = PROVIDERS[provider]["model"]
        values = [
            next((e for e in body_of(c).get("data", []) if e.get("id") == pin), None)
            for c in captures
        ]
        out["listing_entry"] = {"values": values, "stable": same(values)}
    names = {n for c in captures for n in c["response"]["headers"]}
    for name in sorted(names):
        if any(h in name.lower() for h in MARKER_HINTS):
            values = [c["response"]["headers"].get(name) for c in captures]
            out[f"header:{name}"] = {"values": values, "stable": same(values)}
    return out


def usage_usd(provider, capture):
    p = PROVIDERS[provider]
    usage = body_of(capture).get("usage") or {}
    tokens_in = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
    tokens_out = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
    return (tokens_in * p["in"] + tokens_out * p["out"]) / 1e6


def stdin_json():
    # PowerShell may pipe a UTF-8 BOM ahead of the body; utf-8-sig drops it.
    return json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))


def read_body(method):
    return stdin_json() if method == "POST" else None


def cmd_call(a):
    capture = send(
        a.provider, a.method, a.path, read_body(a.method), auth=not a.no_auth
    )
    write(a.provider, a.label, capture)
    print(capture["response"]["status"], json.dumps(markers(a.provider, [capture])))


def cmd_repeat(a):
    body = read_body(a.method)
    captures = [send(a.provider, a.method, a.path, body) for _ in range(a.times)]
    result = markers(a.provider, captures)
    write(a.provider, a.label, {"captures": captures, "markers": result})
    for name, entry in result.items():
        print(("stable  " if entry["stable"] else "CHANGED ") + name)


def cmd_burst(a):
    p = PROVIDERS[a.provider]
    body = stdin_json()
    if body.get("model") != p["model"]:
        sys.exit(f"refused: a burst must target the priced pin model {p['model']}")
    out_cap = body.get(p["cap_field"])
    if not isinstance(out_cap, int):
        sys.exit(f"refused: a burst body must set {p['cap_field']}")
    if a.count > MAX_BURST_REQUESTS:
        sys.exit(f"refused: --count {a.count} exceeds {MAX_BURST_REQUESTS}")
    in_bound = len(json.dumps(body).encode())  # a token covers at least one byte
    worst = a.count * (in_bound * p["in"] + out_cap * p["out"]) / 1e6
    print(
        f"worst-case spend {a.count} x ({in_bound} in + {out_cap} out) = ${worst:.4f}"
    )
    if worst > min(a.max_usd, MAX_BURST_USD):
        sys.exit(f"refused: worst case ${worst:.4f} exceeds the spend cap")
    if a.dry_run:
        return
    stop = threading.Event()
    barrier = threading.Barrier(a.count, timeout=60) if a.mode == "wave" else None

    def one(_):
        if barrier is not None:
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass  # a straggler past 60 s still sends; its timing is on its row
        elif stop.is_set():
            return None
        capture = send(a.provider, "POST", a.path, body)
        if capture["response"]["status"] == 429:
            stop.set()
        return capture

    workers = a.count if a.mode == "wave" else a.workers
    with ThreadPoolExecutor(max_workers=workers) as pool:
        captures = [c for c in pool.map(one, range(a.count)) if c is not None]
    statuses = [c["response"]["status"] for c in captures]
    first_ok = next((c for c in captures if c["response"]["status"] == 200), None)
    first_err = next((c for c in captures if c["response"]["status"] != 200), None)
    write(
        a.provider,
        a.label,
        {
            "mode": a.mode,
            "requested": a.count,
            "sent": len(captures),
            "worst_case_usd": round(worst, 4),
            "billed_usd_from_usage": round(
                sum(usage_usd(a.provider, c) for c in captures), 6
            ),
            "status_counts": {str(s): statuses.count(s) for s in set(statuses)},
            "first_non_200": first_err,
            "first_200": first_ok,
            "rows": [
                {
                    "utc": c["utc"],
                    "elapsed_s": c["elapsed_s"],
                    "status": c["response"]["status"],
                    "model": body_of(c).get("model"),
                    "system_fingerprint": body_of(c).get("system_fingerprint"),
                }
                for c in captures
            ],
        },
    )
    print(json.dumps({str(s): statuses.count(s) for s in set(statuses)}))


def cmd_compare(a):
    captures = []
    for label in a.labels:
        path = CAPTURE_DIR / a.provider / f"{label}.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        captures += obj.get("captures", [obj] if "response" in obj else [])
    result = markers(a.provider, captures)
    write(a.provider, a.out_label, {"compared": a.labels, "markers": result})
    for name, entry in result.items():
        print(("stable  " if entry["stable"] else "CHANGED ") + name)


def cmd_tally(_):
    grand = 0.0
    for provider in PROVIDERS:
        total = 0.0
        for path in sorted((CAPTURE_DIR / provider).glob("*.json")):
            obj = json.loads(path.read_text(encoding="utf-8"))
            if "billed_usd_from_usage" in obj:
                total += obj["billed_usd_from_usage"]
            for capture in obj.get("captures", [obj] if "response" in obj else []):
                total += usage_usd(provider, capture)
        grand += total
        print(f"{provider}: ${total:.4f}")
    print(f"total: ${grand:.4f}")


def main():
    if not CAPTURE_DIR.is_dir():
        sys.exit("JUDGE_CAPTURE_DIR is not set to an existing folder")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    call = sub.add_parser("call")
    repeat = sub.add_parser("repeat")
    for sp in (call, repeat):
        sp.add_argument("provider", choices=PROVIDERS)
        sp.add_argument("label")
        sp.add_argument("method", choices=("GET", "POST"))
        sp.add_argument("path")
    call.add_argument("--no-auth", action="store_true")
    repeat.add_argument("--times", type=int, required=True)
    burst = sub.add_parser("burst")
    burst.add_argument("provider", choices=PROVIDERS)
    burst.add_argument("label")
    burst.add_argument("path")
    burst.add_argument("--count", type=int, required=True)
    burst.add_argument("--max-usd", type=float, required=True)
    burst.add_argument("--mode", choices=("wave", "stream"), required=True)
    burst.add_argument("--workers", type=int, default=50)
    burst.add_argument("--dry-run", action="store_true")
    compare = sub.add_parser("compare")
    compare.add_argument("provider", choices=PROVIDERS)
    compare.add_argument("out_label")
    compare.add_argument("labels", nargs="+")
    sub.add_parser("tally")
    a = parser.parse_args()
    {
        "call": cmd_call,
        "repeat": cmd_repeat,
        "burst": cmd_burst,
        "compare": cmd_compare,
        "tally": cmd_tally,
    }[a.cmd](a)


if __name__ == "__main__":
    main()
```

### Run sheet

PowerShell 5.1 on Windows 11, from the repo root that holds `.env`. A request body is pasted between `@'` and `'@` (the closing `'@` at column 0) and piped to the tool; keep bodies ASCII. Where a line reads `<... as written>`, paste the `-d` JSON of that call from the named spike's Follow-up, with only the stated change. `--dry-run` on a burst prints its worst-case spend and sends nothing.

1. Setup (prints the three key names, never their values):

```powershell
Select-String -Path .env -Pattern '^(DEEPSEEK|ZAI|OPENAI)_API_KEY=.+' | ForEach-Object { $_.Line.Split('=')[0] }
$m = Get-Date -Format 'yyyy_MM'; $d = Get-Date -Format 'yyyy_MM_dd'
$env:JUDGE_CAPTURE_DIR = "$PWD\aidd_docs\tasks\$m\${d}_judge-provider-live-calls"
New-Item -ItemType Directory -Force $env:JUDGE_CAPTURE_DIR | Out-Null
$md = Get-Content -Raw -Encoding UTF8 'aidd_docs\backlog\spikes\does-one-paid-key-session-capture-what-the-three-judge-provider-spikes-need.md'
[IO.File]::WriteAllText("$env:JUDGE_CAPTURE_DIR\live_calls.py", [regex]::Match($md, '(?s)\x60{3}python\r?\n(.*?)\x60{3}').Groups[1].Value)
function lc { $input | uv run --no-sync --env-file .env python "$env:JUDGE_CAPTURE_DIR\live_calls.py" @args }
lc tally
```

2. Terms and price pages, saved on the day before the first paid call (DeepSeek call 10, Luna call 9, and the terms and price evidence all three Bounds name). Every line of `<date>_index.txt` must start with `200`:

```powershell
$terms = "$env:JUDGE_CAPTURE_DIR\terms"; New-Item -ItemType Directory -Force $terms | Out-Null
$pages = [ordered]@{
  'deepseek-privacy-policy.html'      = 'https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html'
  'deepseek-open-platform-terms.html' = 'https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html'
  'deepseek-pricing.html'             = 'https://api-docs.deepseek.com/quick_start/pricing'
  'deepseek-rate-limit.html'          = 'https://api-docs.deepseek.com/quick_start/rate_limit'
  'zai-terms-of-use.md'               = 'https://docs.z.ai/legal-agreement/terms-of-use.md'
  'zai-privacy-policy-and-dpa.md'     = 'https://docs.z.ai/legal-agreement/privacy-policy.md'
  'zai-pricing.md'                    = 'https://docs.z.ai/guides/overview/pricing.md'
  'openai-services-agreement.html'    = 'https://openai.com/policies/services-agreement/'
  'openai-your-data.html'             = 'https://developers.openai.com/api/docs/guides/your-data'
  'openai-pricing.html'               = 'https://developers.openai.com/api/docs/pricing'
  'openai-gpt-5.6-luna.html'          = 'https://developers.openai.com/api/docs/models/gpt-5.6-luna'
}
foreach ($name in $pages.Keys) {
  $code = curl.exe -sS -L -o "$terms\${d}_$name" -w '%{http_code}' $pages[$name]
  "$code $($pages[$name]) ${d}_$name" | Add-Content -Encoding ascii "$terms\${d}_index.txt"
}
Get-Content "$terms\${d}_index.txt"
```

   The OpenAI Services Agreement answered 403 to a plain fetch on 2026-10-02 (Luna spike) and 2026-10-03 (this spike). For it, and for any other line not starting with `200`: open the URL in a browser, Print => Save as PDF to `terms\<date>_<name>.pdf`, delete the error body the loop saved, and append `browser-pdf <url> <file>` to the index.

3. DeepSeek, non-burst (opt-out email already sent):

```powershell
New-Item -ItemType Directory -Force "$env:JUDGE_CAPTURE_DIR\deepseek" | Out-Null
'opt-out email to privacy@deepseek.com sent on <yyyy-mm-dd> from the account owner address' | Set-Content -Encoding ascii "$env:JUDGE_CAPTURE_DIR\deepseek\d00-opt-out.txt"
lc call deepseek d01a-models GET /models
lc call deepseek d01b-models-noauth GET /models --no-auth
@'
{"model":"deepseek-v4-pro","messages":[{"role":"user","content":"OK"}],"thinking":{"type":"disabled"},"max_tokens":1}
'@ | lc call deepseek d01c-probe-one-token POST /chat/completions
@'
<DeepSeek call 2's JSON, as written>
'@ | lc call deepseek d02-dated-id POST /chat/completions
lc call deepseek d03-v1-models GET /v1/models
@'
<DeepSeek call 4's JSON, as written>
'@ | lc repeat deepseek d04-judge-x5 POST /chat/completions --times 5
@'
<DeepSeek call 4's JSON, as written, with "temperature":1 and "seed":42>
'@ | lc repeat deepseek d05a-seed42-x3 POST /chat/completions --times 3
@'
<the d05a JSON with "seed":43>
'@ | lc call deepseek d05b-seed43 POST /chat/completions
@'
<DeepSeek call 4's JSON, as written, with "reasoning_effort":"none" in place of "thinking">
'@ | lc call deepseek d06-effort-none POST /chat/completions
@'
<DeepSeek call 4's JSON, as written, with user content "Write 300 words about rivers." and "max_tokens":5>
'@ | lc call deepseek d07-caller-cap POST /chat/completions
@'
<DeepSeek call 4's JSON, as written, with "max_tokens":393217>
'@ | lc call deepseek d08-max-tokens-over POST /chat/completions
```

   `d04-judge-x5` covers call 4's three runs and the marker-stability repeat in one file.

4. Z.ai, non-burst:

```powershell
lc call zai z01a-models GET /api/paas/v4/models
lc call zai z01b-models-noauth GET /api/paas/v4/models --no-auth
@'
{"model":"glm-5.2","messages":[{"role":"user","content":"OK"}],"thinking":{"type":"disabled"},"max_tokens":1}
'@ | lc call zai z01c-probe-one-token POST /api/paas/v4/chat/completions
@'
<Z.ai call 2's JSON, as written>
'@ | lc repeat zai z02-thinking-disabled-x5 POST /api/paas/v4/chat/completions --times 5
@'
<Z.ai call 2's JSON, as written, with "thinking":{"type":"enabled"} and "max_tokens":1024>
'@ | lc call zai z03-thinking-enabled POST /api/paas/v4/chat/completions
@'
{"model":"glm-5.2","messages":[{"role":"system","content":"Score the answer from 1 to 10. Reply with the number only."},{"role":"user","content":"Question: What is the capital of France? Answer: Paris."}],"thinking":{"type":"disabled"},"do_sample":false,"max_tokens":16}
'@ | lc repeat zai z04a-greedy-x5 POST /api/paas/v4/chat/completions --times 5
@'
{"model":"glm-5.2","messages":[{"role":"system","content":"Score the answer from 1 to 10. Reply with the number only."},{"role":"user","content":"Question: What is the capital of France? Answer: Paris."}],"thinking":{"type":"disabled"},"do_sample":true,"temperature":0.0,"max_tokens":16}
'@ | lc repeat zai z04b-sampled-t0-x5 POST /api/paas/v4/chat/completions --times 5
@'
<Z.ai call 2's JSON, as written, plus "seed":42>
'@ | lc call zai z05a-seed42 POST /api/paas/v4/chat/completions
@'
<only if z05a returned 200: Z.ai call 2's JSON with "do_sample":true,"temperature":1.0,"seed":42>
'@ | lc repeat zai z05b-seed42-sampled-x5 POST /api/paas/v4/chat/completions --times 5
@'
<Z.ai call 2's JSON, as written, with user content "Write 200 words about rivers." and "max_tokens":4>
'@ | lc call zai z06-caller-cap POST /api/paas/v4/chat/completions
@'
<Z.ai call 2's JSON, as written, with "model":"glm-5.2-20260616">
'@ | lc call zai z07a-dated-id POST /api/paas/v4/chat/completions
@'
<Z.ai call 2's JSON, as written, with "model":"glm-0-nonexistent">
'@ | lc call zai z07b-unknown-id POST /api/paas/v4/chat/completions
```

   GLM call 4 named no prompt; `z04a` and `z04b` use DeepSeek call 4's judge prompt so the two judges' determinism captures are comparable. If `z01a` is not a 200 listing, `z01c` is the Methodology 12 pre-flight and the row records it as a probe.

5. OpenAI, non-burst. The judge text that replaces the `...` in Luna call 2 is `Original: The meeting moved to Thursday because the room was unavailable. Rewrite: Because the room was unavailable, the meeting moved to Thursday.`

```powershell
lc call openai o01a-models GET /v1/models
lc call openai o01b-model-luna GET /v1/models/gpt-5.6-luna
lc call openai o01c-models-noauth GET /v1/models --no-auth
@'
{"model":"gpt-5.6-luna","messages":[{"role":"user","content":"OK"}],"reasoning_effort":"none","max_completion_tokens":1}
'@ | lc call openai o01d-probe-one-token POST /v1/chat/completions
@'
<Luna call 2's JSON, as written, its "..." replaced by the judge text above>
'@ | lc repeat openai o02-seed1234-x5 POST /v1/chat/completions --times 5
@'
<the o02 JSON with "seed":5678>
'@ | lc call openai o03-seed5678 POST /v1/chat/completions
@'
<the o02 JSON with "reasoning_effort":"minimal">
'@ | lc call openai o04a-effort-minimal POST /v1/chat/completions
@'
<the o02 JSON with "reasoning_effort":"low">
'@ | lc call openai o04b-effort-low POST /v1/chat/completions
@'
{"model":"gpt-5.6-luna","reasoning":{"effort":"none"},"temperature":0,"store":false,"max_output_tokens":400,"input":"Score this rewrite from 1 to 5 and reply with the digit only: Original: The meeting moved to Thursday because the room was unavailable. Rewrite: Because the room was unavailable, the meeting moved to Thursday."}
'@ | lc call openai o05a-responses POST /v1/responses
@'
{"model":"gpt-5.6-luna","reasoning":{"effort":"none"},"temperature":0,"store":false,"max_output_tokens":400,"seed":1,"input":"Score this rewrite from 1 to 5 and reply with the digit only: Original: The meeting moved to Thursday because the room was unavailable. Rewrite: Because the room was unavailable, the meeting moved to Thursday."}
'@ | lc call openai o05b-responses-seed POST /v1/responses
@'
<the o02 JSON with "max_completion_tokens":1>
'@ | lc call openai o06-caller-cap POST /v1/chat/completions
lc call openai o08a-unavailable-model GET /v1/models/gpt-5.6-luna-2099-01-01
@'
<the o02 JSON with "model":"gpt-5.6-luna-2099-01-01">
'@ | lc call openai o08b-unavailable-chat POST /v1/chat/completions
```

   `o02-seed1234-x5` covers Luna call 2, call 3's two same-seed repeats and the marker-stability repeat. The account's tier is read from `x-ratelimit-limit-requests` in `o01d`'s headers against the model page's tier table (500 => Tier 1); no dashboard visit is needed.

6. Bursts, last, so a rate-limit penalty cannot disturb the other captures. Run each once with `--dry-run` first.

```powershell
@'
{"model":"deepseek-v4-pro","messages":[{"role":"user","content":"Count from 1 to 40, separated by spaces."}],"thinking":{"type":"disabled"},"temperature":0,"max_tokens":64}
'@ | lc burst deepseek d09-burst-concurrency /chat/completions --count 520 --max-usd 0.30 --mode wave

# Read the glm-5.2 concurrency on https://z.ai/manage-apikey/rate-limits (logged in), then:
$n = <that figure>
"glm-5.2 concurrency $n read on the console at $(Get-Date -Format o)" | Set-Content -Encoding ascii "$env:JUDGE_CAPTURE_DIR\zai\z08a-console-concurrency.txt"
@'
{"model":"glm-5.2","messages":[{"role":"user","content":"Count from 1 to 40, separated by spaces."}],"thinking":{"type":"disabled"},"do_sample":false,"max_tokens":64}
'@ | lc burst zai z08b-burst-concurrency /api/paas/v4/chat/completions --count ($n + 5) --max-usd 0.35 --mode wave

@'
{"model":"gpt-5.6-luna","messages":[{"role":"user","content":"Reply with OK."}],"reasoning_effort":"none","max_completion_tokens":16}
'@ | lc burst openai o07-burst-rpm /v1/chat/completions --count 600 --max-usd 0.05 --mode stream --workers 50
```

   DeepSeek counts concurrency "from the time it is sent until the model response is complete" (DeepSeek spike), so the wave holds 520 requests of up to 64 output tokens open at once against the documented 500. If no 429 arrives, the capture records that, which DeepSeek call 9 already accepts. If `$n + 5` exceeds 600 the tool refuses; then `z08a` alone is call 8's evidence, recorded as "limit above the burst cap".

7. End-of-session marker repeat (at least 60 minutes after the first listing), then cross-time comparison:

```powershell
lc call deepseek d99a-models-end GET /models
@'
<DeepSeek call 4's JSON, as written>
'@ | lc call deepseek d99b-judge-end POST /chat/completions
lc compare deepseek d98a-listing-markers d01a-models d99a-models-end
lc compare deepseek d98b-response-markers d01c-probe-one-token d04-judge-x5 d99b-judge-end

lc call zai z99a-models-end GET /api/paas/v4/models
@'
<Z.ai call 2's JSON, as written>
'@ | lc call zai z99b-judge-end POST /api/paas/v4/chat/completions
lc compare zai z98a-listing-markers z01a-models z99a-models-end
lc compare zai z98b-response-markers z01c-probe-one-token z02-thinking-disabled-x5 z99b-judge-end

lc call openai o99a-model-end GET /v1/models/gpt-5.6-luna
@'
<the o02 JSON>
'@ | lc call openai o99b-judge-end POST /v1/chat/completions
lc compare openai o98a-listing-markers o01b-model-luna o99a-model-end
lc compare openai o98b-response-markers o01d-probe-one-token o02-seed1234-x5 o99b-judge-end
```

   Skip `z99a` and `z98a` if `z01a` was not a 200 listing. A `CHANGED` line is a finding for the spike's conclusion (a marker that is not stable cannot be refused on), never something to retry away.

8. Spend actually billed: `lc tally | Set-Content -Encoding ascii "$env:JUDGE_CAPTURE_DIR\tally.txt"`.

9. Redaction check (must print 0):

```powershell
$keys = Select-String -Path .env -Pattern '^(DEEPSEEK|ZAI|OPENAI)_API_KEY=(.+)$' | ForEach-Object { $_.Matches[0].Groups[2].Value.Trim().Trim('"') }
(Get-ChildItem -Recurse -File $env:JUDGE_CAPTURE_DIR | Select-String -SimpleMatch -Pattern $keys).Count
Remove-Variable keys
```

### Stop-when checklist

Every Bounds item of the three spikes, mapped to the captures that answer it (labels are files under `<provider>/`, `terms/` is shared).

| Bounds item | DeepSeek | Z.ai | OpenAI |
| --- | --- | --- | --- |
| Live catalog, auth, entry shape | d01a, d01b | z01a, z01b (z01c if no listing) | o01a, o01b, o01c |
| Dated ids listed and addressable; alias resolution | d01a, d02 | z01a, z07a | o01a, o08a, o08b |
| Sampling names, ranges, defaults; temperature at the chosen effort | d04, d06, d07 | z02, z04a, z04b | o02, o04b, o05a |
| Seed exists and is honoured | d04, d05a, d05b | z05a, z05b | o02, o03, o05b |
| Content, finish reason, usage; reasoning tokens apart | d04, d07, d08 | z02, z03, z06 | o02, o05a, o06 |
| Reasoning disabled or lowest effort, and what is billed | d04, d06 | z02 vs z03 | o02, o04a, o04b |
| Paid-tier limit, 429 body, retry hint | d09 | z08a, z08b | o07, o01d headers |
| API version a row records | d01a, d03 | z02 headers | o01a, o02 headers |
| Unknown id error | d02 | z07a, z07b | o08a, o08b |
| List price with retrieval date | terms deepseek-pricing | terms zai-pricing | terms openai-pricing, openai-gpt-5.6-luna |
| Data-use and retention terms at a named revision | terms deepseek-privacy-policy, deepseek-open-platform-terms; d00-opt-out | terms zai-terms-of-use, zai-privacy-policy-and-dpa | terms openai-services-agreement (pdf), openai-your-data |
| Build markers and their stability (amended Methodology 12) | d01c, d04, d98a, d98b | z01c, z02, z98a, z98b | o01d, o02, o98a, o98b |

### Cost estimate

List prices per 1M tokens as the spikes recorded them, re-read 2026-10-03: DeepSeek `deepseek-v4-pro` $1.32 input (cache miss) and $3.96 output at peak, off-peak half (https://api-docs.deepseek.com/quick_start/pricing); Z.ai `glm-5.2` $1.40 input and $4.40 output (https://docs.z.ai/guides/overview/pricing.md); OpenAI `gpt-5.6-luna` $0.20 input and $1.20 output (https://developers.openai.com/api/docs/models/gpt-5.6-luna). Listing calls carry no tokens and are counted at $0. Every non-burst call is bounded at 300 input tokens (each body is under 400 bytes, about 100 tokens) and at its own output cap. DeepSeek is priced at peak throughout, an upper bound.

- DeepSeek non-burst: 15 generation calls; output caps 1 (d01c) + 8 (d02) + 5 x 16 (d04) + 3 x 16 (d05a) + 16 (d05b) + 16 (d06) + 5 (d07) + 16 (d08) + 16 (d99b) = 206 tokens. Cost: 15 x 300 x $1.32/1M + 206 x $3.96/1M = $0.00594 + $0.00082 = $0.0068.
- DeepSeek burst: 520 x (185 bytes x $1.32 + 64 x $3.96)/1M = 520 x $0.000498 = $0.2588.
- Z.ai non-burst: 27 generation calls; output caps 1 (z01c) + 5 x 16 (z02) + 1,024 (z03) + 10 x 16 (z04a, z04b) + 16 (z05a) + 5 x 16 (z05b) + 4 (z06) + 2 x 16 (z07) + 16 (z99b) = 1,413 tokens. Cost: 27 x 300 x $1.40/1M + 1,413 x $4.40/1M = $0.01134 + $0.00622 = $0.0176.
- Z.ai burst: ($n + 5) x (179 bytes x $1.40 + 64 x $4.40)/1M = ($n + 5) x $0.000532; $0.1064 at 200 requests, $0.3193 at the 600-request ceiling.
- OpenAI non-burst: 14 generation calls; output caps 1 (o01d) + 5 x 400 (o02) + 400 (o03) + 2 x 400 (o04) + 2 x 400 (o05) + 1 (o06) + 400 (o08b) + 400 (o99b) = 4,802 tokens. Cost: 14 x 300 x $0.20/1M + 4,802 x $1.20/1M = $0.00084 + $0.00576 = $0.0066.
- OpenAI burst: 600 x (143 bytes x $0.20 + 16 x $1.20)/1M = 600 x $0.0000478 = $0.0287.
- Per provider: DeepSeek $0.0068 + $0.2588 = $0.27; Z.ai $0.0176 + $0.1064 = $0.12 (up to $0.34 if 600 burst requests are needed); OpenAI $0.0066 + $0.0287 = $0.04. Total about $0.42 (up to $0.64). Cash outlay is the prepaid credit, not the spend: at least $5 for OpenAI Tier 1; DeepSeek's and Z.ai's minimum top-ups are not sourced.

### Time estimate

About 1.5 hours in one sitting: setup and terms 15 minutes (plus 5 for the browser PDF); DeepSeek, Z.ai and OpenAI non-burst calls 15 minutes each; bursts 15 minutes (a DeepSeek request it queues receives keep-alive lines and can stay open up to 10 minutes, its documented limit); end-of-session repeats, compare, tally and redaction check 15 minutes. The owner acts before it (three accounts with credit, the opt-out email) are outside the sitting.

### Request fields grounded in

Read 2026-10-03 unless stated; the three spikes cite the rest.

- DeepSeek `max_tokens` minimum 1, maximum 393,216; `thinking.type` enabled/disabled; no `seed`; response `model`, `system_fingerprint`, `usage.completion_tokens_details.reasoning_tokens`: https://api-docs.deepseek.com/api/create-chat-completion. Concurrency 500 for `deepseek-v4-pro`, HTTP 429 on excess, empty keep-alive lines while waiting, connection closed after 10 minutes without inference, no Retry-After: https://api-docs.deepseek.com/quick_start/rate_limit.
- Z.ai base `https://api.z.ai/api`, `POST /paas/v4/chat/completions`, Bearer auth; `max_tokens` 1 to 131,072; `temperature` [0.0, 1.0]; `do_sample` default true; `thinking.type` enabled/disabled; no `seed`; response `id`, `request_id`, `created`, `model`, `usage`: https://docs.z.ai/api-reference/llm/chat-completion.md. 429 codes 1302, 1305, 1308, 1310, 1113; unknown model 1211 (HTTP 400): https://docs.z.ai/api-reference/api-code.md.
- OpenAI Chat Completions `max_completion_tokens` (includes reasoning tokens; no minimum stated), `reasoning_effort` values none to max, `seed` Beta best effort; Responses `max_output_tokens`, `reasoning`, `store`, `input` string accepted, no `seed`: SDK types generated from the OpenAPI spec, https://raw.githubusercontent.com/openai/openai-python/v3.24.0/src/openai/types/chat/completion_create_params.py and .../types/responses/response_create_params.py. Rate-limit headers and Retry-After, tier thresholds: https://developers.openai.com/api/docs/guides/rate-limits. `gpt-5.6-luna` single undated snapshot, effort none to max, Tier 1 500 RPM: https://developers.openai.com/api/docs/models/gpt-5.6-luna.
- Terms pages: DeepSeek Privacy Policy "Last Update" February 10, 2026, opt-out by email to privacy@deepseek.com; Z.ai Terms of Use "Last Update" April 14, 2026, API terms 3(b); OpenAI Services Agreement HTTP 403 to a fetch.

### Gaps (not sourced, left open rather than invented)

- OpenAI Services Agreement: no scripted fetch works (403 to curl on 2026-10-02 and to a fetch on 2026-10-03); the browser PDF in step 2 is the only path.
- Z.ai per-model concurrency: login-gated console (`https://z.ai/manage-apikey/rate-limits`, a redirect target of https://docs.z.ai/api-reference/rate-limit.md); read by hand in step 6.
- Z.ai `GET /api/paas/v4/models`: undocumented; `z01a` settles whether it exists.
- Chat Completions `max_completion_tokens` floor: not documented; `o01d` and `o06` send 1 and record whatever comes back. A floor of 16 on Responses `max_output_tokens` appears only in secondary sources (GitHub issues), not in OpenAI docs; `o05` sends 400 and is unaffected.
- Whether GLM's `max_tokens` also bounds reasoning tokens when thinking is enabled: undocumented. If it does not, `z03` could run to 131,072 output tokens, $0.58 at list price, the one call outside the bound above.
- Whether 520 simultaneous non-streaming requests overlap long enough to exceed DeepSeek's 500 concurrency: not knowable from docs; `d09` records the outcome either way.
- Minimum prepaid top-up for DeepSeek and Z.ai: not sourced.
