---
objective: "The ~4B class holds a second family beside Qwen3-4B, admitted through the candidate gate and run through both suites on the laptop from a committed tree, with its MoE question answered, or is labelled a single-family ladder citing every refusal; the composition check passes for the class."
status: in_progress
---

# Plan: The ~4B class spans two families, or is published as a searched single-family ladder

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Gate the class's pinned candidates in the story's order (`granitemoe`, `mistral3`, `phi3`, `phimoe`) until one non-Qwen entry passes and the MoE question is answered; publish the entry, its download section, the class declaration and composition (stage A, committed), then both suites per entry from that commit (stage B) |
| **Source** | `aidd_docs/backlog/stories/the-four-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md` |

## Phases

| #   | Phase                                                    | File                         |
| --- | -------------------------------------------------------- | ---------------------------- |
| 1   | Candidate gate runs, in gate order                       | [`phase-1.md`](./phase-1.md) |
| 2   | Roster entry, class declaration, docs, tests (stage A)   | [`phase-2.md`](./phase-2.md) |
| 3   | Both suites from the committed tree, promote, merge (stage B) | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `https://huggingface.co/api/models/<repo>` for the four GGUF repos | each repo's head sha equals the story's pin; card licence `apache-2.0` (bartowski, Mistral; README only for bartowski), `mit` (unsloth, tripathyShaswata) |
| `https://huggingface.co/ibm-granite/granite-3.1-3b-a800m-instruct/blob/a02780686e08a03fe0d2679a293b5c74a90efa89/README.md` l.25-26 | the Granite 3.1 language statement (bartowski's card states none) |
| `mistralai/Ministral-3-3B-Instruct-2512@b35d4dfe...` README l.42, `microsoft/Phi-4-mini-instruct@cfbefacb...` card `language`, `microsoft/Phi-tiny-MoE-instruct@2fe50e88...` README l.24 | the language statements of the three declarations not gated |
| The downloaded GGUF's header | `granitemoe.expert_count` 40, `expert_used_count` 8, `block_count` 32, `context_length` 131072 |

## Decisions

| Decision | Why |
| -------- | --- |
| The declaration copies `qwen3-4b-q4km`'s `server_flags` verbatim and `load_profile` `{n_cpu_moe: null, threads: 8}`, the MoE included | The earlier class stories' precedent; a 2.0 GB MoE fits the 6 GB GPU whole at a 32,768-token context (the gate's load launched with `-ngl 99`), so no `--n-cpu-moe` |
| Phi-tiny-MoE's declaration sets `context_size: 4096` | Its trained context, per the story and the spike's assumption (4) |
| Language claims cite the base model card at its own sha | bartowski's card carries no language statement |
| `active_params_b` 0.8 for the MoE | The spike's "~0.8B active" for Granite 3.1 3B-A800M |
| The search stops after Granite 3.1 3B-A800M's pass | Owner answer Q128 (a): it is non-Qwen and MoE at once, so its pass (gate and both suites) ends the search |
| Rows are run only after the orchestrator commits stage A | Methodology 19: a published row carries a clean commit (`tree_dirty: false`) whose roster holds its entry |
