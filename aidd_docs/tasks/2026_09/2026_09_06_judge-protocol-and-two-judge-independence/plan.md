---
objective: "A judged quality row cannot be written unless it names each judge's dated model id, the language variant and content hash of the prompt that was issued, the rubric version applied, each judge's raw returned text and parsed score, the judge-call egress and token cost, and either a named agreement statistic over two judges of different model families or an explicit single-judge flag."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A judge call carries its versioned prompt and rubric, and two judges of different families or an honest single-judge flag

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Build the judge machinery as three provider-agnostic modules (`judge_protocol.py`, `judge.py`, `agreement.py`) plus one provider-binding module (`judge_backends.py`), a `family` attribute on `roster.py`, a per-suite contested threshold in `settings.py`, and a conditional judged-row block on `row_contract.py` under one `SCHEMA_VERSION` bump. Every test runs against stubbed HTTP; no live judge call and no CLI wiring — the probe and the live two-path proof are story 6. |
| **Source** | `aidd_docs/backlog/stories/a-judge-call-carries-its-versioned-prompt-and-rubric.md` (order 3) and `aidd_docs/backlog/stories/two-judges-of-different-families-or-an-honest-single-judge-flag.md` (order 4), planned as one increment; authority `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` Methodology 10 and 11, and `aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md` |

## Phases

| #   | Phase                                                        | File                         |
| --- | ------------------------------------------------------------ | ---------------------------- |
| 1   | Versioned judge prompts and rubrics, the judge call, the contract bump | [`phase-1.md`](./phase-1.md) |
| 2   | Agreement statistics and the contested rule                   | [`phase-2.md`](./phase-2.md) |
| 3   | Independence by family, refusals, egress and judge cost       | [`phase-3.md`](./phase-3.md) |
| 4   | CHANGELOG and memory                                          | [`phase-4.md`](./phase-4.md) |

## Resources

<!-- External sources only (URLs, docs), not code files. Omit if none consulted. -->

| Source | Verified          |
| ------ | ----------------- |
| https://en.wikipedia.org/wiki/Cohen%27s_kappa | The weighted form is `κ = 1 − ΣΣ W(i,j)·Õ(i,j) / ΣΣ W(i,j)·Ẽ(i,j)`, with `Õ(i,j) = O(i,j)/N`, `Ẽ(i,j) = p̂(i,·)·p̂(·,j)` from the two raters' marginals, and quadratic weighting `W(i,j) = (i−j)²`. Kappa is mathematically undefined only when the denominator is zero. Confirms that dividing the weights by `(k−1)²` is optional: it scales numerator and denominator alike and cancels out of the ratio. |
| https://mistral.ai/pricing/api and `aidd_docs/memory/external/google-ai-studio-api.md` | Already snapshotted into `cost.PRICE_TABLES` (`mistral-small-2603`, `gemini-3.5-flash-lite`, both `retrieved_at: 2026-08-27`). Judge-call costing reuses those tables; no new price retrieval and no new pricing source is introduced by this increment. |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision   | Why   |
| ---------- | ----- |
| The 1-5 ordinal rubric publishes quadratic-weighted Cohen's kappa with exact-match and within-one rates beside it, **not** the epic's "absolute score delta" and not the PRD's literal "absolute score delta for a numeric one". | A direct conflict between three authorities, resolved in favour of the story, which is the most recent and the most specific: story 4's acceptance names quadratic-weighted kappa explicitly, and the user restated it as a decision already taken. The epic's own Dependencies table anticipated the reversal ("whether a weighted kappa is added at suite level is deferred to the first suite holding enough judged items"). The PRD's intent survives because the raw agreement figures published beside kappa — exact-match rate and within-one rate — *are* the absolute-delta information, at a finer grain than a single mean delta. **The epic's decision row and the PRD's criterion 10 wording now disagree with shipped behavior and must be corrected by whoever closes the epic**; this plan does not edit the backlog. |
| Judge fields are required **conditionally**: a quality row carrying any judge field must carry all of them; a row carrying none validates exactly as it does today. | Story 3 asks for two things that are in tension read literally — "extend the quality row's required-field list additively" and "an existing deterministic row keeps validating unchanged". A conditional set satisfies both, and gives story 4's "carrying neither an agreement figure nor the single-judge flag" refusal a natural home: the same gate that knows a row is judged is the one that knows what a judged row owes. An unconditional set would force `quality_cli.py` to write a dozen null judge keys onto every deterministic classification row, which is CLI wiring this increment explicitly excludes. |
| One `SCHEMA_VERSION` bump for the whole increment (`"8"` → `"9"`), declared in phase 1, covering both stories' fields. | The two stories ship together as one contract change. Bumping in phase 1 and again in phase 3 would publish an intermediate `"9"` that no row ever carries and that no reader can ever encounter — a version comment describing a shape that never existed. Phase 1 declares the complete judged-field set; phase 3 adds the *rules* over those fields (family collision, neither-statistic-nor-flag) without touching the version. |
| `cost_total` on a judged row stays the subject generation's cost. The judge calls' tokens and cost land in the row's cost block as their own named `judge_cost` record, per judge provider. | The user asked for judge tokens to join the row's cost block; the epic recorded whether they are *summed into* `cost_total` as an open decision belonging to the row epic (criterion 16). Naming them separately does both: the figures are on the row, in the cost block, recomputable per provider at that provider's own rates — and the summing decision stays open rather than being made by silent addition. Summing a Google judge's tokens into a Mistral subject's `cost_total` would also break the existing contract rule that a non-null `cost_total` is recomputable from the row's own `list_price_*` rates. |
| A fourth new module, `judge_backends.py`, holds the two provider bindings; neither story lists it. | Story 3's acceptance forbids `judge.py` from importing a single provider's error type, and the pacing/retry layer needs exactly that type to decide `is_retryable`. Something has to bind them. Putting it in `quality_cli.py` would drag CLI wiring into an increment that excludes it; putting it in `judge.py` would break the acceptance criterion; leaving it in the tests would mean story 6 finds no wiring to call. One named seam module is the smallest honest answer, and it is the only module in this increment that imports `mistral_client` or `google_client`. |
| The project's zero-variance kappa rule is deliberately stricter than the textbook undefined condition, and the two cases carry different reasons. | Mathematically kappa is undefined only when `ΣΣ W·Ẽ = 0` — which for unweighted kappa needs *both* raters constant on the same category. One constant rater and one varying rater yields a defined `κ = 0`, which is precisely the "reads as chance-level disagreement" misreading story 4 forbids. So `agreement.py` returns null with `zero_variance` when either judge's scores are constant, and null with `zero_expected_disagreement` on the mathematical case, rather than collapsing both into one reason or letting the first fall through to `0`. |
| `family` is an **optional** field on a roster entry, resolved through `roster.family_of` with an in-code declaration as the fallback. The shipped `aidd_docs/roster/models.json` is not edited. | Story 4 asks for the declaration to be "written as the seam it is, not duplicated": `family_of` prefers an entry's own `family` when Methodology 13's roster carries one, and falls back to the code declaration until it does. Making it required, or editing the shipped roster now, would force a `roster_version` bump that every published row and every reference-bundle test compares against — a change to published evidence for no behavioral gain in this increment. |
