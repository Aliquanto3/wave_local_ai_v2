---
objective: "The registry holds `output_compressed` v1 with a declared per-family applicability; a quality row records a no-op where it does not apply; a run of either variant keeps the item set and everything but the prompt; and one laptop baseline-versus-variant pair is compared through the existing paired test."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: The terse-output variant runs every item and meets baseline in a paired test

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `output_compressed` v1 (an appended terse-output instruction, applicable to `classification` only, reason in the entry) in `prompt_variants.py`; `apply_variant` takes the item's task family and reports a no-op; quality rows carry `prompt_variant_noop` from schema "27", checked by the gate; `wave-local-ai-v2-quality --prompt-variant`; invariance, no-op, unparseable and comparison tests; one laptop pair compared with `wave-local-ai-v2-compare --dimension prompt_variant` |
| **Source** | `aidd_docs/backlog/stories/the-terse-output-variant-runs-every-item-and-meets-baseline-in-a-paired-test.md`; parent epic `the-engine-and-the-prompt-variant-are-measured-not-assumed.md`; night-run owner decision D2 (local only) |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Registry entry, applicability and the no-op row field (schema "27") | [`phase-1.md`](./phase-1.md) |
| 2   | `--prompt-variant` on the quality CLI; invariance, unparseable and comparison tests | [`phase-2.md`](./phase-2.md) |
| 3   | Docs and the laptop campaign cell pair with its comparison record | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Applicability is an optional `applies_to` list of task families (`task_suite` values) plus `applicability_reason` inside the hashed definition; a definition without `applies_to` applies to every family. `baseline`'s definition is untouched, so its hash and version stay. | Acceptance line 2 wants the declaration and its reason in the entry; editing `baseline` would force a version bump with no change in behavior. |
| `output_compressed` v1 applies to `classification` only; `translation` records a no-op. Reason: a translation's length is fixed by its source and its reference, so a terse instruction can only remove content chrF requires; classification's single-label answer has an exact-match test behind it. | Story "So that": "on a task family with a test behind it". |
| Transformation `append_instruction`: authored prompt + `"\n\n"` + the instruction. The wording is the definition. | Leaves the authored prompt intact and visible in `prompt_before_template`; the change is exactly the appended text. |
| `apply_variant(variant, authored_prompt, task_family)` returns `VariantApplication(prompt, noop)`; `task_family=None` (the runtime fixed prompt) applies only a variant with no `applies_to`. | One place decides both the prompt and the no-op, so a writer can never publish one without the other. |
| `prompt_variant_noop` (bool) required on quality rows only, from schema "27"; the gate checks it equals the registry's answer for the row's `task_suite`, and, whenever the authored text resolves, that `prompt_before_template` equals the variant applied to it (baseline keeps refusing an unresolved text). Runtime rows are unchanged. | Runtime rows run one fixed prompt under `baseline` and belong to no task family; the gate generalizes the existing baseline check instead of adding a parallel one. |
| `prompt_variant_noop` joins `comparison.py`'s per-item exempt fields. | It is derived from the variant and the suite; a translation pair would otherwise report it as a confound beside the declared dimension. |
| The variant is chosen by a `--prompt-variant ID[@VERSION]` CLI flag (default `baseline`, latest version), replacing the module constant `PROMPT_VARIANT_ID`. | The evidence needs both variants on one suite; the campaign check already validates the chosen variant against the declaration. |
| Local run under a campaign declared in the task's `evidence/` (`CAMPAIGNS_DIR`), every results path in `evidence/`; no judge, no cloud (D2). | Brief: nothing lands in tracked stores. |
| `comparison.py` exempts `score_interval` from the differing-field set (outside this story's listed code). | The first laptop pair published as an observation with confound `score_interval`: a batch interval is an outcome of the scores, so any two batches that score differently differed on it and no real pair could ever be a test. Without the fix acceptance line 4 could not hold on real rows. |
| The evidence fiche was not kept in `evidence/`; rows validate against the byte-identical `73ec536e...` fiche already tracked by the named-run-profiles evidence. | A fiche JSON trips the detect-secrets hex scan and cannot carry an inline pragma. |
