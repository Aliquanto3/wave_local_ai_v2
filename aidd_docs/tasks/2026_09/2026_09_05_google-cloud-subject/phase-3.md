---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: One live three-provider run, and the docs it proves

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── aidd_docs/results/quality.jsonl   ✏️ one live run's rows appended: local, mistral, google
├── CHANGELOG.md                       ✏️ + entry for the second cloud provider
├── .env.example                       ✏️ + GOOGLE_API_KEY line
├── docs/setup.md                      ✏️ + the three-provider run note (was "second run, set MISTRAL_API_KEY")
├── aidd_docs/memory/ecosystem.md      ✏️ + google as a second cloud provider, scope-3 estimate unchanged
└── aidd_docs/memory/codebase-map.md   ✏️ + google_client.py entry
```

## User Journey

```mermaid
flowchart TD
  A[Operator sets GOOGLE_API_KEY in .env alongside MISTRAL_API_KEY] --> B[uv run wave-local-ai-v2-quality]
  B --> C[Local batch runs and persists]
  C --> D[Mistral batch runs and persists]
  D --> E[Google batch runs and persists]
  E --> F[Three accuracy lines on stdout, one per provider]
  F --> G[Operator inspects quality.jsonl: 3 x 20 rows, distinguishable by provider]
```

## Test Scope

<!-- Required for every phase. Keep Setup, Happy path, any qualifying Edge cases, and any required Teardown in this one journey. -->

```mermaid
---
title: Test scope
---
journey
  section Setup
    GOOGLE_API_KEY and MISTRAL_API_KEY both set in .env on this machine => credentials ready for a live run: 5: cli
  section Happy path
    uv run wave-local-ai-v2-quality => three accuracy lines print, quality.jsonl gains 60 new rows across the three providers: 5: cli
    Every google row validates against row_contract and carries a non-null cost_total, version and api_version: 5: system
  section Edge case - reference comparison
    A prior google-provider reference exists (or is absent) => the batch verdict reads not_reproduced/reproduced or not_comparable honestly, never fabricated: 1: system
  section Teardown
    n/a -- an append-only results file needs no reset: 5: system
