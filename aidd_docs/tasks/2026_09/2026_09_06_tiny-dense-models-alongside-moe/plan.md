---
objective: "Three tiny dense Qwen3 models are pinned in the roster, launch on this host without any MoE-offload flag, and produce classification, translation and runtime rows that sit beside the MoE flagship's own in a published side-by-side record."
status: implemented
---

# Plan: Tiny dense models compared alongside the MoE flagship

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A dense size ladder (0.6B / 1.7B / 4B) runs the two live suites and the N=5 runtime protocol on this machine, so "dense or MoE per use case" becomes an answer read off rows rather than an assumption. |
| **Source** | `aidd_docs/backlog/stories/tiny-dense-models-compared-alongside-moe.md` (story, written 2026-08-21, pre-methodology), arbitrated against the PRD's Goals and Benchmark Methodology 13 (`aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`), and the roster / fiche / verdict machinery on `main`. |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The three dense entries and their weights on this machine | [`phase-1.md`](./phase-1.md) |
| 2   | The dense launch seam and each entry's real `-ngl` | [`phase-2.md`](./phase-2.md) |
| 3   | The live runs, model by model | [`phase-3.md`](./phase-3.md) |
| 4   | The side-by-side record | [`phase-4.md`](./phase-4.md) |

## The models, and why these three

One vendor-official GGUF per size slot, all three from the same model generation, all three on an architecture this build loads:

