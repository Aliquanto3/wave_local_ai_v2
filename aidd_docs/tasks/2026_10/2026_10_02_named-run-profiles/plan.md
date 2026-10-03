---
objective: "Every (roster entry x machine x compute mode) runs under a named run profile resolved from a tracked registry through the one flag builder; validated_host leaves the roster; every row and fiche names its profile and any operator override."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Each model, machine and mode runs under its own named profile

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A tracked run profile registry (`aidd_docs/roster/profiles.json`, `profiles.py`) with per-(machine, mode) defaults and per-entry overrides, one resolution order (entry default, profile, operator override), `server.build_flags` taking the resolved profile, `validated_host` removed from the roster, `profile_id` and `profile_overrides` on every row (schema "26") and `profile_id` on the fiche outside the hashed projection |
| **Source** | `aidd_docs/backlog/stories/each-model-machine-and-mode-runs-under-its-own-named-profile.md`; parent epic `the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md`; night-run owner decisions D1 and D4 |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Profile registry, loader and resolver with its refusal | [`phase-1.md`](./phase-1.md) |
| 2   | `validated_host` moved into profiles; `build_flags` and host-fit on the resolved profile; byte-identical launch held | [`phase-2.md`](./phase-2.md) |
| 3   | Profile id and override record on fiche and rows across the three writers | [`phase-3.md`](./phase-3.md) |
| 4   | Docs, CHANGELOG, one laptop run per mode | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| D4 (owner, 2026-10-03): `tests/test_launch_byte_identical.py` is edited only so it takes its values from the resolved (MoE flagship, `laptop-mobile-gpu`, `gpu`) profile and passes that profile to `server.build_flags`; `BASELINE_FLAGS` and every expected flag string stay byte-for-byte unchanged. | Resolves the acceptance conflict between "`validated_host` leaves the roster" and "`tests/test_launch_byte_identical.py` unedited": the test read `entry.validated_host`, which can no longer exist. The launch guarantee is what the test protects, and it is held. |
| D1 (owner, 2026-10-02): tower and professional-PC values nobody has read are declared `not_yet_declared` with what they await, never invented. A run under a profile with an undeclared value refuses before any server starts, unless the operator overrides that value, which the row then records as an override. | The machine registry's honesty discipline (`{value, source, read_from}`) applied to profile values. The pro PC declares `cpu_only` only; laptop and tower declare `gpu` and `cpu_only`. |
| Registry shape: `defaults[machine_id][mode]` holds `n_gpu_layers`, `n_cpu_moe`, `threads`, each `{value, source, read_from}` or absent (absent = the roster entry's own default, or no flag); `entries[entry_id][machine_id][mode]` overrides single values and may only name a declared (machine, mode). The declared profile set of an entry is every declared (machine, mode). | Acceptance line 1: a fifth roster entry needs no hand-written profile. Of the four current entries only the flagship overrides anything (its laptop `gpu` `n_cpu_moe` 37), so the epic's "per-entry values everywhere" finding did not occur. |
| Profile id is `<entry_id>@<machine_id>/<compute_mode>`, built by the resolver. | One deterministic name per triple; the fiche carries it outside the hash, so a rename never moves a hash (tested on constructed fiches). |
| `cpu_only` defaults declare `n_gpu_layers` 0 and may not declare `n_cpu_moe` (refused at load); `--device none` stays emitted by the mode itself (`server.CPU_ONLY_DEVICE_FLAGS`). A `cpu_only` profile resolving any other `-ngl` is refused at load. | Epic decisions "`-ngl` ownership" and "`--n-cpu-moe` under `cpu_only`"; story 1's spike shows `--device none` is what makes the mode CPU-only. |
| `server.build_flags(entry, profile, model_path, *, engine=None)`: the profile is a required argument, so no caller can fall back to the laptop's values. `roster.validate_host_fit(entry, profile)` reads the resolved profile. | Owner instruction with D4; acceptance line 3. |
| `SERVER_N_CPU_MOE` and `SERVER_THREADS` both become unset-means-`None` operator overrides; `DEFAULT_HOST_N_CPU_MOE` and `DEFAULT_HOST_THREADS` are removed. A row's `profile_overrides` maps each overridden value to `{"profile": <profile value or null>, "operator": <value>}`; `{}` when none. | Acceptance line 5: a row never claims a profile it did not run under. A default thread count of 8 would be a laptop value silently reused on another machine. |
| Row schema "26": `profile_id` and `profile_overrides` required on both row kinds from "26"; a cloud subject's quality row states `"not_applicable"` for both. Rows below "26" are never back-filled. | Same discipline as `machine_id` / `compute_mode` (schema "23"). |
| Candidate gate: the declaration's `validated_host` becomes `load_profile` (`n_cpu_moe`, `threads`), used to build an explicit profile for the gate's one load (`<entry_id>@candidate-gate/gpu`), and is not copied into the passed entry block. | The gate's passed block is the author's to copy into `models.json`, which no longer carries `validated_host`; the gate runs on no declared machine and writes no row. |
| `roster.build_flags_from_entry` is kept. | The story removes it only if the resolver makes it dead; it already had no production caller, and the resolver does not change that. |
| `roster_version` 4 -> 5; `profiles.json` `registry_version` 1. | Acceptance line 4 / "Code it changes". |
| Live evidence goes to this task's `evidence/` folder, never the committed stores. | Night-run rule. |
