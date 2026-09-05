# Decision: live three-provider evidence

## Setup

`.env` already carried `MISTRAL_API_KEY` and `GOOGLE_API_KEY`; `QUALITY_PROVIDERS`
was unset (default `local,mistral,google`). Port 8080 free, GPU idle.

```
uv run wave-local-ai-v2-quality
```

## Result: Mistral still 429s under 1.1s pacing, exit 0, local + google succeed

Full stdout:

```
model=Qwen3.6-35B-A3B provider=local accuracy=0.80
model=gemini-3.5-flash-lite provider=google accuracy=1.00
```

Full stderr:

```
[codecarbon INFO @ 18:48:11] offline tracker init
[codecarbon WARNING @ 18:48:11] Multiple instances of codecarbon are allowed to run at the same time.
mistral skipped: retry budget exhausted after 4 retries
```

Exit code: `0`. `aidd_docs/results/quality.jsonl` gained 40 new rows for this
run_id (20 `local`, 20 `google`) — zero `mistral` rows, matching the retry
budget's own exhaustion (`CLOUD_RETRY_MAX_ATTEMPTS` default `4`): the whole
batch was retried until the shared budget ran out, then skipped, never
partially written.

## Reading

The 1.1s Mistral pacing this plan defaults to (`DEFAULT_MISTRAL_REQUEST_PACING_S`)
is not enough on its own to keep this project's Mistral Free-tier workspace
under its rate floor for a 20-item burst, even with 4 retries and
exponential backoff behind it. This is not evidence the retry/pacing layer
is broken — Mistral's own `RetryableRequestError` correctly classified every
429 as retryable, the shared `RetryBudget` correctly enforced one ceiling
across the whole batch, and the CLI's existing "skip, don't abort" contract
held exactly as designed: local and google rows were not lost to Mistral's
failure. It is evidence that 1.1s is too tight a steady-state interval for
this workspace's actual Free-tier ceiling, the same way the plan's own Risks
table already flagged 4.1s as untested margin against Google's confirmed-safe
4.5s.

No Google 429 was observed at 4.1s pacing in this run (`accuracy=1.00`,
20/20, no retries recorded on any google row) — one live data point in favor
of the narrower interval holding for Google specifically, though a larger N
would be needed to call it confirmed the way 4.5s was.

Per the story's own instruction (plan.md's phase-4 task 1.4), this is
recorded as evidence, not acted on: `QUALITY_PROVIDERS`'s documented default
(`local,mistral,google`) is left exactly as it is — Mistral is still expected
to be attempted, still expected to sometimes 429 out on this workspace's Free
tier, and still expected to be skipped rather than abort the run when it
does. A future increment could raise `MISTRAL_REQUEST_PACING_S` past 1.1s if
this recurs; that is a config change an operator can make today without a
code change, not something this plan silently walks back.
