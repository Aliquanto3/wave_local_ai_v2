---
objective: "The ~8B-and-up class holds a second family and a dense model beside the Qwen3.6-35B-A3B flagship, admitted through the candidate gate and run through both suites on the laptop from a committed tree, or says which requirement it misses and why; the composition check passes for the class."
status: in_progress
---

# Plan: The top class spans two families with dense and MoE, or says why not

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Gate the dense Gemma 4 12B `IQ4_XS` first; only if it does not pass (gate and both suites), gate the Gemma 4 26B-A4B `UD-IQ4_XS` MoE. Publish the entry, its download section, the class declaration and composition (stage A, committed), then both suites per entry from that commit (stage B) |
| **Source** | `aidd_docs/backlog/stories/the-top-class-spans-two-families-with-dense-and-moe-or-says-why-not.md` |

## Phases

| #   | Phase                                                    | File                         |
| --- | -------------------------------------------------------- | ---------------------------- |
| 1   | Candidate gate runs, in gate order                       | [`phase-1.md`](./phase-1.md) |
| 2   | Roster entry, class declaration, docs, tests (stage A)   | [`phase-2.md`](./phase-2.md) |
| 3   | Both suites from the committed tree, promote, merge (stage B) | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `https://huggingface.co/api/models/<repo>/revision/<sha>` for the two GGUF repos | each pin resolves to itself; card licence `apache-2.0`; `gemma-4-12b-it-IQ4_XS.gguf` 6,375,734,080 B, `gemma-4-26B-A4B-it-UD-IQ4_XS.gguf` 13,597,177,568 B |
| `unsloth/gemma-4-12b-it-GGUF@fc034cff...` README l.157, `unsloth/gemma-4-26B-A4B-it-GGUF@c099eb48...` README l.150 | the Gemma 4 language statement, naming no language ("Out-of-the-box support for 35+ languages, pre-trained on 140+ languages.") |
| `google/gemma-4-12B-it@707f0a3b...` and `google/gemma-4-26B-A4B-it@4d7ae498...` `config.json` | 12B: 48 layers (8 full-attention); 26B-A4B: 30 layers, 128 experts, 8 active |

## Decisions

| Decision | Why |
| -------- | --- |
| The 12B's declaration copies `qwen3-4b-q4km`'s `server_flags` verbatim (`-ngl 99`, `load_mode: auto`) and `load_profile` `{n_cpu_moe: null, threads: 8}` | The story: the 12B is dense and declares as the dense Qwen entries do; the earlier class stories copied the same block |
| The 26B-A4B's declaration takes `load_profile.n_cpu_moe` 28 of its 30 layers | The flagship's ratio on the same 6 GB GPU (37 of 40); gated only if the 12B does not pass |
| `language_claim.languages` is empty for both | The card names no language, only counts; the roster allows an empty claim (the flagship's is empty too) |
| `active_params_b` 11.91 for the dense 12B | Its total, as every dense entry declares (the spike's 11,907,350,576) |
| The plan is written directly rather than through `aidd-dev:01-plan` | The earlier class stories' layout is followed as the pattern the orchestrator named |
| Rows are run only after the orchestrator commits stage A | Methodology 19: a published row carries a clean commit (`tree_dirty: false`) whose roster holds its entry |
