---
objective: "A command takes one declared candidate model through seven verification steps, cheapest first, stopping at the first failure, and appends one tracked candidate record beside the roster file: a pass carrying every value a roster entry needs, or a refusal (or a deferral, for an architecture the pinned build does not load) naming the step, the evidence and the date; the gate itself never writes `models.json`."
status: implemented
---

# Plan: A candidate model enters the roster only through the verification gate, or leaves a recorded refusal

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | New `candidate_gate` module and `wave-local-ai-v2-candidate-gate` command: revision and file, licence, disk headroom, download and hash, one load under the probed build, template and thinking control, language claim; append-only `aidd_docs/roster/candidate-records.jsonl` |
| **Source** | `aidd_docs/backlog/stories/a-candidate-model-enters-the-roster-only-through-the-verification-gate-or-leaves-a-recorded-refusal.md` |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The gate: candidate declaration, the seven steps over injected hub/download/server seams, the record writer, the command, and the no-reasoning probe in `local_client` | [`phase-1.md`](./phase-1.md) |
| 2   | The real seams: the Hugging Face listing and licence reader, the streaming downloader, the GGUF header reader | [`phase-2.md`](./phase-2.md) |
| 3   | Docs, memory, and the live pass record for `qwen3-0.6b-q8` kept in this task's evidence | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| `https://huggingface.co/api/models/Qwen/Qwen3-0.6B-GGUF/revision/23749fefcc72300e3a2ad315e1317431b06b590a?blobs=true` | The revision endpoint returns `sha` (the resolved commit), `cardData.license` (`apache-2.0`) and `siblings[]` with `rfilename` and `size` (`639446688` for the GGUF); an unknown 40-hex revision answers `404`. The file is fetched from `https://huggingface.co/<repo>/resolve/<sha>/<path>`. |
| GGUF format (llama.cpp `gguf` spec, v3) | Header: magic `GGUF`, `u32` version, `u64` tensor count, `u64` KV count, typed KVs (13 value types, arrays nested), then per tensor: name, `u32` n_dims, `u64` dims, `u32` type, `u64` offset. Total parameter count is the sum over tensors of the product of dims. |

## Decisions

| Decision | Why |
| -------- | --- |
| The candidate is a JSON declaration file (`--candidate <path>`): `entry_id`, `repo`, `revision`, `repo_file`, `file` (path under `SLM_MODELS_DIR`, the roster's `file`), `display_id`, `quant`, `family`, `thinking_control`, `active_params_b`, `client_commercial_use`, `language_claim` (`languages`, `source_url`, optional `statement`), `server_flags`, `validated_host`. Shape errors that are not a step's subject (unknown family, missing key) exit `2` naming the field, before any step, with no record. | The six inputs the story names are not enough for a pass record to carry "every field a roster entry requires": launch flags, sampler and validated host are the author's to declare, and the load step needs them to launch. A refusal record is about the candidate, never about a typo in its declaration. |
| `thinking_control` in the declaration is a request-argument object, `"none"`, or `"allowed"`. `allowed` skips verification and the pass record's entry carries no `thinking_control` at all. | The roster accepts only an object or `"none"`; an entry with neither is exactly the one `local_client.thinking_kwargs` refuses under `disabled`, which is what "enters with `allowed` declared honestly" means for a row. |
| `client_commercial_use` is the author's reading, declared; the gate reads the licence id off the hub listing at the revision, the licence text (a `LICENSE*` file at the revision, else `README.md`), records `read_on` and `source_url`, and refuses only on a sentence that forbids publishing benchmark results (a sentence naming benchmark(s) with publish/disclose and a prohibition), quoting that sentence. A revision with no declared licence id is refused at step 2. | Licence prose is not machine-decidable in general; the one refusal the epic allows is the one the gate checks, with the clause as evidence. Order 1 authored the commercial flag the same way, by reading. |
| `active_params_b` is declared; `architecture.kind` and `expert_count` are read off the GGUF (`<arch>.expert_count`, `0` when absent => `dense`), and the total parameter count is the tensor-dim sum. | Active parameters for a MoE are not in the metadata; the roster's value is the card's nominal figure. Kind and expert count are facts the file states. |
| Step 5 refuses as outcome `deferred` when the server's stderr names an unknown model architecture, and as `refused` for any other load failure; both name the GGUF's architecture and the probed build. A port already in use, or a build `build_probe` cannot read, exits `2` with no record. | The epic's "defer by default" is about the build not implementing the architecture; an out-of-memory load is a different finding. A busy port or an unreadable binary is the host's fault, and recording it against the candidate would be a false refusal. |
| `none` is checked by one `/v1/chat/completions` generation of `THINKING_PROBE_MESSAGE` with nothing sent; a non-empty `reasoning_content`, or `<think>` in `content`, refuses. The probe lives in `local_client` as `probe_reasoning`. | The thinking story deferred exactly this check to the gate; keeping every local HTTP call in `local_client` keeps one stub point. |
| Records are JSON lines appended to `aidd_docs/roster/candidate-records.jsonl` (`--records` overrides), `record_version: 1`, each with `checked_at`/`checked_on`, `outcome`, `step` (failed step, or `null` on a pass), `evidence`, the declaration, and on a pass the `entry` block (the roster fields) plus `observed` facts (bytes, total params, GGUF architecture, build, template hash, both renders). The live run writes to a temp records path; its pass line is kept at `evidence/candidate-record-pass.jsonl`, not in the committed store. | Append-only by `open("a")`, so a second run shows both attempts. The run owner's rule keeps local-run results out of committed stores, which takes precedence over the story's "committed as the first line"; the committed file is created by the first reviewed gate run. |
| `.secrets.baseline` is not touched. | Checked rather than assumed: `detect-secrets scan` on the committed record file reports no finding (it does flag `models.json`), and the hook passes on it with the repo's exclude pattern, so there is nothing to baseline. |
