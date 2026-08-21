---
objective: "Two consecutive quality runs of the same models and prompts produce identical predicted labels and identical suite_accuracy, and every quality row records the exact sampling parameters that produced it."
status: in-progress
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Reproducible quality sampling and honest test coverage

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Close the 🔴 reproducibility gap in the quality CLI by pinning sampling per request for both models and recording those parameters in every row, then repair the three tests that stub out the code they claim to verify. |
| **Source** | `aidd_docs/tasks/2026_08/2026_08_21_full-branch-review/review.md` (review report, verdict `changes-requested`: 1 critical, 12 warning, 16 minor). This plan covers the 🔴 `fit` finding and the three 🟡 `functional` findings only. |

## Phases

| #   | Phase                                  | File                         |
| --- | -------------------------------------- | ---------------------------- |
| 1   | Deterministic sampling for both models | [`phase-1.md`](./phase-1.md) |
| 2   | Sampling provenance in every quality row | [`phase-2.md`](./phase-2.md) |
| 3   | Tests that exercise the real code path | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md` | `POST /completion` accepts per-request `seed` (default `-1`, random), `temperature` (default `0.80`), `top_k` (default `40`), `top_p` (default `0.95`), `presence_penalty` (default `0.00`). Per-request values override the server's command-line defaults. This is what makes the fix possible without touching `build_flags`. |
| `https://docs.mistral.ai/api/` | `POST /v1/chat/completions` accepts `temperature` (`number\|null`) and `random_seed` (`integer\|null`) — "The seed to use for random sampling. If set, different calls will generate deterministic results." The field is `random_seed`, not `seed`. |
| `llama-server.exe --help` (build b10537, the binary at `LLAMA_SERVER_PATH`) | Confirms `-s, --seed SEED` and `--temp, --temperature N` exist as server flags on this exact build. Recorded because it rules out a build-specific gap, not because the plan uses the flags. |
| `https://docs.mistral.ai/getting-started/models/models_overview/` | Dated Mistral Small ids and their deprecation dates. This page rendered the current id as `mistral-small-4-0-26-03`, which **does not exist on the API**. A live `GET /v1/models` on 2026-08-21 returned `mistral-small-2603` instead. The live endpoint is authoritative; this row is kept as the record of why docs alone were not enough. |

## Decisions

| Decision | Why |
| -------- | --- |
| Pin the quality run's sampling **per request**, in the `/completion` JSON body, rather than by giving the quality CLI its own llama-server flag set. | `server.build_flags` is the runtime harness's baseline contract: its plan requires the harness "reproduce, not rediscover" the validated command, and `tests/test_server.py:10-45` asserts the flag list matches exactly. Per-request parameters override server defaults (verified above), so the quality CLI gets deterministic sampling while `build_flags` stays byte-identical and the runtime benchmark keeps measuring the flag set it was validated against. A second flag set would have duplicated the baseline and invited the two copies to drift. |
| Explicitly send `presence_penalty: 0` (and disable `top_k`/`top_p`) on quality requests rather than relying on `temperature: 0` alone. | The server is launched with `--presence-penalty 1.5`. Penalties are applied to the logits *before* the sampler selects, so `temperature: 0` alone yields greedy selection over *penalised* logits — still deterministic, but a different and quietly wrong distribution that shifts as the prompt grows. Zeroing the penalty is what makes the score mean "the model's best answer" rather than "the model's best answer after a repetition penalty tuned for long-form generation". |
| Record the sampling parameters in every quality row instead of documenting them once in the code. | The user's decision is that greedy is the headline comparable score *and* that a sampled run must be addable later without a schema change. A row that carries its own `sampling` block is self-describing: a greedy row and a future sampled row can coexist in `quality.jsonl` and stay distinguishable without consulting git history. Runtime rows already carry their `flags` for the same reason. |
| Replace the `mistral-small-latest` alias with a dated model id, accepting that the client now needs a deliberate edit to move models. | `mistral_client.py:7-9` chose the alias so the client "does not need updating every time Mistral rotates its small-tier model". That directly contradicts `architecture.md:32`, which defines a reproducible quality score as *model* + prompt + seed: if the model behind the alias rotates between two runs, `random_seed` cannot make them agree and the objective fails for a reason no code in this repo can fix. Pinning the id converts a silent, untraceable change into an explicit, reviewable one — and because `quality_cli.py:71` already writes `mistral_client.MODEL` into every row, a dated id makes each cloud row self-describing at no extra cost. |
| No migration or archival step for existing quality rows. | `aidd_docs/results/quality.jsonl` does not exist — the quality CLI has never written real rows, so there is no non-reproducible data to invalidate. Recorded explicitly so a reader does not go looking for a migration that was deliberately not written. |
| Phase 1's reproducibility is graded by a real double run, not only by stubbed assertions. | The three 🟡 findings this plan also fixes are all "a test stubs out the thing it claims to verify". Proving reproducibility with mocks would repeat that mistake: mocks return what they are told to return, so identical stubbed outputs prove nothing about the sampler. Only two consecutive real runs agreeing can falsify the claim. |
