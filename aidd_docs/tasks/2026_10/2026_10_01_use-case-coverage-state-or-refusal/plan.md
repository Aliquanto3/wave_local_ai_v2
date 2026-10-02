---
objective: "Every PRD use case is one entry of a declared coverage record held as data, and the command that publishes that record into `aidd_docs/results/` refuses, writing nothing and naming every failing entry, unless all ten entries carry a resolvable state."
status: implemented
---

# Plan: Every PRD use case carries a coverage state, or the record refuses to publish

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A coverage record as data beside the suite registry, a gate over it that resolves every named suite through `suite_registry`, and a publish command that refuses until every entry resolves |
| **Source** | `aidd_docs/backlog/stories/every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish.md` (owner question Q30, answer (a): strict refusal, the refusal output is the interim coverage reading) |

## Phases

| #   | Phase                                                           | File                         |
| --- | --------------------------------------------------------------- | ---------------------------- |
| 1   | The coverage record as data and the gate over it                | [`phase-1.md`](./phase-1.md) |
| 2   | The publish command, its refusal evidence, and the docs          | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| New module `use_case_coverage.py` holds the PRD's ten use-case ids (`USE_CASES`, in PRD order), the three states, the gate and the publish command. The record is `src/wave_local_ai_v2/use_case_coverage.json`, beside `suite_registry.py`, not inside `suite_data/`. | The story places the data file "beside the suite registry". `suite_data/` is listed by the registry as suite ids, so a record file there would register as a suite. The required list lives in code, not in the record: if the record declared its own required list, removing an entry and its list item together would pass. |
| The use-case ids are `classification`, `translation`, `document-comparison`, `text-rewriting`, `code-generation`, `agentic-planning`, `agentic-tool-calling`, `web-research`, `rag-answer-generation`, `multilingual-en-fr-de`. | The PRD acceptance criterion's nine names plus its multilingual dimension, kebab-cased; the first two match the shipped `task_suite` values. |
| The rewriting suite is named `rewriting-business-email` in the record (`text-rewriting` `exercised`, and the third suite of `multilingual-en-fr-de`). | No backlog artifact names the rewriting suite's id. The story requires multilingual to "name the unregistered rewriting suite", so an id must be declared; it follows the shipped `<use case>-<domain>` pattern and the quality epic's "text/email rewriting". The story that registers that suite either uses this id or edits the record, which is the declared-not-inferred discipline the gate exists for. |
| The six use cases this epic has yet to build are declared with `"state": null`, not omitted and not given a planned suite id. | The record is "one entry for each" use case; a null state is the honest declaration that nothing covers it yet, and it is refused as "has no state", which is the reading the story asks the refusal to give. |
| An entry is refused for each of: missing, no state, an unknown state, an `exercised`/`covered-by-dimension` entry with no suite id list or naming a suite `suite_registry.resolve` does not resolve (a registry or gate refusal), an `out-of-scope-this-release` entry with a blank or absent reason, a state carrying the other state's field (`reason` on a suite state, `suite_ids` on out-of-scope), a use case outside the PRD list, and a use case declared twice. All failures are collected; one line per failing entry names the use case and every problem on it. | The acceptance names four refusals and requires every failing entry named. "Exactly one of" the three states makes a mixed entry ambiguous, and an unknown or duplicated entry would make a record that passes while saying two things; each is one cheap check. |
| The command is a module invocation, `uv run python -m wave_local_ai_v2.use_case_coverage`, with `--record` and `--output` overrides; no `pyproject.toml` entry point. It writes `aidd_docs/results/use-case-coverage.json` (`settings.DEFAULT_USE_CASE_COVERAGE_PATH`) only after the gate passes, exits `1` with the refusal on stderr otherwise. | Mirrors `suite_snapshot`, the closest analogue (a publisher into `aidd_docs/results/` run after a data edit, not a benchmark CLI). The output path is configuration, per the settings module's stated rule. |
| The published record is the declared entries in PRD order, under `use_cases`, each with its state and its suite ids or reason, nothing derived. | The record is a declaration; adding resolved versions would be a second claim the story does not ask for. Never published today (the gate refuses), so its shape costs nothing to revise. |
| The frontend's `CoverageRecord`/`CoverageAbsence` declared absence is left untouched. | The record is not published until every entry resolves (Q30 (a)), so the absence those components state remains true. Rendering is the pitch epic's. |
