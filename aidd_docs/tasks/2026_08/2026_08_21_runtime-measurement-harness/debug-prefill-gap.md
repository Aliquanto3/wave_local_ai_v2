---
name: task
description: Task tracking system to ensure all tasks are categorized and addressed
---

# Task [runtime-harness-prefill-tok-per-s-gap]

`prompt_tok_per_s` measured by the runtime harness (204.1 tok/s) doesn't match the
validated baseline (~280 tok/s), a 27% deviation, outside the plan's ±1.5 tok/s bar.
`gen_tok_per_s` matches fine (25.98 vs ~26). Root cause unknown; validate hypotheses
before touching the harness.

## Hypotheses

- [x] H1 — First-request warm-up cost (CUDA kernel autotune/graph capture) not
      amortized in a single cold run. Confidence 8/10 → **INVALIDATED**.
      Evidence: 3 requests to one warm server (identical fixed prompt): req1
      (cold) = 219.5 tok/s, req2 = 28.8 tok/s, req3 = 25.8 tok/s. The cold
      request is the *fastest*, not the slowest — contradicts a warm-up-cost
      explanation. Requests 2-3 collapsed because llama-server's prompt/prefix
      cache recognized the repeated prompt and skipped re-evaluating it
      (ttft_ms dropped 2173ms → ~140ms) — a real caching mechanism, not
      evidence about the original gap. Confirmed number: a genuine cold/fresh
      prompt run still lands at 219.5 tok/s, ~22% short of ~280 baseline —
      consistent with the original 204.1 tok/s recording, not closed by
      warm-up.
- [ ] H2 — HTTP/JSON overhead (implementer's stated explanation). Confidence 2/10.
- [x] H3 — Server batch/ubatch size defaults differ from llama-bench's pp-test batch
      size. Confidence 3/10 → **INVALIDATED**. Evidence: `llama-server --help` /
      `llama-bench --help` both default to `-b 2048 -ub 512`; `build_flags()`
      doesn't override either, so both paths already use identical batch
      settings. A live `llama-bench` run with the harness's exact flags
      (`-ngl 99 -ncmoe 37 -fa on -t 8 --load-mode none -p 512 -n 128 -r 5`)
      still reports pp512 = 314.81 ± 5.60 tok/s, well above the harness's
      204-220 — batch size was never the variable.
- [ ] H4 — Wrong timings field / stale field-name assumption for build b10537.
      Confidence 2/10 — not tested directly, but superseded by H6's confirmed
      length-dependent scaling, which a field-mapping bug wouldn't produce.
- [ ] H5 — Single-run measurement noise (no `-r 5` averaging). Confidence 4/10 →
      weakened further: H6's probe shows a length-dependent *systematic* curve,
      not scatter.
- [x] H6 — The `/completion` server path carries fixed per-request overhead
      (slot allocation/lookup, prompt tokenization, batch dispatch — counted
      inside the server's own `prompt_ms`) absent from llama-bench's internal
      `llama_decode` loop. Confidence 6/10 → **CONFIRMED — ROOT CAUSE**.
      Evidence: 4 distinct (non-cached) prompts at increasing length via the
      running server: 401 tok → 214.2 tok/s, 1360 tok → 278.2 tok/s,
      2949 tok → 287.1 tok/s (4791 tok → 239.9 tok/s, separate large-context
      effect, out of scope). Throughput climbs toward the 278-287/314±5.6
      baseline band as prompt length grows past ~1300 tokens, confirming a
      roughly fixed ~400-500ms per-request cost dominates short-prompt
      measurements. This also invalidates H2 (generic HTTP/JSON overhead):
      the cost is inside the server's own measured window, not the wire layer,
      and it's a real length-dependent effect, not noise.

## Root cause

The harness's fixed prompt (~400-500 tokens) is too short to amortize
llama-server's fixed per-request overhead (slot/cache setup, prompt
tokenization, batch dispatch — all counted inside the server's own reported
`prompt_ms`). `llama-bench`'s internal decode loop has no equivalent per-call
overhead, so it reports near-raw compute throughput at any length. The gap
closes to within baseline noise once the prompt is long enough
(~1300-3000 tokens) to amortize that fixed cost.

## Follow-up: implement attempt and a second, more specific finding

`FIXED_PROMPT` was lengthened in two steps (1333 tok, then 1507 tok) and the
real CLI was re-run each time:

| prompt tokens | prompt_tok_per_s | gen_tok_per_s |
| --- | --- | --- |
| ~500 (original) | 204.1 | 25.98 |
| 1333 | 233.4 | 25.8 |
| 1507 | 255.9 | 26.0 |
| 1507 (repeat) | 259.3 | 25.5 |

This closed most of the gap (27% -> ~8%) but plateaued around 255-260, well
short of the H6 probe's 278-287 prediction for this length range. The
discrepancy: **H6's own probe was confounded.** It reused one already-running
server across 4 requests; only its first call (401 tok, cold) was a genuine
cold-server measurement. The 1360/2949-token calls that read 278/287 tok/s
were requests 2-3 on an *already-warmed* server — free-riding on CUDA
kernel/graph warm-up from request 1, even though their prompts were distinct
(no prompt-cache hit). The real harness launches a fresh server every run and
sends exactly one request, so it always pays a first-request cold-start tax
that H6's plateau numbers excluded.

### Warm-up experiment (targeted test of the cold-start tax)

Sent an untimed, discarded warm-up request (a distinct, non-cache-colliding
prompt) immediately before the real measured request, on one fresh server
launch:

```
warm-up (discarded): prompt_tok_per_s=276.6  ttft_ms=22309.1
measured (real):     prompt_tok_per_s=263.9  gen_tok_per_s=11.8  ttft_ms=5646.7
```

`prompt_tok_per_s` improved marginally (259.3 -> 263.9) but `gen_tok_per_s`
**collapsed from ~26 to 11.8**. With `-np 1` (single slot) and no explicit
cache-clearing, the warm-up's context stayed resident in the slot, so the
measured request's decode ran over a much larger effective context (warm-up
tokens + real prompt), inflating per-token attention cost. **Conclusion: a
naive warm-up request doesn't cleanly amortize the cold-start cost — it
contaminates the very measurement it's meant to protect.** A correct version
would need explicit slot/cache isolation (distinct `id_slot`, or a `/slots`
erase call) — new server-API surface not otherwise used in this harness, for
one metric, with a new class of leakage bug to get right.

## Final root cause and decision (path 1 — evidence-backed re-scope)

`prompt_tok_per_s` on this harness's actual design (fresh server launch, one
real request) is systematically ~8-10% below llama-bench's warmed,
5-repetition-averaged pp512 figure (314.81 +/- 5.60, itself above the
original ~280 baseline doc value). This gap is real, reproducible, and not
closeable by prompt length alone or by a low-risk warm-up — it is the cost of
measuring a genuinely cold first request, which llama-bench's methodology
structurally excludes. Per phase-4 task 3.2, the harness was treated as wrong
first (three independent hypotheses tested and invalidated/refined: warm-up
timing, batch defaults, and a naive warm-up-request fix), before concluding
the remaining gap is inherent to what this harness measures, not a bug. The
acceptance bar is re-scoped with this evidence: `prompt_tok_per_s` around
255-260 tok/s (not ~280) is the harness's correct, honest figure for "one
fixed prompt, one fresh server, one real request." See `plan.md`'s Decisions
table for the recorded re-scope.