| Slot | Entry id | Model | Repo | File | Quant | Size on disk | Revision pinned |
| ---- | -------- | ----- | ---- | ---- | ----- | ------------ | --------------- |
| sub-1B | `qwen3-0.6b-q8` | Qwen3-0.6B | `Qwen/Qwen3-0.6B-GGUF` | `Qwen3-0.6B-Q8_0.gguf` | `Q8_0` | 639,446,688 B (0.60 GiB) | `23749fefcc72300e3a2ad315e1317431b06b590a` |
| ~1.7B | `qwen3-1.7b-q8` | Qwen3-1.7B | `Qwen/Qwen3-1.7B-GGUF` | `Qwen3-1.7B-Q8_0.gguf` | `Q8_0` | 1,834,426,016 B (1.71 GiB) | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` |
| ~4B | `qwen3-4b-q4km` | Qwen3-4B | `Qwen/Qwen3-4B-GGUF` | `Qwen3-4B-Q4_K_M.gguf` | `Q4_K_M` | 2,497,280,256 B (2.33 GiB) | `bc640142c66e1fdd12af0bd68f40445458f3869b` |

**No download here is large.** 4.63 GiB for all three against 195 GiB free on `D:`, and the biggest single file is 2.33 GiB — a quarter of the 17.7 GiB the MoE flagship already cost. Expect minutes per file, not the hour that one took.

Why these:

- **The architecture loads on `b10537`.** `qwen3` is in that tag's `LLM_ARCH_NAMES` (checked against the tag's own `src/llama-arch.cpp`, see Resources) — not inferred from the family name.
- **Vendor-official GGUF, Apache-2.0, one generation.** All three repos are `Qwen/`, all three were published in May 2025 from the same Qwen3 release. The ladder therefore varies size and nothing else: same tokenizer, same post-training recipe, same chat behaviour.
- **The multilingual claim is on the card**, in the words the suites need: "Support of 100+ languages and dialects with strong capabilities for multilingual instruction following and **translation**". Both live suites are EN/FR/DE.
- **32,768 native context on all three**, which is exactly `classification_suite.CONTEXT_LENGTH` and `translation_suite.CONTEXT_LENGTH`. No entry has to publish a context cap it cannot honour.
- **The family is already known.** `roster.KNOWN_FAMILIES` holds `qwen`; each entry declares `family: "qwen"` and the judged path works unchanged the day the rewriting suite lands. A Granite or Llama pick would have needed a new family constant before its first judged row.
- **The MoE flagship is also Qwen**, so dense-vs-MoE isolates architecture rather than vendor.

Rejected, with the reason:

| Candidate | Why not |
| --------- | ------- |
| `ibm-granite/granite-4.0-350m-GGUF` / `granite-4.0-1b-GGUF` | Full Q4_K_M ladder and `granite` is a supported architecture, but IBM's sub-1B models are Granite 4.0 while its ~3B is 4.2 — no single-generation ladder — and it adds a vendor axis to a comparison whose question is dense-vs-MoE. Kept as the named follow-up if vendor diversity becomes the question. |
| `google/gemma-4-E2B-it-qat-q4_0-gguf` / `E4B` | `gemma4` loads on this build and the QAT quants are official, but MatFormer "effective parameter" naming makes a size ladder unreadable, and the repos are any-to-any multimodal — more surface than a text suite needs. |
| `unsloth/Qwen3.5-4B-GGUF` and other repackagers | Uniform Q4_K_M across all three slots, but not the vendor's own artifact, and it would mix Qwen3.5 with Qwen3 in one ladder. |
| Phi-4-mini | `phi4` is **not** in `b10537`'s architecture list (`phi3` and `phimoe` are). Not verified as loadable, so not chosen. |

## Divergences from the story

The story predates the methodology epic and its acceptance is two lines. Where it conflicts with the PRD, the shipped code or the published-evidence discipline, the plan follows those and records the conflict here.

| # | The story says | What is built instead | Why |
| - | -------------- | --------------------- | --- |
| D1 | Scored "on classification, translation, **and rewriting**" | Classification and translation only | The rewriting suite does not exist; it arrives with the provider phase of the use-case epic. Two of three use cases are covered for real, and nothing fabricates a rewriting row. The same divergence the translation plan recorded as D2. |
| D2 | "at least one tiny dense model" | Three, one per size slot | The PRD's Goal is "whichever model family performs best per use case", and one dense point cannot separate "dense wins" from "this particular small model wins". Three sizes make the axis readable at the cost of three downloads that total under 5 GiB. |
| D3 | Silent on where the rows are published | Live stores plus a dated section in `aidd_docs/results/README.md`; the committed reference bundle is **not** touched | The bundle is frozen at `schema_version` `"7"` and `tests/test_reference_bundle.py::test_every_row_carries_the_published_bundle_schema_version` asserts it. Today's rows are `"10"`. Adding them would either break that test or force the full regeneration job (every model × every suite × two runs, in a quiet thermal window) that `aidd_docs/results/README.md` and `tech-debt.md` already file as separate work. The translation suite shipped its live run exactly this way yesterday; this follows that precedent. The fiches those rows cite **are** committed, so the published numbers stay checkable. |
| D4 | Assumes the harness can launch a dense model | `settings.host_n_cpu_moe` becomes `int \| None` and `server.build_flags` omits `--n-cpu-moe` when it resolves to `None` | It cannot today: `SERVER_N_CPU_MOE` defaults to `37`, `build_flags` always emits the flag, and `roster.validate_host_fit` refuses any non-`None` value on a dense entry — correctly, per Methodology 13. The seam is the smallest change that lets a dense entry launch **without** weakening that refusal. See Decisions. |
| D5 | Silent on the cloud comparator | The existing `google` rows are cited, not re-run | The live store already holds `gemini-3.5-flash-lite` rows for classification at `suite_version` `"2"` (40 rows) and translation at `"1"` (42 rows), on the same items these dense runs use. Re-running them would pay ~6 minutes of paced quota to reproduce rows already on disk. A re-run happens only if a suite version moved. |

## Assumptions

- **"one runtime row set per model"** is read as one `wave-local-ai-v2` invocation per entry at default settings (1 warm-up + 5 counted, 10 s cooldown), not a reproduction pair. Every new entry's `verdict` will be `not_comparable` — no reference row matches on `quant` / `flags` — and that is the honest first-run state, not a gap to fill by inventing a second run this story did not ask for.
- **The quality sampler is unaffected by the entries' sampler block.** `quality_cli` pins `temperature=0` and a seed per request; the roster sampler flags shape the runtime row only. The per-model sampler values are therefore the model card's recommendation, and they change what `wave-local-ai-v2` measures, not what either suite scores.
- **`-ngl 99` is not assumed to fit.** This host is a 6144 MiB RTX 3060 Laptop (5996 MiB free). Estimated f16 KV at 32,768 context is ~3.5 GiB for the two 28-layer models and ~4.5 GiB for the 36-layer 4B; with weights that is ~4.1 / ~5.2 / ~6.8 GiB. The 4B does not fit with every layer resident, and the 1.7B is close. Phase 2 probes each entry and records the value that actually launched.

## Resources

| Source | Verified |
| ------ | -------- |
| `https://raw.githubusercontent.com/ggml-org/llama.cpp/b10537/src/llama-arch.cpp` | The architecture list this exact build loads. `qwen3`, `granite`, `granitehybrid`, `smollm3`, `gemma4`, `phi3` are present; `phi4` is not. This settles the "verify before committing to it" requirement for the chosen family. |
| `llama-server --help` from the installed `b10537` CUDA build | `--load-mode` takes `auto` (default), `none`, `mmap`, `mlock`, `mmap+mlock`, `dio`. `none` is the mode the MoE entry needs because `--n-cpu-moe` is set; a dense entry has no such need and takes `auto`. Also confirms `-ncmoe`, `--reasoning`, `--reasoning-budget` exist on this build. |
| `https://huggingface.co/Qwen/Qwen3-0.6B-GGUF` (card + file list) | Only `Q8_0` is published; context 32,768; thinking-mode sampler `temp 0.6 / top_p 0.95 / top_k 20 / min_p 0 / presence_penalty 1.5`, with `presence_penalty 1.5` explicitly recommended "for quantized models to suppress repetitive outputs". |
| `https://huggingface.co/Qwen/Qwen3-1.7B-GGUF` (card + file list) | Only `Q8_0` is published; context 32,768; same sampler guidance and the same 100+ language claim. |
| `https://huggingface.co/Qwen/Qwen3-4B-GGUF` (card + file list) | `Q4_K_M` through `Q8_0` published; context 32,768 natively (131,072 with YaRN, not used here). |
| `https://huggingface.co/api/models/Qwen/Qwen3-{0.6B,1.7B,4B}-GGUF` | The three commit shas in the model table above, read from each repo's `sha` field. |
| `nvidia-smi --query-gpu=name,memory.total,memory.free` on this host | `NVIDIA GeForce RTX 3060 Laptop GPU`, 6144 MiB total, 5996 MiB free, driver 572.70 — the ceiling the `-ngl` probe works against. |

