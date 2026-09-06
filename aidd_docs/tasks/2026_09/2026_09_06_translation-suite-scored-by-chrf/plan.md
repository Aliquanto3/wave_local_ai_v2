---
objective: "A 21-item hand-written translation suite is scored deterministically by an in-repo chrF against the same local SLM and cloud subjects as classification, publishing a graded score the row itself lets an auditor recompute."
status: implemented
---

# Plan: Translation scoring extends deterministic coverage, scored by chrF

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A second use case scores deterministically on the proven machinery, with a graded metric the exact-match row shape cannot carry as-is. |
| **Source** | `aidd_docs/backlog/stories/translation-scoring-extends-deterministic-coverage.md` (story, written 2026-08-21, pre-methodology), arbitrated against `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` Benchmark Methodology 2-5 and 9, and the shipped code. |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The chrF metric, alone and provable | [`phase-1.md`](./phase-1.md) |
| 2   | The translation suite and its graded scorer | [`phase-2.md`](./phase-2.md) |
| 3   | The graded row, the verdict, and the `--suite` seam | [`phase-3.md`](./phase-3.md) |
| 4   | The live run and the record it leaves | [`phase-4.md`](./phase-4.md) |

## Divergences from the story

The story predates the methodology epic. Where it conflicts with the PRD or the shipped code, the plan follows the PRD and the code and records the conflict here.

| # | The story says | What is built instead | Why |
| - | -------------- | --------------------- | --- |
| D1 | "the same local SLM and **cloud model**" — one cloud subject | Every provider in `QUALITY_PROVIDERS` (today `local`, `mistral`, `google`) | The Google subject landed after the story was written (`quality_cli._CLOUD_PROVIDERS`). Restricting the translation suite to one cloud subject would build a narrower comparison than the classification suite already publishes. |
| D2 | The result appears "alongside classification **and rewriting** results" | Alongside classification only | The rewriting suite is a later story in the same epic and does not exist. The acceptance criterion is met for the two suites that exist; nothing fabricates a rewriting row. |
| D3 | Silent on suite size, language mix, provenance, prompt-set hash, generation caps | The suite passes `suite_gate.gate_suite` and carries `suite_id` / `suite_version` / `prompt_set_hash` / `max_output_tokens` / `stop_sequences` / `context_length` on every row | Methodology 2-5 and the shipped `suite_gate.py` post-date the story. This is scope the story does not mention and the PRD requires. |
| D4 | "produces a deterministic quality score" — assumed to fit the existing row | `SCHEMA_VERSION` `"9"` → `"10"`, adding a conditional graded block; `correct`, `suite_accuracy` and `language_breakdown` are null on a translation row | `correct` is a boolean and `suite_accuracy` is an exact-match rate. A chrF mean is neither. Writing one into the other would publish a graded score under an exact-match name. See Decisions. |
| D5 | Assumes the verdict machinery works unchanged | `verdict.quality_verdict` decides on `item_score` when `predicted_label` is null on both sides | It compares `predicted_label` today. Every translation row's is null, so two runs would come back `reproduced` off two sets of nulls — the exact failure `judge_probe.py` documents and routes around. Methodology 8 already allows it: "identical per-item predicted labels **or scores**". |
| D6 | Silent on `--resume` | `results.resume_skip_reason` gains a `task_suite` filter | It keys on `(run_id, provider)` alone, so `--resume <classification-run-id> --suite translation` would find a complete classification batch and skip a translation batch that was never run. |

## Assumptions

Resolved from the source where possible, stated here where the source could not settle them.

- **"the three directions implied by EN/FR/DE tags"** is read as one direction per source language, arranged as a cycle: `en→fr`, `fr→de`, `de→en`, seven items each, 21 in total. Every language appears once as source and once as target, and `suite_gate`'s ≥25%-per-language rule is satisfied at 33% each.
- **`language` tags the source language** — the language of the text handed to the model, matching what `language` already means on a classification item and on a probe item. The target is a new item field, `target_language`.
- **21 items, not 30.** The story asks ≥20 and the gate requires ≥20. At seven per language all three per-language cells are marked indicative (`suite_gate.MIN_PER_LANGUAGE_CELL_ITEMS` is 10) — the same posture the shipped classification suite has for its `fr` and `de` cells. Clearing that mark needs 10 per direction, i.e. nine more hand-authored reference translations whose quality nobody in-project can natively verify for German; the mark is the honest report of a real limitation, and inflating the set to remove it would trade a visible weakness for an invisible one. A later story adds them if a native reviewer is available.

