---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/a-gpu-run-and-a-cpu-only-run-never-share-a-fiche.md
  - aidd_docs/backlog/stories/a-model-below-its-declared-minimum-refuses-and-the-refusal-is-published.md
order: 5
---

# Story: Each machine returns its rows by pull request, and a hash collision is refused

**As** the maintainer assembling one published bundle from three machines
**I want** each machine's rows, fiches and refusals committed to that machine's own tracked results file through its own pull request, and one merge step that builds the bundle from them
**So that** every published number arrives through a check that could have refused it, and two machines can never silently claim the same fiche

Maps to: PRD Goal "an academic or technical reviewer can trace any published figure back to the run, the suite, the roster entry and the machine that produced it"; PRD AC "Given a code change, an automated check suite... blocks the merge"; epic decision "Row transport"; epic success checks 4 and 6.

Current state: the live stores are per-machine and gitignored (`.gitignore:25-27`); the two `*-reference.jsonl` files are "curated snapshots: no CLI ever writes to them" (`aidd_docs/results/README.md`). Three machines writing `runtime.jsonl` produce three files of the same name and no defined merge.

## Acceptance

- Each declared machine has its own tracked results location holding its runtime rows, its quality rows and its refusal records. The operator promotes named `run_id`s from the machine's live store into it; promotion refuses a row whose `machine_id` is not that location's machine, and copies the cited fiches into the tracked registry (content-addressed, so two machines' PRs never conflict on a fiche file).
- One merge step builds the published bundle from every machine's tracked location. It is keyed by fiche hash and **refuses a collision**, naming both rows, both machine ids and the shared hash, when two rows claim one fiche hash under different machine ids; it never chooses between them. [epic success check 4]
- The merge refuses a row whose `machine_id` does not resolve to a declared machine entry.
- The bundle is derived, never hand-edited: CI fails when the committed bundle differs from what the merge step produces from the committed per-machine files. This replaces the "no CLI ever writes to them" rule in `aidd_docs/results/README.md`, and that README says so.
- One branch and one pull request per machine, through the check suite the clean-machine epic already ships. A machine that cannot push uses the documented operator-carried fallback: the operator copies that machine's location and fiches to a machine that can, and the commit records the transport as operator-carried, naming the source machine and the carrying one, under the same declared-not-verified honesty as the energy labels. It is never passed off as the machine's own push. [epic decision "Row transport"]
- `tests/test_reference_bundle.py` gains the three bundle-level assertions: every row's machine id resolves to a declared entry, no two machines' rows share a fiche hash, and every refusal record resolves its roster entry, machine and profile.
- `docs/setup.md` gains the per-machine loop: declare, run, promote, branch, pull request; and the fallback, step by step.

## Code it changes

- A promotion command and a merge command (entry points in `pyproject.toml`, documented in `aidd_docs/memory/cli.md`).
- `settings.py`: the per-machine results root.
- `results.py` for row reading reused by both commands; `fiche_registry.py` for fiche copying.
- `.github/workflows/ci.yml`: the derived-bundle check.
- `tests/test_reference_bundle.py`; `aidd_docs/results/README.md`; `docs/setup.md`; `.gitignore` only if the tracked location sits under an ignored path; `CHANGELOG.md`.

## Tests it needs

- Promotion: a named run's rows land in the machine's location with their fiches; a foreign `machine_id` is refused; an unknown `run_id` is refused naming it; promoting twice is idempotent.
- Merge: two machines' files merge into one bundle deterministically (same input, byte-identical output); a constructed collision is refused naming both; an undeclared machine id is refused; refusal records are carried into the bundle and never into a runtime file.
- CI check: a hand-edited bundle fails it (asserted by the test that backs the workflow step, the pattern `tests/test_ci_workflow.py` already uses).
- `tests/test_reference_bundle.py`: the three new assertions.

## Evidence it publishes

- A dry run on constructed rows: two fake machines' files merged into a bundle, then a collision injected and refused, with the refusal's output quoted in the plan's evidence file. No real bundle is republished here; that is order 6.

## Plan shape

1. Per-machine tracked locations and the promotion command.
2. The merge command with its collision and undeclared-machine refusals.
3. The derived-bundle CI check and the bundle-level test assertions.
4. The per-machine loop and the operator-carried fallback in `docs/setup.md`; results README; CHANGELOG.

## Cancellation

n/a — not cancelled.
