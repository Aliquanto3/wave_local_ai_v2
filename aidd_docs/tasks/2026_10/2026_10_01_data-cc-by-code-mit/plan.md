---
objective: "LICENSE stays MIT for the code, LICENSE-DATA carries CC-BY 4.0 in full with a scope naming every covered part and every part it does not grant, each covered directory and each item-literal module states its terms where it lives, README states the split, and a test fails on any covered path that is renamed, missing its notice, or added without one."
status: implemented
---

# Plan: The data is CC-BY 4.0, the code stays MIT, and each says so where it lives

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A scoped data licence beside the unchanged MIT code licence, notices where the data lives, a README licence section, and a test that keeps the scope and the tree in step |
| **Source** | `aidd_docs/backlog/stories/the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives.md` (owner answers Q43 (a) and Q1 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`) |

## Phases

| #   | Phase                                                        | File                         |
| --- | ------------------------------------------------------------ | ---------------------------- |
| 1   | LICENSE-DATA, the directory and module notices, and the test | [`phase-1.md`](./phase-1.md) |
| 2   | The README licence section                                   | [`phase-2.md`](./phase-2.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| https://creativecommons.org/licenses/by/4.0/legalcode.txt | The official CC-BY 4.0 legal code, fetched 2026-10-02 (18657 bytes, 396 lines, UTF-8, sha256 `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411`) and appended to `LICENSE-DATA` byte for byte, its two curly quotes included. |

## Decisions

| Decision | Why |
| -------- | --- |
| The last acceptance bullet applies to `judge_probe.py` only: it is the one module in `src/wave_local_ai_v2/` holding hand-written item literals (`JUDGE_PROBE_ITEMS`, ten `_item(...)` calls). `classification_suite.py` and `translation_suite.py` get no notice. | Since commit `d66f760` (Q1 (a)) their items live in `suite_data/*.json`; both modules now hold only the label set, the item shape and the rationale. The bullet's parenthetical is stale, and a "holds item literals" notice on a module that holds none would be false. A grep of every `src/` module for item constructors and item-shaped literals found no other. |
| `src/wave_local_ai_v2/suite_data/` is a covered directory in `LICENSE-DATA` and holds its own `NOTICE.md`. | Q43's intent is that hand-written items inside `src/` fall under `LICENSE-DATA`; the items moved there from the two modules. JSON cannot carry a header, so a notice file in the directory is the equivalent. `suite_registry` lists only names ending in `.json` (`suite_registry.py`, the `iterdir` filter), so the notice registers no suite. |
| `aidd_docs/results/comparisons/` is covered and holds a notice. | Its family records are published results computed over covered rows, written by the project, with no model output in them. Leaving a published results directory unscoped is the gap the story closes. |
| The roster's licence and language blocks are covered as part of `aidd_docs/roster/models.json`; the licences those blocks record are named as not granted. | The blocks are the project's records (what the publisher states, when it was read, which languages are claimed). The epic: "The roster names third-party licences; it grants none of them." |
| `src/wave_local_ai_v2/use_case_coverage.json` is covered as a named file; its published copy (`aidd_docs/results/use-case-coverage.json`, not yet written) is covered by the `aidd_docs/results/` entry. It gets no directory notice. | It is hand-written data the project publishes into `aidd_docs/results/`; one set of terms for the same bytes avoids the dual-licence bypass Q43 closed for items. Its directory is the code package, so a directory notice there would claim the code; the scope entry names the file instead. |
| The notice file is `NOTICE.md` in each covered directory; `README.md`/`NOTICE.md` in a covered directory are named as documentation, not data. | One fixed name lets the test find it. The repository states no licence for its documentation today, and this story does not invent one. |
| The covered list in `LICENSE-DATA` is a fixed-format bullet list (`` - `path`: ... ``) that the test parses. A path ending in `/` is a directory that must hold `NOTICE.md`; a `.py` path is an item-literal module that must carry the header notice. | The test reads the scope from the file a reader reads, so a renamed path or a directory added to the scope without a notice fails, with no second list to drift. |
| The test also requires every subdirectory of `aidd_docs/results/` and `aidd_docs/roster/`, every `*-reference*.jsonl` in `aidd_docs/results/`, and every `src/` module binding a list literal to a name ending in `ITEMS` to be named in the covered list. | Catches the other half of drift: a data directory or a superseded reference file added later without entering the scope, or a new item-literal module without its header. |
| The model-output part names `predicted_label` today and states that any later row field holding a model's generated output joins it. | It is the only output field on today's published rows (checked over all four reference files); naming the rule rather than only the field stops a future `subject_output` from falling under CC-BY by default. |
| The legal text's integrity is checked by the sha256 of the text after the marker line. | "In full" and "verbatim" become checkable; a hand edit of the legal code fails the build. |
| The licensor is named as in `LICENSE` ("Aliquanto3"); the attribution string is left to order 2, and README and `LICENSE-DATA` say where it will be. | The epic defers the attribution identity to the first tag. |
