---
objective: "Every runtime row and every local quality row names a registered engine and its live-probed build, the fiche hashes the engine identity and a path-free engine configuration hash, and every fiche already committed still verifies under the projection its citing row's schema version selects."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Every row names the engine that produced it, and the fiche hashes it

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A tracked engine registry (`llama.cpp`, reference, `spawned`) drives the launch host/port, the build probe and the thinking switch; the fiche gains `engine_id`, `engine_build`, `engine_config_hash` inside a second hashed projection selected by row `schema_version` "22"; rows carry `engine_id`/`engine_build` and the writer gate refuses an unregistered engine |
| **Source** | `aidd_docs/backlog/stories/every-row-names-the-engine-that-produced-it-and-the-fiche-hashes-it.md`; owner answers Q20 (a) and Q74 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Engine registry and its loader | [`phase-1.md`](./phase-1.md) |
| 2   | Fiche generalised, two projection versions, verdict blocking fields | [`phase-2.md`](./phase-2.md) |
| 3   | Launch, build probe and thinking switch read from the entry | [`phase-3.md`](./phase-3.md) |
| 4   | Row fields, writer gate, schema 22, writers, resume check, comparison axis, read model, export, docs | [`phase-4.md`](./phase-4.md) |
| 5   | Live evidence on `qwen3-0.6b-q8` | [`phase-5.md`](./phase-5.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| `llama-server.exe --help` (b10537) | Defaults not reported by `/props`: `-b` 2048, `-ub` 512, `-ctk`/`-ctv` f16 => the registry's `declared` defaults |
| `GET /props` on b10537 with `qwen3-0.6b-q8` loaded (no sampler flags) | `default_generation_settings.params` reports `samplers` order, `repeat_penalty` 1.0, `dry_multiplier` 0.0, `n_predict` -1; `build_info` `b10537-bf0040e15` => the registry's `engine_reported` defaults |

## Decisions

| Decision | Why |
| -------- | --- |
| The hashed projection is versioned in `hardware.FICHE_PROJECTIONS` (`"1"`: the legacy ten keys with `llama_cpp_build`; `"2"`: `engine_id`, `engine_build`, `engine_config_hash` in its place). `row_contract.fiche_projection_for(schema_version)` selects `"2"` from `ENGINE_FICHE_SCHEMA_VERSION = "22"` up and `"1"` below; `fiche_registry.verify_fiche` takes the citing row's `schema_version` as a required keyword. An unparseable version selects the current projection. | Story acceptance and Q74 (a): the projection is chosen by the citing row's version, never by an absent field, so a new fiche missing an engine key fails as `edited` instead of passing as an old one. Naming it a projection version is what lets the machine story rebase onto `"2"` (Q74). Committed fiches are untouched and keep verifying under `"1"`. |
| `tests/test_reference_bundle.py` passes each citing row's `schema_version` to `verify_fiche` (one call site changed, no bundle file edited). | A required keyword is the only way a caller cannot silently verify under the wrong projection; a defaulted argument would pick a projection by omission. |
| Q20 (a): `engine_config_hash` enters the projection. For llama.cpp it is SHA-256 over the launch flag list with the `-m` value replaced by `roster:<roster_entry_id>` and the `--host`/`--port` pairs removed; both spellings are registry data (`config_normalisation`). Raw `flags` stay outside the projection. | Path-free and location-free (Methodology 14); host and port must stay outside the hash per the acceptance, and they are part of the flag list. |
| A legacy fiche (no `engine_id`) read by the runtime verdict counts its absent engine fields as null: null never matches, so a schema-22 run against the schema-7 reference is `not_comparable` naming `engine_build`/`engine_id`. | Reading a legacy `llama_cpp_build` as `engine_build` would back-fill an engine nobody recorded; the bundle is republished by the campaign story, not here. |
| A row no local engine produced carries `engine_id: "not_applicable"` and `engine_build: null` (`row_contract.ENGINE_NOT_APPLICABLE`); locality is read from `provider == "local"`. Both keys are required on every quality row and every runtime row. | The acceptance asks the row to *state* that the engine does not apply; a null id would read as `null_in_row` absence in the read model. The machine story has not landed, so this sets the precedent it names. |
| The registry's entry id is its key (no inner `engine_id`), the roster's convention. Exactly one entry is `reference: true`. | Mirrors `roster.load_roster`; a duplicated id inside the entry could disagree with its key. |
| The engine's `thinking_switch` is `{"request_field": "chat_template_kwargs"}` or `"none"`. `local_client.check_engine_carries` refuses an object roster control the engine cannot carry: one spelled in another top-level field, or any object control on an engine declaring `"none"`. `thinking_kwargs` calls it, so a `disabled` batch is refused before any generation; the candidate gate calls it in its `thinking_control` step, before any render. A roster `none` entry (a model that does not reason) still runs `disabled` on any engine, sending nothing. A declared switch whose render does not change refuses the batch, as the done thinking-control story requires. Rows always publish the suite's own `thinking_policy`; the parked `effective_thinking_policy` downgrade (`disabled` to `allowed`) is removed. | Owner amendment 44c8953: "a declared switch that renders no difference refuses the batch before any generation; an engine that offers no switch declares `none`, checked by the candidate gate", on Methodology 3 (the policy is the suite's, identical across models). Downgrading a `disabled` suite's rows to `allowed` on one engine would make the policy differ across rows of one suite. The epic's decision row still says such rows "declare `allowed` honestly"; the story's amended acceptance governs here. |
| `engine_id` and `engine_build` are owed only from schema "22" (`row_contract.ENGINE_FIELDS`, gated by `ENGINE_FICHE_SCHEMA_VERSION`): a row below "22" validates without them and is not held to the registry. | The "19", "20" and "21" precedent; the committed bundle and every row written before this story stay valid unedited. |
| Along the comparison's `model` dimension, `engine_id` and `engine_build` are axis fields only when one side is a local subject and the other a cloud one (`comparison._axis`, read from `provider`); between two local sides a differing engine or build is a confound, so the member is an observation naming it. The `prompt_variant` dimension is unchanged (the engine stays a confound there). | A local-versus-cloud model comparison differs on the engine by construction, as on `provider` and `subject_egress`, and must stay a test. Two local models on different engines or builds would otherwise publish a model difference that is partly an engine difference (epic: the engine is its own dimension). |
| `--resume` (quality CLI and judge probe) compares `engine_id` and `engine_build` with the rows already written: the local batch against this invocation's probed engine fields, each cloud batch against `not_applicable` / null. The resume check now runs after the build probe (a `--version` call) and still before the fiche, any server spawn or any row is written. | A batch resumed under another engine build would publish one score over two builds, the class of mix the resume check exists to refuse. |
| The engine registry lives at `aidd_docs/roster/engines.json` (cwd-relative default, like the roster) with no new environment variable; the writer gate reads the registered ids through a cached load of that file. | The story proposes the path; every other tracked-data default in `settings.py` is cwd-relative. |
| The candidate gate's own `llama_cpp_build` observed field (candidate records) is left as is. | It is a candidate-record field, not a fiche field; renaming it would rewrite the meaning of committed records. |
| The implementation parked at `c0fdfef` (written on `2af06fc`) was brought onto the current head as a patch and its conflicts resolved; its row schema "16" is renumbered "22" everywhere ("16" to "21" were taken by later stories). Projection `"2"` is this story's: the GPU/CPU fiche story has not landed, so per Q74 (a) it rebases onto `"2"`. | The rows "16" to "21" already define other fields; the projection number is independent of the row schema number. |
