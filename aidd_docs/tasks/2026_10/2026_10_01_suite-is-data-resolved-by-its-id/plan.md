---
objective: "Every task suite is one declared definition held as data, gated at load and resolved by its suite id through a registry, so the quality CLI runs any registered suite with no suite import or branch of its own, while the two shipped suites' versions, prompt-set hashes and snapshot bytes stay unchanged."
status: implemented
---

# Plan: A suite is data resolved by its id, not an import in the CLI

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Replace `quality_cli._SUITES`/`SuiteSpec` with a suite registry over data files and named scoring rules; migrate classification and translation onto it byte-for-byte |
| **Source** | `aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md` (owner questions Q1 and Q43, default (a)) |

## Phases

| #   | Phase                                                                 | File                          |
| --- | --------------------------------------------------------------------- | ----------------------------- |
| 1   | The suite registry, the data files, the named scoring rules, snapshots from the registry | [`phase-1.md`](./phase-1.md) |
| 2   | The quality CLI resolves `--suite` through the registry; fixture suite end to end; docs | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| New module `suite_registry.py` holds `SuiteDefinition` (frozen dataclass), `load_definition`, `register`, `resolve`, `registered_ids`, `prompt_set_hash` and the scoring-rule table lookup. Built-in definitions are the JSON files in the package directory `src/wave_local_ai_v2/suite_data/`, one file per suite named `<suite_id>.json`, discovered by listing that directory and loaded lazily on first `resolve` (cached). | Package data travels with the installed package and needs no path setting; naming the file by the id lets `registered_ids()` list suites without loading any, so one broken file never stops another suite from running. Adding a suite is dropping a file. |
| The named scoring rules live in a new `scoring_rules.py` (`exact_label_match`, `chrf_against_reference`), a name-to-callable table the registry consults; a rule's signature is `(items, completions, *, max_output_tokens) -> (per_item_fields, batch_fields)`. | Moving them into `classification_suite.py`/`translation_suite.py` would form an import cycle (`scoring.py` imports both modules for `LABELS` and the item TypedDicts). The cap is passed in, so a rule no longer reads a module constant and the suite's own declared cap is what scores truncation. |
| Each data item stores its full `prompt` string (instruction included), plus every field the snapshot already publishes, and an explicit `contamination_risk`. The instruction text is therefore repeated per item. | The published prompt is readable from the data with no rendering rule in code, and `PROMPT_SET_HASH` is computed over exactly the strings that are stored. A per-suite instruction template would need a renderer per suite, i.e. code per suite again. |
| `prompt_set_hash` moves from `classification_suite.py` to `suite_registry.py`; `judge_probe.py` imports it from there. | It is suite identity, not classification scoring; leaving it in a suite module would make the registry import a suite module for its hashing rule. The hashing rule itself is unchanged. |
| The definition carries `task_suite` (the row's use-case name, `classification`/`translation`) as a declared field beside the story's listed fields. | Rows already publish `task_suite` and `--resume` keys on it; a future publication-level suite shares `task_suite` with a different `suite_id`, so it cannot be derived from the id or the rule. |
| Unknown suite-level keys in a definition are kept in `SuiteDefinition.extra` and exported in the snapshot; unknown item keys are kept on the item. Only the core keys are type-checked. | Satisfies "the interval epic's fields are additions without a second shape": a `level`, `licence` or `selection_rule` lands in the data and the snapshot with no loader change. Cost: a misspelt optional key is carried instead of refused. Today's two files carry no extra key, so their snapshots do not move. |
| The scoring-rule name and `task_suite` are not exported in the snapshot. | The acceptance pins today's snapshot bytes; adding either key would rewrite both committed files. |
| `--suite` takes a registered suite id (default `classification-support-routing`); the old `classification`/`translation` values are refused like any unregistered id. No alias table. | The acceptance says `--suite` takes a suite id and refuses an unregistered one; an alias layer is a second resolution path. An invocation with no `--suite` behaves as before. Docs updated. |
| The refusal of an unregistered id is raised by the registry (`SuiteRegistryError`, naming the registered ids) and caught by `main()` as one stderr line, not by argparse `choices`. | One refusal for every caller: the CLI, `row_contract`'s baseline check and the snapshot exporter all resolve through the same function. |
| The gate result is computed once at load and held on the definition (`SuiteDefinition.gate`); the CLI reads it instead of calling `gate_suite` again. | "Every definition passes through the gate when it is loaded": a refused definition never becomes a `SuiteDefinition`, so it cannot reach a run. |
| `row_contract._authored_prompt` resolves registered suites through the registry; the judge probe stays a separate in-code entry. | A fixture suite registered in a test must pass the writer gate's baseline check; otherwise the "no edit to `quality_cli.py`" test fails in `row_contract` instead. |
| The per-suite rationale comments (why the caps, why each version bump) move into the suite modules' docstrings; JSON carries no comments. | Keeps the reasoning beside the code that remains for each suite without adding a `notes` key that would change the snapshots. |
| Q43's header notice (items CC-BY 4.0, code MIT) is not added here: its story is `the-data-is-cc-by-4-0-...` and no `LICENSE-DATA` exists yet. After this story the items no longer live in `src/*.py` literals; they live in `suite_data/*.json`. | Out of scope; noted in the report as a change of premise for that story. |
