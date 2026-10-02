---
objective: "Every roster entry can declare a family the code resolves for every candidate vendor, and every shipped entry carries a validated licence block and a sourced EN/FR/DE language claim."
status: implemented
---

# Plan: Every roster entry states its family, its licence and its language claim

## Overview

| Field      | Value                                                                                          |
| ---------- | ---------------------------------------------------------------------------------------------- |
| **Goal**   | Grow `KNOWN_FAMILIES` to the candidate vendors, check `family` at load, add the licence and language-claim blocks, fill them for the four shipped entries. |
| **Source** | `aidd_docs/backlog/stories/every-roster-entry-states-its-family-its-licence-and-its-language-claim.md`; owner answer Q11 (a) |

## Phases

| #   | Phase                                         | File                         |
| --- | --------------------------------------------- | ---------------------------- |
| 1   | Families, family check and block validation   | [`phase-1.md`](./phase-1.md) |
| 2   | Shipped blocks, version bump and the export   | [`phase-2.md`](./phase-2.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/blob/23749fefcc72300e3a2ad315e1317431b06b590a/README.md (+ `LICENSE`) | `license: apache-2.0`; LICENSE is Apache 2.0; language wording "Support of 100+ languages and dialects", no language named |
| https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/blob/90862c4b9d2787eaed51d12237eafdfe7c5f6077/README.md (+ `LICENSE`) | same as 0.6B |
| https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/bc640142c66e1fdd12af0bd68f40445458f3869b/README.md (+ `LICENSE`) | same as 0.6B |
| https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/blob/main/README.md | `license: apache-2.0` linking upstream LICENSE; repo has no LICENSE file (404); `main` resolved to `a483e9e6cbd595906af30beda3187c2663a1118c`, the sha `docs/setup.md` records; the card states no supported language |
| https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/main/LICENSE | upstream LICENSE the flagship card links, Apache 2.0, `main` at `995ad96eacd98c81ed38be0c5b274b04031597b0` |

## Decisions

| Decision | Why |
| -------- | --- |
| Family values are vendor lineage (Q11 (a)): add `ibm`, `liquid`, `microsoft`; Gemma resolves to `google`, Ministral to `mistral`. `glm`/`deepseek` not added. | Owner answer Q11 (a); the judge families are the judge epic's stories, per the acceptance. |
| A declared `family` outside `KNOWN_FAMILIES` (or not a string) is refused in `load_roster`, naming entry and value. `family_of` keeps its own check for the `MODEL_FAMILIES` fallback. | Acceptance bullet 2; refusal at load reaches the operator before any run. |
| `licence` = `{id, client_commercial_use, read_on, source_url}`; `language_claim` = `{languages, source_url, read_on, statement?}`, both optional on `RosterEntry`, not in `REQUIRED_FIELDS`. | Acceptance says each entry *can* carry them; keeps constructed and older rosters loading, same seam as `family` and `thinking_control`. The shipped-file test is what makes them present. |
| `languages` lists only what the card names among `en`/`fr`/`de`; the vendor's wording goes verbatim in `statement`. All four shipped claims list `[]`. | The pinned cards say "100+ languages and dialects" (dense) or nothing (flagship) and name no language: recording `en`/`fr`/`de` would be inference, not the vendor's claim. The Qwen blog's language list is outside the pinned card and is not used. |
| Licence `id` written as the SPDX identifier `Apache-2.0` (cards spell `apache-2.0`). | Matches the bundle's `item_licence` unit, "SPDX licence identifier". |
| Flagship licence source is its own card at `main` (no LICENSE file in the packager repo), read date standing in for the sha. | Acceptance bullet 5 and the open tech-debt row on the flagship's `main` pin. |
| `roster_version` 2 -> 3; the version line inside `test_the_shipped_moe_entry_still_loads_with_no_family_of_its_own` moves 2 -> 3, its family assertions untouched. | Acceptance bullet 6 names that assertion as the one that follows the file; it lives in that test, so "unchanged" is read as its family half. |
| The bundle carries the blocks as roster-table columns; the "roster licence block" owned-elsewhere entry is removed. | The bundle export refuses an undescribed field, and a block it now carries is no longer owned elsewhere. |
| `test_family_of_refuses_an_entry_declaring_an_unknown_family` becomes a load-time refusal test. | The acceptance moves that refusal to load, so the old test can no longer reach `family_of`. |
