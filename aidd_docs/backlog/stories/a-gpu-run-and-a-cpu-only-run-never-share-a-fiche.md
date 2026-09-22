---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/the-professional-pc-is-confirmed-able-to-take-part-before-code-depends-on-it.md
order: 1
---

# Story: A GPU run and a CPU-only run never share a fiche

**As** a client-side engineer checking a reproduction verdict
**I want** every fiche and every row to name the declared machine and the compute mode that produced it, both inside the fiche's hashed identity
**So that** a `cpu_only` run can never be stored under a `gpu` run's fiche, and a GPU run and a CPU run are never compared as a failed reproduction of each other

Maps to: PRD AC "Given a runtime record, it always references a hardware fiche..."; PRD AC "Given a GPU-bearing machine, running a declared `cpu_only` profile... never compared against the same machine's `gpu` rows as a reproduction"; PRD AC "Given a published run, a re-run of it returns an explicit verdict..."; Methodology 8, 14, 21.

Blocks every other story in this epic. Today `-ngl 99` and `-ngl 0` hash identically (`hardware.py:44-55` excludes `flags` and carries no mode), `fiche_registry.write_fiche` is write-once by hash (`fiche_registry.py:42`), so a `cpu_only` run's fiche is never stored, the `gpu` fiche stands in for it, `verify_fiche` still reports `ok`, and `verdict.select_runtime_reference` reads one stored flag list for both rows and returns a throughput verdict between a GPU run and a CPU run.

## Acceptance