```

## Wireframe

<!-- UI phase only. No UI => omit the section, don't invent one. -->

## Tasks to do

### `1)` One live run on this machine

> Proves the whole path end to end against the real API, not stubs.

1. Confirm `GOOGLE_API_KEY` is set in `.env` (per the spike's confirmed free-tier key). Run `uv run wave-local-ai-v2-quality`.
2. Read back the newly appended rows in `aidd_docs/results/quality.jsonl`: confirm 20 local + 20 mistral + 20 google rows, each google row's `model_id == "gemini-3.5-flash-lite"`, `version` matching the catalog's current snapshot, `api_version == "v1"`, and a non-null `cost_total`/`list_price_input_per_million`.
3. Record the run's suite accuracy, cost and the verdict for all three providers in the phase's own evidence note (not committed to `quality.jsonl` beyond the rows themselves) — this is the "reference-comparison verdict" the story's Evidence section asks for.
4. If the run raises (`GoogleBlockedError`, rate-limit `GoogleRequestError`, or otherwise), record the exact failure and adjust phase 1/2 rather than silently retrying past it — a live failure here means the stubbed tests missed a real response shape.

### `2)` `CHANGELOG.md`

1. One entry: Google AI Studio (`gemini-3.5-flash-lite`) added as a second cloud subject to the quality CLI, alongside Mistral, under the same pinning discipline.

### `3)` `.env.example`

1. Add `GOOGLE_API_KEY=AIza-replace-me` beneath the existing `MISTRAL_API_KEY` line.

### `4)` `docs/setup.md`

1. Update the "second run, set `MISTRAL_API_KEY` first" section (or add a sibling one) to name `GOOGLE_API_KEY` too, and state plainly that an unset Google key skips that provider's rows rather than aborting the run — the one behavioral asymmetry with Mistral an operator needs to know before they wonder why `quality.jsonl` has no google rows.

### `5)` `aidd_docs/memory/ecosystem.md`

1. Extend the cloud-provider section to name Google as the second cloud subject, its pinned id, and that its Scope-3 energy/emissions estimate reuses the same `SCOPE3_WH_PER_TOKEN` formula as Mistral's (no new formula id).

### `6)` `aidd_docs/memory/codebase-map.md`

1. Add `google_client.py` next to the existing `mistral_client.py` entry, one line, same style.

## Test acceptance criteria

<!-- Each criterion is an observable behavior, not a command. -->

| Task | Acceptance criteria |
| ---- | -------------------- |
| 1    | The live run completes (or its failure is recorded and phases 1/2 are revised before this phase is marked done); `quality.jsonl` gains 60 rows in the local/mistral/google order, all `row_contract`-valid |
| 2    | `CHANGELOG.md` names the second cloud provider and its pinned id |
| 3    | `.env.example` documents `GOOGLE_API_KEY` |
| 4    | `docs/setup.md` tells an operator both env vars matter and that a missing Google key degrades to a skip, not a failure |
| 5    | `aidd_docs/memory/ecosystem.md` names Google as the second cloud subject |
| 6    | `aidd_docs/memory/codebase-map.md` lists `google_client.py` |

## Evidence (live run, 2026-09-05)

Scope change from the product owner, mid-phase: the cloud provider set
became configuration (`settings.QUALITY_PROVIDERS`), and both cloud
providers moved from hard-required/optional-skip to a uniform optional-skip
shape. See `feat(quality): make the cloud provider set configuration` on
this branch. This changes what this phase's live run can honestly claim
against the original three-provider acceptance text above.

**Mistral — skipped, not run.** Two live attempts (`uv run
wave-local-ai-v2-quality`, default `QUALITY_PROVIDERS`) both 429'd on the
very first Mistral call (`code 1300`, "Rate limit exceeded"), immediately
after a fresh ~1-minute local batch completed each time. The Mistral console
confirmed the cause: this project's workspace is on the Free plan, with
Billing usage at 0 — not a monthly-quota exhaustion, but the Free tier's own
rate floor, low enough that this suite's unpaced 20-item loop 429s before a
single completion lands. **Story 5** ("a rate-limited run persists, resumes
and never re-pays") is the tracked fix; until then, an operator on a Free
Mistral workspace should expect `mistral skipped: ...` on every run and set
`QUALITY_PROVIDERS=local,google` (or add a Mistral payment method) rather
than treat it as broken.

**Google — succeeded after adding request pacing.** The first
`QUALITY_PROVIDERS=local,google` attempt also 429'd
(`RESOURCE_EXHAUSTED`, `generate_content_free_tier_requests`, limit 15):
`google_client`'s design costs two requests per suite item
(`check_context_fits` + `complete_prompt`) plus two for
`check_model_available`, so a 20-item suite fires ~42 calls — well over
Google's 15 requests/minute free-tier cap even though "20 items" reads as
comfortably under it. Fixed in-scope with `GOOGLE_REQUEST_PACING_S` (4.5s
between every Google request in `quality_cli`, mocked to a no-op in tests):
a second attempt completed clean, `google accuracy=1.00`.

**Run recorded** (`run_id=70b654faf73b49faae9012b6515e987b`,
`QUALITY_PROVIDERS=local,google`): 20 local + 20 google rows, all
`row_contract`-valid (checked programmatically). Local: accuracy 0.80,
verdict `reproduced` (against the prior local reference), `cost_total≈0.000274`
(kWh-derived). Google: accuracy 1.00, verdict `not_comparable` (no prior
google-provider reference exists yet — honest, not fabricated, per the Test
Scope's own edge case), `cost_total≈0.000372` (list-price-derived),
`model_id=gemini-3.5-flash-lite`, `model_version=gemini-3.5-flash-lite`,
`api_version=v1`.

**Tech debt — three noise run_ids in the live store.** The two Mistral 429
attempts and the one unpaced-Google 429 attempt each still ran and persisted
a full local batch before failing (by design: local is written before any
cloud call). These three run_ids carry only local rows and should be
excluded from any future local-provider median/reproduction analysis over
`aidd_docs/results/quality.jsonl` — they are real local runs, just not part
of a completed three-provider comparison:

- `3b685236fe70455dab1f65cbb5a68078`
- `a9529fca36234085bb4e31bda576a52d`
- `fbc4d63b6f3f4960a8d88dfdfd377ed5`
