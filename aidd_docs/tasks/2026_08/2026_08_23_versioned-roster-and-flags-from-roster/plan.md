---
objective: "A tracked, versioned roster file pins every model's identity and flag set, and the server flags, model file and llama.cpp build come from that roster and host settings instead of source constants."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A versioned roster pins every model, and flags/build come from it

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Ship `aidd_docs/roster/models.json` with one validated entry, resolve the server flag set, model file and llama.cpp build through it and host settings instead of source constants, and prove the launched command stays byte-identical to today's validated baseline. |
| **Source** | `aidd_docs/backlog/stories/a-versioned-roster-pins-every-model.md` (order 12), `aidd_docs/backlog/stories/flags-model-and-build-come-from-the-roster-not-from-source.md` (order 13); authority: PRD Methodology criteria 13 and 14, epic `every-published-row-explains-and-reproduces-itself.md` |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ----------------------------- |
| 1   | Roster file and validation | [`phase-1.md`](./phase-1.md) |
| 2   | Server, CLIs and build probe resolve through the roster | [`phase-2.md`](./phase-2.md) |
| 3   | Byte-identical proof and documentation | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `llama-server.exe --version` run live on this machine against the pinned `b10537` binary at `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe` | Prints to **stderr**, exit code 0, no stdout: `version: 0.1.2-dev (build 10537, commit bf0040e15)` then `built with Clang 20.1.8 for Windows x86_64`. `build_probe.py` must read stderr and match `build (\d+)`, formatting the id as `b<number>` to match the `LLAMA_CPP_BUILD = "b10537"` convention it replaces. |
| `context_input/baseline_qwen36.md` | Validated command: `-m <gguf> -ngl 99 --n-cpu-moe 37 -c 32768 -fa on -t 8 --jinja -np 1 --load-mode none --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5 --host 127.0.0.1 --port 8080`. Model: `unsloth/Qwen3.6-35B-A3B-GGUF`, file `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf`. Architecture: 40 MoE layers exactly (`--n-cpu-moe 40` = ceiling, "tous les experts en RAM"), hybrid Gated DeltaNet + Gated Attention, `--load-mode none` mandatory with `--n-cpu-moe`, `--min-p 0` explicit, `--jinja` mandatory. |
| `context_input/model_candidates.md` | Qwen3.6-35B-A3B: 35B total / 3.1B active parameters, MoE, matches `docs/setup.md`'s pinned repo/revision/checksum. |
| `docs/setup.md` (step 3) | Repo `unsloth/Qwen3.6-35B-A3B-GGUF`, revision `main` (commit `a483e9e6cbd595906af30beda3187c2663a1118c` at time of writing), file `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf`, sha256 `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3` — the roster's first entry must match every one of these fields verbatim. |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision | Why |
| -------- | --- |
| Split the flag set: model-intrinsic flags (`-ngl`, `-c`, `-fa`, `--jinja`, `-np`, `--load-mode`, the sampler flags, the quant file) live in the roster entry's own flag set; only `--n-cpu-moe` and `-t`/threads are host settings (`settings.py`/`.env`), defaulted to today's validated values (37, 8). | Story 13's byte-identical acceptance only holds with host defaults equal to the validated baseline; splitting lets a second machine override the two values that are actually host-dependent without editing source or the roster. |
| The roster entry also records a `validated_host` block (`n_cpu_moe: 37`, `threads: 8`, a one-line `fiche_summary`) alongside its flag set. | Makes the byte-identical claim checkable without cross-referencing `context_input/baseline_qwen36.md`: the entry states the host values it was validated under, and a test can assert the settings defaults equal `validated_host`. |
| The dense-vs-MoE rule and the expert-count ceiling are validated at launch against the **host** `n_cpu_moe` value, not a value stored per roster entry — `--n-cpu-moe` is no longer roster data after the split. | A dense entry combined with a non-null host `n_cpu_moe` is refused; an MoE entry is refused when the host value exceeds `architecture.expert_count`. This is the "architecture field makes the rule checkable" mechanism Methodology 13 asks for, applied to the value that now actually carries `--n-cpu-moe`. |
| `build_probe.py` parses `llama-server --version`'s **stderr** (verified live on this machine, see Resources), extracting the build number and formatting it as `b<number>`. Any subprocess failure or unmatched output yields `None`, never a raised exception and never an assumed value. | Matches Methodology 14 / story 13's "a build that cannot be read is an explicit null, never an assumed value." |
| Criterion 14's fiche SHA-256 hashing (the normalised-projection hash, invalidation on fiche edit) is **not** implemented here. | Neither story's acceptance or "Code it changes" list names a hash computation or an invalidation validator; only the roster-entry-id/roster-version citation and the flags/model/build resolution are in scope. The epic assigns full criterion 14 hashing to a later story; this plan only stops citing a filesystem-path-flattened fiche in a way that would block it. |
| `roster.py`'s contract-field work (phase 1) populates `roster_entry_id`/`roster_version` on every row from the start, even though the flags themselves don't resolve through the roster until phase 2, so `tests/test_cli.py` and `tests/test_quality_cli.py` (which call `_run()` end to end against a stubbed server) stay green after phase 1. | Keeps every phase independently shippable and test-green, per the plan's own phase contract, without changing story 12's scope (it already lists the contract fields as its own deliverable). |
