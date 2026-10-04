---
objective: "The ~2B class holds a second family beside Qwen3-1.7B, admitted through the candidate gate and run through both suites on the laptop from a committed tree, with its MoE question answered, or is labelled a single-family ladder citing every refusal; the composition check passes for the class."
status: implemented
---

# Plan: The ~2B class spans two families, or is published as a searched single-family ladder

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Gate the class's pinned candidates in the story's order (`lfm2`, `granitemoe`, `granitehybrid`, `granite`) until one non-Qwen entry passes and the MoE question is answered; publish the entries, their download sections, the class declaration and composition (stage A, committed), then both suites per entry from that commit (stage B) |
| **Source** | `aidd_docs/backlog/stories/the-two-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md` |

## Phases

| #   | Phase                                                    | File                         |
| --- | -------------------------------------------------------- | ---------------------------- |
| 1   | Candidate gate runs, in gate order                       | [`phase-1.md`](./phase-1.md) |
| 2   | Roster entries, class declaration, docs, tests (stage A) | [`phase-2.md`](./phase-2.md) |
| 3   | Both suites from the committed tree, promote, merge (stage B) | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `https://huggingface.co/api/models/<repo>` for the four GGUF repos | each repo's head sha equals the story's pin; card licence `other`/`lfm1.0` (Liquid, LICENSE file), `apache-2.0` (IBM, bartowski; README only) |
| `https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct/blob/0f604ada3f766f9f257460c4c9f0b5d6f69d431b/README.md` l.67 | the LFM2.5 language statement (the GGUF card states none) |
| `https://huggingface.co/ibm-granite/granite-3.1-1b-a400m-instruct/blob/0da7a48b0276d500ce5922fd2b33944091fc6c09/README.md` l.25-26 | the Granite 3.1 language statement (bartowski's card states none) |
| `https://huggingface.co/ibm-granite/granite-4.0-h-1b/blob/d18cca4c...` and `granite-4.0-1b/blob/6a7381ba...` README l.23-24 | the Granite 4.0 Nano language statement |

## Decisions

| Decision | Why |
| -------- | --- |
| Each declaration copies `qwen3-1.7b-q8`'s `server_flags` verbatim and `load_profile` `{n_cpu_moe: null, threads: 8}`, the MoE included | The half-billion story's precedent; a 1.4 GB MoE fits the 6 GB GPU whole, so no `--n-cpu-moe` |
| Language claims cite the base model card at its own sha | The GGUF cards (Liquid, bartowski) carry no language statement |
| `active_params_b` is total/1e9 rounded for the dense candidates, 0.4 for the MoE | The spike's "~0.4B active" for Granite 3.1 1B-A400M |
| Rows are run only after the orchestrator commits stage A | Methodology 19: a published row carries a clean commit (`tree_dirty: false`) whose roster holds its entry |
