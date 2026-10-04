---
objective: "A 300-item publication-level translation suite drawn from WMT24++ by the recorded sampler rule stands beside the hand-written 21-item suite, its output cap derived from its references under the subject's tokenizer, licensed on the permissive rung with the Apache-2.0 text beside its items, and published in the reference bundle with one development-level batch of the hand-written suite on the same subject in the same session."
status: in_progress
---

# Plan: A publication-level translation suite stands beside the hand-written one

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | The WMT24++ loader (standard library only), the drawn suite with its source-table hash and its derived cap, the export columns, the licence/NOTICE/coverage/README edits, then two published batches on one subject |
| **Source** | `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md` (owner answers Q106 (a), Q118 (a), Q119 (a), Q120 (a), Q130 (a), Q132 (a), Q133 (a), Q134 (a)) |
| **Twin**   | `aidd_docs/tasks/2026_10/2026_10_04_publication-classification-suite/` (`95040a7`, `cf4c224`) |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The loader, the drawn suite, its snapshot and the export columns | [`phase-1.md`](./phase-1.md) |
| 2   | Licence texts, NOTICEs, coverage record and the README statement of the rung | [`phase-2.md`](./phase-2.md) |
| 3   | Stage B: the two published batches, promotion, merge and evidence | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| https://huggingface.co/api/datasets/google/wmt24pp/tree/fd7405c06494bc66a57b25f55d217a72f96e60dc?recursive=true | 57 entries: `.gitattributes`, `README.md` and one `<pair>.jsonl` per pair, no LFS (each file's git blob SHA-1 is its `oid`), no licence or NOTICE file |
| `en-fr_FR.jsonl`, `en-de_DE.jsonl` at the revision (fetched read-only, no login) | 998 rows each, same `segment_id` set (0-997), `source`, `domain`, `document_id` and `is_bad_source` equal on every segment; 38 `is_bad_source` rows (the canary and 37 social), 960 left: social 494, literary 206, news 149, speech 111 |

## Decisions

| Decision | Why |
| -------- | --- |
| Direction by `segment_id % 3`: 0 => EN->FR, 1 => FR->DE, 2 => DE->EN; the stable key is the bare `segment_id`. | Q133 (a): each segment in exactly one direction before the draw, so items stay independent and `canonical_order` never meets a key twice. Pools after the filter: 315, 322, 323. |
| One shared helper module `scripts/hub_source.py` (hash, git-blob check, tree listing, licence-file scan, table text, table verification, file writes, publication certification); `scripts/minds14_suite.py` imports it instead of holding its own copies. | The orchestrator asked to reuse and extend the twin's loader rather than duplicate it; minds14's public names stay importable, so its tests are untouched. |
| `scripts/wmt24pp_suite.py` reads the two jsonl files with the standard library and checks each against the Hub's git blob SHA-1; no dependency group. | The story: "needs no new dependency"; the files are not LFS, so the tree's `oid` is the git blob SHA-1. |
| The cap: `count-tokens` asks a running `llama-server` (`/tokenize`, `add_special` false) for every pool reference's token count with the subject's GGUF; `draw` sets `max_output_tokens` to twice the longest drawn reference's count and records `max_output_tokens_basis` {`tokenizer`, `longest_reference_item_id`, `longest_reference_tokens`, `factor`, `reason`}; each item carries `reference_tokens`. | Q118 (a): the reason names the tokenizer of the model the published batches run (`granite-4.0-h-350m-q8`). CI cannot run that tokenizer, so it checks the arithmetic over the recorded counts and bounds each count by the reference's UTF-8 byte length (a byte-level BPE token covers at least one byte). |
| Prompt shell identical to the hand-written suite's ("Translate the following {source} text into {target}. Reply with only the translation, nothing else.\n\nText: ..."). | The two levels differ by their items, not by their instruction. |
| The Apache-2.0 text ships as `LICENSE-APACHE-2.0.txt` in `src/wave_local_ai_v2/suite_data/`, `aidd_docs/results/suite-definitions/` and `aidd_docs/results/`, byte-equal (LF) to https://www.apache.org/licenses/LICENSE-2.0.txt (SHA-256 `cfc7749b...`), taken from a locally installed package's copy (no download); each NOTICE states the change made. | Q106 (a) and spike assumption A2; no other download is allowed. |
