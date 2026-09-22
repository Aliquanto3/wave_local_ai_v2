---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/each-model-machine-and-mode-runs-under-its-own-named-profile.md
order: 4
---

# Story: A model below its declared minimum refuses, and the refusal is published

**As** someone planning local AI on a 16 GB office PC
**I want** a model that does not fit a machine in a mode to refuse before it starts, naming the requirement it failed, and that refusal to be published
**So that** "this model will not run on your office PC, for want of RAM" is a result I can read, not a blank cell and not a quietly degraded run

Maps to: PRD AC "given a combination below the model's declared minimum for that mode, the run refuses to start naming the requirement and the mode that failed, no runtime row is produced, and no smaller quant, shorter context or CPU-only path is substituted on the harness's own initiative"; Methodology 21; epic decision "A refusal is published"; epic success check 2.

Current state: no roster entry declares a RAM, VRAM or disk requirement; they exist only as README prose ("32 GB system RAM", "~18 GB free disk", `README.md:39-46`) that no code reads.

## Acceptance

- Each roster entry declares, per compute mode, a minimum RAM, VRAM (for `gpu` only) and disk requirement. The first declarations are calibrated from peaks the published rows already carry (15.2 GB RSS for the flagship, 1.1 GB for the 0.6B, `README.md:48-52`), with the source of each number recorded beside it; none is invented. That a declaration can be wrong is stated in `docs/setup.md`: a too-low one surfaces as a run that starts and then fails. [epic decision "Requirements are declared, not verified"]
- A pre-flight check compares the requirement against what the machine reports (total RAM, allocatable VRAM from the machine's declared entry where it differs from nominal, free disk on the models volume when the weights are not already present) **before the weights are looked for and before `llama-server` starts**, so the professional PC can refuse the flagship without downloading 18 GB of weights it cannot run.
- A refusal names the requirement, the mode, the declared minimum and the observed value, exits non-zero, and writes no runtime or quality row. [PRD AC]
- The check tests the declaration, not the machine: a profile whose minimum is raised above the machine refuses, and the same profile lowered below it runs. [epic success check 2]
- Nothing is substituted: no smaller quant, no shorter context, no switch from `gpu` to `cpu_only`. A refused `gpu` run tells the operator that a `cpu_only` profile exists if one does, and runs nothing.
- Every refusal writes one refusal record: roster entry, machine id, compute mode, profile id, the failed requirement with its declared and observed values, the code's release version and commit sha, and a timestamp. It is never a runtime row, never read by any runtime view as one, and lives in its own tracked per-machine file so order 5's transport carries it with the rows. [epic Boundaries "a published record of every refusal"]

## Code it changes

- `aidd_docs/roster/models.json` (or the profile registry, whichever order 3 made the home of per-mode data): requirements with their calibration source.
- `roster.py` or the profile loader: requirement fields required and validated.
- A pre-flight module called from the three writers (`__init__.py`, `quality_cli.py`, `judge_probe.py`) ahead of weight resolution and server launch.
- A refusal writer, following `results.append_row`'s shape but writing to its own file with its own small contract in `row_contract.py`.
- `settings.py` for the refusal file path; `docs/setup.md` (the requirement table replaces the README prose it supersedes, and `README.md:35-62` points to it); `CHANGELOG.md`.

## Tests it needs

- Pre-flight: each of RAM, VRAM and disk refusing alone, naming itself and the mode; raised-declaration refuses and lowered-declaration passes on the same stubbed machine; the check runs before the model path is resolved (a missing weights file does not mask a RAM refusal).
- Writers: a refused run exits non-zero, writes no row, writes exactly one refusal record carrying every field; no substitution path exists (a refused `gpu` run never launches `cpu_only`).
- Requirement loader: a missing requirement field is refused like any other missing roster field.

## Evidence it publishes

- The requirement table in `docs/setup.md`, with each declaration's calibration source.
- One real refusal on the laptop with a deliberately raised declaration, its refusal record, and the same profile running once the declaration is restored: recorded in the plan's evidence file.

## Plan shape

1. Declared requirements and their loader, calibrated from published peaks.
2. The pre-flight check and its placement ahead of weights and launch in the three writers.
3. The refusal record, its contract and its per-machine file.
4. Docs, CHANGELOG, the raised-then-lowered live proof on the laptop.

## Cancellation

n/a — not cancelled.