## Resources

| Source | Verified |
| ------ | -------- |
| `https://raw.githubusercontent.com/mjpost/sacrebleu/master/sacrebleu/metrics/chrf.py` | The reference chrF algorithm. Defaults `CHAR_ORDER = 6`, `WORD_ORDER = 0`, `BETA = 2`, `eps_smoothing = False`. With eps smoothing off — the default — per-order precisions and recalls are averaged over the *effective* orders (those where both hypothesis and reference have at least one n-gram), and one F-score is computed from the two averages, not per order then averaged. Result scaled `×100`. |
| `https://raw.githubusercontent.com/mjpost/sacrebleu/master/sacrebleu/metrics/helpers.py` | `extract_all_char_ngrams`: with `include_whitespace=False` (the chrF default) the line is collapsed with `''.join(line.split())` before n-grams are cut; no lowercasing unless asked. Match counts per order are the multiset intersection of the two `Counter`s. |
| Popović 2015, "chrF: character n-gram F-score for automatic MT evaluation", WMT15 | The metric's original definition, which the sacreBLEU default reproduces. |

## Decisions

| Decision | Why |
| -------- | --- |
| chrF is implemented in-repo (`chrf.py`), not taken from `sacrebleu` | The algorithm is ~60 lines of `Counter` arithmetic with no I/O and no randomness. `sacrebleu` pulls `numpy`, `regex`, `portalocker`, `tabulate`, `colorama` and `lxml` into a project whose CI runs `scripts/audit_dependencies.py` against every transitive dependency and whose reproduction story asks a client engineer to install the tree. Paying six packages for sixty lines fails that trade. sacreBLEU's own source stays the spec (Resources above), so the in-repo implementation is checkable against it rather than a private variant. |
| A graded score is a **conditional row block** (`row_contract.GRADED_FIELDS`), not an overload of `correct` / `suite_accuracy` | Exactly the shape `JUDGED_FIELDS` already established at `SCHEMA_VERSION` `"9"`: required only on a row carrying any of it, so every existing classification row validates unchanged and no reference bundle is regenerated. The alternative — a chrF mean in `suite_accuracy` — publishes a character-n-gram F-score under the name "accuracy" in the same store as a real exact-match rate. |
| The graded block carries `reference_output` beside the row's existing `subject_output` | chrF is deterministic and offline, so a row carrying both texts and its metric parameters lets an auditor recompute the score with sacreBLEU and catch us. That is Methodology 16's "a row carrying a derived value also carries what it was derived from", applied to a score instead of a cost. |
| Scores are published on `0..1`, not sacreBLEU's `0..100` | One store already reports `suite_accuracy` on `0..1`; two score scales side by side in one file is a reading trap. The scale is declared on the row (`metric_params.scale`) rather than left to be inferred. |
| `--suite` is a two-entry dispatch table inside `quality_cli.py`, not a registry module | The full suite registry belongs to the use-case epic (`no-use-case-is-silently-absent.md`). This is the minimum the CLI needs to stop being hard-wired to one suite: a `SuiteSpec` holding the items, the identity, the caps and the batch scorer, and a literal dict of two. Same discipline `_CLOUD_PROVIDERS` follows. |
| No text extraction from the completion before scoring | The classification path extracts (`normalize_label` finds the first matching token) because it looks for a member of a closed set. A translation has no closed set to search, and any extraction rule — strip a preamble, take the last paragraph — is a scoring choice invented here that sacreBLEU would not reproduce. The raw completion is scored after whitespace normalisation only, and a model that answers with "Sure! Here it is:" is genuinely worse at the instruction and its score says so. |

## Risks

- **Reference quality bounds every score.** chrF against a single reference penalises a valid alternative translation. The German references especially cannot be natively reviewed in-project. The suite module states this in its docstring and `docs/` repeats it; the score is defensible as a *comparison between models on identical references*, never as an absolute translation-quality figure.
- **The live phase depends on providers.** Google's free tier is paced at `4.1 s` between requests and each item costs two requests: 21 items ≈ 3 minutes. The Mistral workspace has 429'd a 20-item burst before; if it does not answer, phase 4 ships local + google and the record says which provider was absent and why, rather than blocking.
- **`unparseable` is structurally unreachable on this suite**, so the taxonomy key stays at 0. That is stated on the suite, the way `judge_probe.py` states its own two unreachable keys, rather than left to look like a suite that never fails to parse.
