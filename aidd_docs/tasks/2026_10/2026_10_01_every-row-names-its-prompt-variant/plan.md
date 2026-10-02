---
objective: "Every quality and runtime row names the prompt variant and variant version it ran under and carries the prompt as the variant left it, and the writer gate refuses a row missing either field, naming an unregistered variant or version, or claiming `baseline` while its pre-template prompt differs from the item's authored text."
status: implemented
---

# Plan: Every row names its prompt variant, and a baseline row carries the authored prompt

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A versioned, hash-checked prompt variant registry holding `baseline` v1, one application function ahead of every engine's templating, three new row fields on both row kinds, and a gate that checks the `baseline` claim against the authored text |
| **Source** | `aidd_docs/backlog/stories/every-row-names-its-prompt-variant-and-a-baseline-row-carries-the-authored-prompt.md` |

## Phases

| #   | Phase                                                         | File                         |
| --- | ------------------------------------------------------------- | ---------------------------- |
| 1   | The variant registry, its load-time hash check, and the one application function | [`phase-1.md`](./phase-1.md) |
| 2   | Row fields, gate rules and schema "14", applied on every writer path, with the gate evidence | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The registry is a Python module, `prompt_variants.py`, beside `classification_suite.py` and `translation_suite.py`, not a JSON file under `aidd_docs/`. Its entries are a literal tuple loaded and hash-checked at import, so an edited definition at an unchanged version makes the import itself fail naming the variant. | The suite definitions it sits beside are Python data, and the gate (`row_contract.validate_row`) reads the registry on every write: a cwd-relative data file would make the gate depend on the working directory, which `uv_build` package-data and test `chdir`s would both have to be taught about. The story's "proposed beside the suite definitions" reads naturally as this. |
| The new pre-template field is named `prompt_before_template`; the variant version is a string (`"1"`), matching `suite_version`, `rubric_version` and `metric_version`. | Names the intent (the prompt as it stood before the engine's templating) rather than the mechanism. No backlog artifact names the field. |
| The gate resolves "the item's authored text" from the code that owns it: the three suites keyed by `suite_id` (classification, translation, judge probe) for a quality row, `FIXED_PROMPT` for a runtime row. A `baseline` row whose suite, suite version or item cannot be resolved is refused, naming the field, because the claim cannot be checked. Imports are function-local: every suite module imports `row_contract`. | A text the row itself carried could be forged alongside the transformed prompt, which is exactly the hand-built row the gate must refuse. Requiring the in-code `suite_version` keeps "the item" the one identified by (suite, version, item). |
| The declared variant is a module constant on each writer (`PROMPT_VARIANT_ID = prompt_variants.BASELINE_ID`), resolved once per invocation through the registry. | The campaign declaration that would carry it as data is a later story in the epic; until then every writer runs `baseline`, and a constant is the narrowest declaration that is still not chosen per call site. |
| The judge is still handed the item's authored prompt, not the variant's output. | Epic decision "Variant is a prompt transformation and nothing else": it never changes the scorer. |
| The three new fields are not rendered by the results service (`read_model` `*_FIELDS_NOT_RENDERED`). | Epic Boundaries exclude "rendering either dimension to a decision-maker" (owned by the pitch epic); the partition test still forces each field to be placed. |
