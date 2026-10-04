---
objective: "A gpu run and a cpu_only run of one model on one machine hash to two fiches, are both stored with their own flags, and are never compared as a reproduction of each other; every fiche and every row names its declared machine and compute mode."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A GPU run and a CPU-only run never share a fiche

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A tracked machine registry (the three PRD machines), `MACHINE_ID` and `COMPUTE_MODE` as required run inputs, a `cpu_only` launch that is genuinely CPU-only, `machine_id` and `compute_mode` inside a third hashed fiche projection selected by row schema "23", both fields on every row behind the writer gate, and `compute_mode` verdict-blocking with a declared-absent GPU matching itself |
| **Source** | `aidd_docs/backlog/stories/a-gpu-run-and-a-cpu-only-run-never-share-a-fiche.md`; parent epic `the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md`; owner answer Q74 (a); night-run owner decision D1 (order 0 waived) |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Machine registry, its loader, and the two required run inputs | [`phase-1.md`](./phase-1.md) |
| 2   | Fiche fields, projection "3", `cpu_only` launch and host-fit mode check | [`phase-2.md`](./phase-2.md) |
| 3   | Row fields and writer gate across the three writers, verdict blocking, declared-absent GPU | [`phase-3.md`](./phase-3.md) |
| 4   | Live proof on the laptop, docs, CHANGELOG, PRD alignment | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| `llama-server.exe --help` (b10537) | `-dev, --device <dev1,..>`: "none = don't offload"; `--op-offload/--no-op-offload` default true; `-ngl` default `auto` |
| Spike on the laptop, `qwen3-0.6b-q8`, 4001-token prompt (`evidence/spike-ngl0.log`, `evidence/spike-devnone.log`) | `-ngl 0` alone: GPU utilisation 74% during prompt processing, prompt 2227 tok/s => the CUDA build still offloads work. `-ngl 0 --device none`: GPU utilisation 0% throughout, prompt 211 tok/s => genuinely CPU-only; the process still holds a CUDA context (~107 MiB total GPU memory used, no utilisation) |
| `Get-CimInstance Win32_PhysicalMemory` / `Win32_Processor` / `Win32_OperatingSystem`, `nvidia-smi`, `kernel32!IsProcessorFeaturePresent` on the laptop (2026-10-02) | Laptop facts: 2x16 GiB, SMBIOSMemoryType 26 (DDR4), Speed 3200 and ConfiguredClockSpeed 3200, channels A and B; Ryzen 7 5800H 8 cores / 16 threads; AVX2 present, AVX-512F absent; RTX 3060 Laptop 6144 MiB, driver 572.70; Windows 11 build 26200 |

## Decisions

| Decision | Why |
| -------- | --- |
| Projection `"3"` = projection `"2"` plus `machine_id` and `compute_mode`; `row_contract.MACHINE_FICHE_SCHEMA_VERSION = "23"`; `fiche_projection_for` returns `"1"` below "22", `"2"` below "23", `"3"` from "23" (and for an unreadable version). `flags` stays outside every projection. | Q74 (a): the engine story landed first with `"2"`, so this story rebases onto it. The citing row's version picks the projection, so the committed schema-7 bundle verifies unedited and a new fiche missing `compute_mode` fails as `edited`. |
| Machine registry at `aidd_docs/roster/machines.json` (`machines.py`), keyed by machine id; every fact is `{value, source, read_from}` with `source` `declared` (read from the machine or from the PRD's machine definition, `read_from` names how) or `not_yet_declared` (value `null`, `read_from` names what it awaits). `gpu_present` must be `declared`. Ids: `laptop-mobile-gpu`, `tower-desktop-gpu`, `pro-pc-no-gpu`; a configuration change is a new id. | The engines.json `{value, source, read_from}` precedent is the repo's honesty discipline for declared values. Order 0 has recorded nothing (D1 waives it), so every tower and pro-PC fact beyond the PRD's own definition is `not_yet_declared`, never copied from untranslated operator notes. `gpu_present` decides a refusal and the verdict, so it cannot be unknown; the PRD defines it for all three. |
| `MACHINE_ID` and `COMPUTE_MODE` are read by `load_settings` with no default (`None` when unset) and validated by `settings.require_run_profile`, which the three writers call right after `load_settings`, before the roster, the build probe, the fiche or any spawn. | `load_settings` is also used by the candidate gate and the validator's no-argument form, which produce no row and must not need a machine. The `Settings` dataclass keeps `None` defaults so `tests/test_launch_byte_identical.py` constructs it unedited. |
| `cpu_only` emits `-ngl 0 --device none` and no `--n-cpu-moe`; a host `SERVER_N_CPU_MOE` under `cpu_only` is refused by `roster.validate_host_fit(..., compute_mode=...)` naming the mode; the entry's own `validated_host.n_cpu_moe` is a `gpu`-profile value and is not resolved under `cpu_only`. `server.build_flags`' `compute_mode` defaults to `None` = the entry as written (the `gpu` launch). | The spike shows `-ngl 0` alone still uses the GPU on the CUDA build; `--device none` is the additional setting (order 0's acceptance). `--n-cpu-moe 0` means the opposite of CPU-only (epic decision). The default keeps the flagship's `gpu` launch byte-identical without editing the test. |
| A row no local model produced (a cloud subject's quality row) carries `machine_id: "not_applicable"` and `compute_mode: "not_applicable"`. Runtime and local quality rows carry a declared machine id and `gpu` or `cpu_only`. | The engine precedent (`ENGINE_NOT_APPLICABLE`): a stated non-applicability, never a null. The cloud model was not produced on a declared machine. |
| The local-row fields are carried as one "local producer" mapping (`quality_rows.local_producer_fields`: engine id and build, machine id, compute mode) replacing `local_engine_fields`, and `NO_LOCAL_PRODUCER_FIELDS` replacing `ENGINE_NOT_APPLICABLE_FIELDS`. | One mapping already flows into every row writer and both `--resume` checks; extending it makes a resume under another machine or mode refuse with no new plumbing. |
| `compute_mode` joins `verdict._RUNTIME_BLOCKING_FIELDS`. A `gpu_name` that is null on a fiche whose machine the tracked registry declares GPU-less reads as `declared_absent`, which matches itself; a null `gpu_name` on any other fiche still never matches. `machine_id` is not added to the blocking fields. | Story acceptance. M8 says CPU, RAM, driver and OS never block; the machine id carries those, so adding it would contradict M8 beyond what the story asks. |
| Along the comparison's `model` dimension, `machine_id` and `compute_mode` join the engine fields that move with the axis between a local and a cloud side. | A cloud side states `not_applicable` for both by construction; between two local sides a different machine or mode stays a confound. |
| The read model lists `machine_id` and `compute_mode` as not rendered. | The epic excludes rendering the machine dimension (the pitch epic owns the views); the partition test requires every contract field to be placed. |
| PRD alignment recorded (epic `→ PRD` rows): Methodology 14's "the same configuration hashes identically on a second machine" still holds because a machine id names a declared configuration, not a box; Methodology 8's "shares the re-run's normalised fiche hash" diverges from the code's blocking-field match, and `compute_mode` is now in both. | Acceptance: the alignment is recorded, not assumed. The PRD itself is not edited by an implementer. |
| Live evidence goes to this task's `evidence/` folder (results, reference and fiche registry paths), not the live store the story names. | Night-run rule: no results path into the repo's stores. Reported as a backlog contradiction. |