- **A declared machine registry exists**: one tracked, English entry per target machine, the three PRD machines first, keyed by a stable machine id that names a declared **configuration** (a RAM upgrade or GPU swap is a new id). Each entry carries the facts order 0 recorded and the fiche cannot capture: memory type, rated and configured speed, whether a GPU is present, allocatable VRAM where it differs from nominal, CPU core count and the instruction-set notes. Each declared value is marked declared, under the same honesty discipline as the energy method labels. [PRD M21; epic decision "Memory type and speed"]
- **Machine and mode are required run inputs, never defaults.** A run with no machine id, or one naming an undeclared id, refuses before any server starts and names the declared ids. A run with no compute mode refuses naming `gpu` and `cpu_only`. A `gpu` run on a machine declared GPU-less refuses naming the machine. [PRD M21 "never as a fallback"]
- **`cpu_only` changes the launch.** It emits the CPU-only flag set order 0 observed to be genuinely CPU-only (at least `-ngl 0`), emits no `--n-cpu-moe`, and a `--n-cpu-moe` value supplied under `cpu_only` is refused by the host-fit check naming the mode, never dropped silently. A `gpu` launch of the MoE flagship stays byte-identical to today's (`tests/test_launch_byte_identical.py` passes unedited). [epic decision "`--n-cpu-moe` under `cpu_only`"]
- **`compute_mode` and `machine_id` are on every fiche and inside its hashed projection**, alongside the existing keys; `flags` stays outside it, as Methodology 14 requires. Two runs of one model on one GPU-bearing machine, one `gpu` and one `cpu_only`, produce two different `fiche_hash` values and two stored fiches, each carrying its own flag list. [PRD M14; epic success check 1]
- **Every row names both**: runtime rows and local quality rows carry `machine_id` and `compute_mode`; the writer gate refuses a row missing either and a row whose `machine_id` is not a declared entry. A row no local model produced (a cloud subject's quality row) never carries `gpu` or `cpu_only`: it states that compute mode does not apply. [PRD M21 "every fiche and every row names which one produced it"]
- **Compute mode is verdict-blocking.** A `cpu_only` candidate against a `gpu` reference, same machine, same model, returns `not_comparable` with `compute_mode` among the differing fields, never `reproduced` or `not_reproduced`. It is added to both definitions the epic names (the hashed projection and `verdict._RUNTIME_BLOCKING_FIELDS`), so whichever one a later reader follows, the rule holds. [PRD M8]
- **A declared-absent GPU is not an unknown GPU.** Two `cpu_only` runs on the no-GPU machine with equal build, quant, flags and mode can reach `reproduced`; the null-never-matches rule still holds for a GPU field that *failed to capture* on a machine that declares one. Without this, every row the professional PC ever publishes would be permanently `not_comparable`, which is a degraded row by another name. [PRD AC "rows appear... as ordinary rows... rather than marked as degraded"; PRD M8]
- **The committed bundle still verifies, and nothing in it is edited.** Which projection a stored fiche is verified under is decided by the `schema_version` of the row citing it (the `FICHE_HASH_SCHEMA_VERSION` precedent in `row_contract.py`), never by a field happening to be absent from the fiche, so a new fiche that forgets `compute_mode` cannot pass as an old one. Regeneration is deferred to order 6, once, under the epic's final schema.
- The PRD alignment the epic marked `→ PRD` is recorded, not silently assumed: Methodology 14's "the same configuration hashes identically on a second machine" still holds because a machine id names a declared configuration, and Methodology 8's "shares the re-run's normalised fiche hash" versus the code's four blocking fields is named as the divergence it is, now with `compute_mode` in both.

## Code it changes

- New tracked machine registry (proposed `aidd_docs/roster/machines.json`, beside `models.json`) and its loader, refusing an entry missing a required field the way `roster.load_roster` does.
- `settings.py`: machine id and compute mode, required, validated against the registry; `.env.example` and `docs/setup.md` §4 gain both.
- `hardware.py`: `Fiche` gains `machine_id`, `compute_mode`; `_NORMALISED_KEYS` gains both; the legacy projection kept for rows below the new schema version.
- `fiche_registry.py` / `fiche_validator.py`: verification under the citing row's projection.
- `server.py` (`build_flags`) and `roster.py` (`validate_host_fit` gains the mode).
- `verdict.py`: `compute_mode` blocking; declared-absent GPU handling.
- `row_contract.py`: both fields required, `SCHEMA_VERSION` bumped with its history comment.
- The three fiche writers: `__init__.py`, `quality_cli.py`, `judge_probe.py`.
- `CHANGELOG.md` Unreleased; `aidd_docs/memory/architecture.md` if the fiche's description there moves.

## Tests it needs

- `tests/test_hardware.py`: `gpu` and `cpu_only` fiches of one machine hash differently; two machine ids with identical captured fields hash differently; key order still irrelevant.
- `tests/test_fiche_registry.py`: the two fiches are both stored, each with its own `flags`.
- `tests/test_verdict.py`: the mode-mismatch pair is `not_comparable` naming `compute_mode`; two `cpu_only` runs on a declared no-GPU machine can reproduce; a GPU field that failed capture on a GPU-declaring machine still never matches.
- `tests/test_server.py` / `tests/test_roster.py`: the `cpu_only` flag set, no `--n-cpu-moe`, refusal of a supplied one; `tests/test_launch_byte_identical.py` unedited and green.
- Settings and registry tests: missing and undeclared machine id, missing mode, `gpu` on a GPU-less machine.
- `tests/test_row_contract.py` and `tests/test_reference_bundle.py`: the new fields required from the new version; the committed schema-7 bundle still passes `test_every_cited_fiche_still_hashes_to_its_own_name` with no file edited.

## Evidence it publishes

- The epic's success check 1, run for real on the laptop: two runtime runs of `Qwen3-0.6B`, one per mode, their two `fiche_hash` values, the two stored fiches' `flags`, and the second row's `not_comparable` verdict naming `compute_mode`. Recorded in the plan's evidence file; the rows stay in the live store (the bundle is republished once, in order 6).

## Plan shape

1. Machine registry, its loader, and the two required settings with their refusals.
2. Fiche fields, hashed projection, schema-version-selected verification; `cpu_only` flag set and host-fit mode check.
3. Row fields and writer gate across the three writers; verdict blocking and declared-absent GPU.
4. Live proof on the laptop, docs, CHANGELOG, PRD alignment note.

## Cancellation

n/a — not cancelled.
