---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/a-gpu-run-and-a-cpu-only-run-never-share-a-fiche.md
order: 3
---

# Story: Each model, machine and mode runs under its own named profile

**As** the consultant running one roster on three machines
**I want** the host-fitted launch settings declared per (roster entry x machine x compute mode) as named run profiles, resolved through the one existing flag builder
**So that** one model on two machines, or on one machine in two modes, is two named profiles rather than one laptop's settings silently reused, and a second machine is configured by the repo rather than by editing `.env` per run

Maps to: PRD AC "Given a roster model, a target machine and a compute mode, a run profile exists for that (model x machine x mode) triple and every row and fiche it produces names that profile and that mode"; Methodology 13, 21.

Current state: every roster entry carries one `validated_host` block (`n_cpu_moe`, `threads`, and the same free-text `fiche_summary` on all four entries, `aidd_docs/roster/models.json`), and `SERVER_N_CPU_MOE` / `SERVER_THREADS` apply process-wide to whichever entry runs (`settings.py:159-165`, `server.py:66-87`). There is no key by which a value could be per machine.

## Acceptance

- A tracked run profile registry declares profiles keyed by (roster entry, machine, compute mode). Profiles resolve from per-(machine, mode) defaults and are overridden per entry only where a model needs it, so a fifth roster entry needs no hand-written profile unless it differs. If the four current entries turn out to need per-entry values everywhere, that is recorded as the finding the epic predicted, not worked around. [epic Unknowns "Roster growth multiplies profiles"]
- The declared set covers the three machines: `gpu` and `cpu_only` on the laptop and the tower, `cpu_only` only on the professional PC. A run whose triple has no declared profile refuses before any server starts, naming the triple and the profiles that do exist for that entry. [PRD AC run profile per triple]
- One resolution order, stated once in code and once in `docs/setup.md`: roster entry default, then profile, then explicit operator override. `server.build_flags` stays the only flag builder; `-ngl` is overridden by the profile, the roster keeps the model-intrinsic default. [epic decision "`-ngl` ownership"]
- `validated_host` leaves the roster: its thread count and `--n-cpu-moe` move into the laptop's `gpu` profiles, and `fiche_summary` is replaced by the machine registry entry. Two places to read a thread count from is one too many. [epic Boundaries]
- `SERVER_N_CPU_MOE` and `SERVER_THREADS` remain as operator overrides, applied last. A row launched with an override names that it deviated from its profile and which values it overrode, so a row never claims a profile it did not run under.
- Every fiche and every row names its profile id. The profile id is evidence on the fiche like `flags`, outside the hashed projection: the flags a profile produces are already on the fiche, and a renamed profile must not move a hash.
- The MoE flagship's laptop `gpu` profile launches byte-identically to today's baseline (`tests/test_launch_byte_identical.py` unedited and green): the move from roster to profile changes where the values live, not what is launched.

## Code it changes

- New tracked profile registry (proposed `aidd_docs/roster/profiles.json`) and its loader and resolver.
- `roster.py`: `validated_host` removed from `REQUIRED_FIELDS` and the entry; `validate_host_fit` reads the resolved profile; `roster_version` bumped. Removing `build_flags_from_entry` (tech-debt row 2026-08-23, no production caller) is in scope only if the resolver makes it dead.
- `server.py` (`build_flags` takes the resolved profile), `settings.py` (overrides reframed as overrides).
- `aidd_docs/roster/models.json`; `hardware.py` (`profile_id` on the fiche, not hashed); `row_contract.py` (`profile_id` and the override record, `SCHEMA_VERSION` bumped).
- The three writers (`__init__.py`, `quality_cli.py`, `judge_probe.py`).
- `docs/setup.md` §4, `.env.example`, `CHANGELOG.md`.

## Tests it needs

- Resolver: entry default, profile override, operator override, in that order; per-(machine, mode) default used when no per-entry profile exists; missing triple refused naming the triple.
- `tests/test_roster.py`: a roster without `validated_host` loads; the new `roster_version` is read.
- `tests/test_server.py`: the laptop and tower `gpu` profiles for the flagship produce different `-t` / `--n-cpu-moe`; a `cpu_only` profile never emits `--n-cpu-moe`; `tests/test_launch_byte_identical.py` unedited and green.
- Writer tests: every row and fiche names its profile; an overridden run names its override.
- `tests/test_hardware.py`: renaming a profile does not move `fiche_hash`.

## Evidence it publishes

- The declared profile set itself, as the tracked registry, and a table in `docs/setup.md` naming, per machine, which modes are declared and which values each profile sets.

## Plan shape

1. Profile registry, loader and resolver with its refusal.
2. `validated_host` moved into profiles; `build_flags` and host-fit on the resolved profile; byte-identical launch held.
3. Profile id and override record on fiche and rows across the three writers.
4. Docs, CHANGELOG, one laptop run per mode showing its profile on the row.

## Cancellation

n/a — not cancelled.
