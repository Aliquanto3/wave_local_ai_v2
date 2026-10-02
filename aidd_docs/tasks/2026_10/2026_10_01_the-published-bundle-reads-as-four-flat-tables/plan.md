---
objective: "A packaged, standard-library-only command turns the published bundle into four flat CSV tables, a column dictionary and a manifest declaring the schema it read, with every pointer resolved, absence kept distinguishable from a recorded null, and the published accuracies recomputable from the quality table alone."
status: implemented
---

# Plan: The published bundle reads as four flat tables and their column dictionary

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Ship `wave-local-ai-v2-export` (`bundle_export.py`): quality, runtime, fiche and roster tables plus `column_dictionary.csv` and `bundle_manifest.csv`, derived from the bundle and computing nothing |
| **Source** | `aidd_docs/backlog/stories/the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary.md` |

## Phases

| #   | Phase                                                             | File                         |
| --- | ----------------------------------------------------------------- | ---------------------------- |
| 1   | Export module, column registry, entry point and tests             | [`phase-1.md`](./phase-1.md) |
| 2   | Run over the committed bundle, recomputation evidence, README     | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Columns are data-driven (the leaf paths the bundle's rows actually carry), each described by a static registry keyed by source path with `*` for dynamic keys (language codes, metric parameters, aggregation labels); a path the registry does not know is refused, naming it | Every column written is documented by construction, nothing is silently dropped, and a schema-"7" bundle does not drag forty always-empty schema-"14" columns. A test partitions the registry against `row_contract` so a contract field added later fails the build until it is described |
| Contract fields no row of the bundle carries are written to the dictionary as `carried=false` entries, beside the four blocks owned elsewhere (interval, item licence and source, roster licence, comparison/family records) | "Every dictionary column is in a table" holds for `carried=true` entries; the not-carried entries are named, with the epic or story that owns each, and are asserted to be in no table |
| A recorded `null` and a field the row does not carry are both empty cells; each row's `fields_not_carried` column lists the column names whose emptiness is "not carried" | Keeps numeric columns numeric for DuckDB/R/spreadsheet type inference (a `null` token would turn them into text), while still letting a reader tell the two apart from the table alone |
| Lists (`stop_sequences`, `indicative_reasons`, `verdict.differing_fields`, fiche `flags`) and the judge block's nested records are one compact JSON cell each; per-repetition arrays (`repetitions`, `warmup_repetitions`, `verdict.reference_repetitions`) are excluded and the dictionary says so | Acceptance names dicts as the nested fields to flatten; a variable-length list has no fixed column set. Per-repetition arrays stay in the bundle by acceptance |
| A pointer that does not resolve, a non-finite float, a column-name collision, or a value whose shape conflicts across rows refuses the whole export (exit 1) before any file is written | A table with silently empty machine columns would publish a broken bundle as a complete one |
| CSV pinned as UTF-8 without BOM, `,` delimiter, `"` quote with doubling, minimal quoting, `\r\n` record terminator (RFC 4180), floats as Python's shortest round-trip `repr`, booleans as `true`/`false` | Explicit and OS-independent: files are opened with `newline=""`, and `repr` round-trips every IEEE-754 double |
| `--output-dir` is required; inputs default to the committed bundle paths in `settings` | The command never writes into the bundle by default and never reads the untracked live stores unless pointed at them |
| The roster entry is resolved from the roster file as it stands, and the table carries both the row's own `roster_version` and the file's `roster_file_version` | The bundle rows cite roster version 1 while the file is version 2; the export reconciles nothing and makes the gap readable instead |