## Decisions

| Decision | Why |
| -------- | --- |
| `Q8_0` for the two sub-2B entries, `Q4_K_M` for the 4B | It is what the vendor publishes: the 0.6B and 1.7B GGUF repos contain exactly one quant each, and the cards name it (`Quantization: q8_0`). Forcing a uniform Q4 would mean leaving the official repo for a repackager and would measure quantization damage at 0.6B rather than the model. The quant is roster data, published per row, and named in the results README so nobody reads the ladder as quant-uniform. |
| `host_n_cpu_moe` becomes "unset means read the entry", not "unset means 0" | `validate_host_fit` refuses a dense entry given **any** MoE-offload value, which is Methodology 13's rule and must keep failing loudly. Making the default `None` and resolving it from the entry's own `validated_host.n_cpu_moe` (37 for the MoE, `null` for a dense entry) keeps the MoE launch byte-identical, makes a dense launch need no `.env` juggling, and leaves an explicitly configured `SERVER_N_CPU_MOE=0` on a dense entry refusing exactly as it does today. |
| No fleet orchestrator, no runner script | `ROSTER_ENTRY_ID` already selects the entry and `load_dotenv(override=False)` means a shell-set value wins over `.env`. A documented per-entry loop in `docs/setup.md` is the whole seam; a script would have to own sequencing and failure semantics the CLIs already own. |
| `roster_version` moves `1` → `2` | The file's content changes, and a row that records `roster_version: 1` must not be ambiguous between a one-entry and a four-entry roster. Rows already published keep their `1`; nothing is back-filled. `tests/test_roster.py:379` asserts the shipped version and is updated with the bump. |
| The dense entries pin a commit sha, not `main` | Methodology 13 says "pinning its repo revision", and `main` is not a pin. The shipped MoE entry uses `main` with the sha recorded in `docs/setup.md`; the new entries put the sha in the field itself. The inconsistency is noted, not retro-fixed here. |
| The cloud comparator is the `google` rows already on disk | Same suite ids, same versions, same items, already paid for. Methodology asks that scores be comparable, not that they be re-generated per subject. |

## Risks

- **Reasoning tokens against a 32/128-token cap.** Qwen3 is a thinking-by-default family, the local quality path posts a raw prompt to `/completion` (no chat template), and the caps are 32 output tokens for classification and 128 for translation. A model that opens with a reasoning block spends the budget on it and the row lands as `truncated_max_tokens`, scoring 0. The server-side switches that would suppress it (`--reasoning off`, `--reasoning-budget 0`) act on the chat endpoint's template handling, not on `/completion`, so there is no flag fix; editing the prompt is forbidden (it moves `PROMPT_SET_HASH` and invalidates every published row). Phase 3 therefore starts with a single-model pilot before any of the matrix is paid for. If the models truncate, that is the finding — published as `failure_counts` with the reason on the row, the way the MoE's empty `<think>` envelope already is — and a tech-debt entry proposes the suite-level decision. It is not patched mid-run.
- **VRAM at 32k context.** The 4B almost certainly cannot hold every layer plus a full-context KV cache in 5996 MiB. Mitigated by the per-entry `-ngl` probe in phase 2, which is a roster field and not a code change. Lowering `context_size` instead is rejected: both suites publish a 32,768 context cap on every row, and an entry launched at 8192 would make that cap a lie.
- **Thermal state.** This machine has produced `sw_thermal_slowdown` rows before (see `aidd_docs/results/README.md`). Runtime rows carry `machine_state` and the `unreliable` flag; phase 3 runs in a quiet window and reports the flag rather than re-running until the number looks good.
- **Generation gap in the dense-vs-MoE comparison.** The dense ladder is Qwen3 (May 2025); the flagship is Qwen3.6 (2026). Size is controlled within the ladder, but the architecture comparison spans a generation. Stated in the results README rather than implied away.
- **A 0.6B model may simply be bad at FR→DE.** That is a result, not a failure. The record reports it with the per-language `score_breakdown` and its `indicative` marks intact.
