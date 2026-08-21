---
objective: "A rotated, removed or deprecated Mistral model id is reported before the local suite runs, so a quality run that cannot finish costs no llama-server lifecycle."
status: in-progress
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Pre-flight the Mistral model id

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Check `mistral_client.MODEL` against the live catalog in `quality_cli._run`, beside the existing `MISTRAL_API_KEY` check, so an absent id fails at second 0 and a deprecated-but-live id warns with its retirement date and replacement. |
| **Source** | `aidd_docs/tasks/2026_08/2026_08_21_quality-sampling-reproducibility/review.md`, the 🟡 `fit` finding: pinning `MODEL` to a dated id made rotation a hard failure at the first cloud request, which lands after the full local suite (~49s in the recorded 21:55:11-21:56:00 run), while `_run` already pre-flights the API key for exactly this reason. |

## Phases

| #   | Phase                                    | File                         |
| --- | ---------------------------------------- | ---------------------------- |
| 1   | Catalog check in the Mistral client      | [`phase-1.md`](./phase-1.md) |
| 2   | Pre-flight before the local suite        | [`phase-2.md`](./phase-2.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| Live `GET https://api.mistral.ai/v1/models` (2026-08-21, HTTP 200) | The response is `{"object": "list", "data": [...]}` with 56 entries. Each entry carries `id`, `deprecation` (an ISO-8601 timestamp or `null`), `deprecation_replacement_model`, `aliases`, `capabilities`, `max_context_length`, `type`, `owned_by`. This is the shape the check must parse. |
| Same call, `mistral-small-2603` entry | Present, `deprecation: null`, so the pinned id is live and carries no retirement date today. Its `aliases` list currently includes `mistral-small-latest` — the concrete demonstration of the earlier decision to abandon that alias: the two resolve to the same model *right now*, and nothing in the API promises they still will next month. |
| Same call, deprecation survey | 6 of the 56 models carry a deprecation date, all `2026-08-31T12:00:00Z` (ten days out), each naming a `deprecation_replacement_model`. Deprecation is a live, near-term event on this API, not a hypothetical, which is why the check reads the field rather than only testing membership. |
| `GET https://api.mistral.ai/v1/models` with an invalid bearer token | HTTP 401 with body `{"detail":"Invalid API Key"}`. The pre-flight therefore also catches a present-but-wrong key, which the existing empty-string check cannot. |

## Decisions

| Decision | Why |
| -------- | --- |
| An absent id raises; a deprecated-but-listed id warns and the run continues. | A deprecation date in the future means the model still answers: failing on `deprecation != null` would break a working run up to the retirement date, trading one real failure mode for a self-inflicted one. The operator needs the actionable half — the date and `deprecation_replacement_model` — without losing the run that is currently fine. Absence is different: the next cloud request is guaranteed to fail, so raising early is strictly cheaper than raising late. |
| The check lives in `mistral_client.py`, not in `settings.py`. | `load_settings` is offline by contract: it reads env vars and stats paths, and `__init__.py`'s runtime harness calls it with no cloud credential configured at all (`settings.py:33-35` says so explicitly). Putting a network probe there would place a Mistral dependency on the runtime benchmark's startup path, which measures a local model and must not care whether a cloud API is reachable. `mistral_client.py` already owns every Mistral HTTP call and its error type. |
| The pre-flight is accepted as a new network round trip on every quality run, and as a failure that can now abort a run at second 0. | It loses nothing that was not already lost. `_run` calls `_score_and_write` only after **both** suites return (`quality_cli.py:88-101`), so a cloud-side failure today already discards the local suite's completions and writes zero rows. Moving the failure earlier changes only what it costs to discover, from a full llama-server lifecycle plus 10 completions down to one GET. |
