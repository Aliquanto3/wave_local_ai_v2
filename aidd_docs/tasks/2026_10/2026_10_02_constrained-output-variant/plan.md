---
objective: "The registry holds `constrained_output` v1 with a per-family GBNF grammar; llama.cpp receives it per request and every quality row names the mechanism and the grammar hash (schema \"28\"); the engine entry declares its mechanisms and a campaign pairing the variant with an engine that supports none is refused; one laptop baseline-versus-constrained pair is compared."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: The constrained-output variant runs under a llama.cpp grammar and names its mechanism

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `constrained_output` v1 in `prompt_variants.py` (classification: closed-label GBNF, no added instruction; translation: no-op with reason); `constraint_for(variant, family)`; `local_client.complete_chat(grammar=...)`; engine entry `constraint_mechanisms` (`gbnf` -> request field `grammar`); campaign refusal; quality rows carry `constraint_mechanism` and `constraint_grammar_hash` from schema "28", checked by the gate; one laptop pair compared |
| **Source** | `aidd_docs/backlog/stories/the-constrained-output-variant-runs-under-a-llama-cpp-grammar-and-names-its-mechanism.md`; parent epic `the-engine-and-the-prompt-variant-are-measured-not-assumed.md`; night-run owner decision D2 (local only) |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Registry entry, engine mechanisms, campaign refusal | [`phase-1.md`](./phase-1.md) |
| 2   | Request path, row fields (schema "28"), gate and comparison exemptions | [`phase-2.md`](./phase-2.md) |
| 3   | Docs and the laptop campaign cell pair with its comparison record | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Definition key `output_formats`: per family, `format` (prose), `instruction` (null = none added) and `constraint` `{mechanism, grammar}`. Classification: `root ::= "account" \| "billing" \| "other" \| "technical"`, no instruction. Translation: not in `applies_to`, reason recorded. | The authored classification prompt already states the format the grammar enforces, so the pair isolates the decoding constraint; a translation is open text, any grammar admitting every reference admits every answer. |
| The mechanism is `gbnf`, sent as the per-request `grammar` field on `/v1/chat/completions`. | `llama-server --help` (b10537): `--grammar GRAMMAR  BNF-like grammar to constrain generations`; per-request use confirmed by a live request in phase 3 evidence. |
| Engine entry gains required `constraint_mechanisms`: `{mechanism: {request_field, read_from}}`; `{}` declares none. | Acceptance line 5; the mechanism-to-field spelling is engine data, like `thinking_switch`. |
| A campaign declaring a variant with a constraint on an engine declaring none of the variant's mechanisms is refused at load. | Acceptance line 5 ("declares none"); a different mechanism the variant cannot express is equally unrunnable until order 8 adds it. |
| A run of a constraining variant with a cloud provider in `QUALITY_PROVIDERS` is refused before launch. | A cloud subject has no grammar path; its row would claim a constraint it never ran under. |
| Rows (quality only, from "28"): `constraint_mechanism` (`gbnf` or `none`) and `constraint_grammar_hash` (sha256 of the grammar sent, or null under `none`); the gate checks both against the registry for the row's variant and `task_suite`. | Acceptance line 2; same derivation-check pattern as `prompt_variant_noop`. |
| Both new fields join `comparison.py`'s `prompt_variant` dimension fields (they move with the variant axis), so a variant pair's differing set names the variant fields and the mechanism and is still a test, while on any other axis they stay compared. | Acceptance line 4: the differing-field set names "only the variant fields and the constraint mechanism". |
| Local run under a campaign declared in `evidence/campaigns`, every results path in `evidence/`; no judge, no cloud (D2). | Brief. |
| The baseline share outside the format is measured by replaying the baseline requests (same build, model, flags, sampling) and reading the raw answers. | A classification row carries `predicted_label`, not the raw answer, and the parser normalizes; greedy decoding makes the replay the same answers, checked against every row's label. |
| The run's fiche is not kept in `evidence/`; rows validate against the byte-identical `73ec536e...` fiche tracked by the named-run-profiles evidence. | Same as the terse story: a fiche JSON trips the detect-secrets hex scan. |
