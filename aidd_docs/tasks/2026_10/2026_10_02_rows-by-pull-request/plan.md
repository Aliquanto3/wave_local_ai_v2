---
objective: "Each declared machine promotes named runs into its own tracked results location, one merge step derives the published bundle from every location (refusing a fiche-hash collision across machines and an undeclared machine id), CI fails on a bundle that differs from the merge output, and docs/setup.md walks the per-machine loop and the operator-carried fallback."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Each machine returns its rows by pull request, and a hash collision is refused

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `aidd_docs/results/machines/<machine_id>/{runtime,quality,refusals}.jsonl` per declared machine (`MACHINE_RESULTS_ROOT`); `wave-local-ai-v2-promote` copies named `run_id`s and their fiches into it; `wave-local-ai-v2-merge-bundle` derives `runtime-reference.jsonl`, `quality-reference.jsonl` and `refusals-reference.jsonl` from every location, `--check` in CI |
| **Source** | `aidd_docs/backlog/stories/each-machine-returns-its-rows-by-pull-request-and-a-hash-collision-is-refused.md`; parent epic `the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md` (decision "Row transport", success checks 4 and 6); night-run owner decision D1 |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Per-machine tracked locations and the promotion command | [`phase-1.md`](./phase-1.md) |
| 2   | The merge command, its collision and undeclared-machine refusals | [`phase-2.md`](./phase-2.md) |
| 3   | The derived-bundle CI check and the three bundle-level assertions | [`phase-3.md`](./phase-3.md) |
| 4   | The per-machine loop and the operator-carried fallback in docs; results README; CHANGELOG; constructed dry run | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| A machine's tracked location is the directory `MACHINE_RESULTS_ROOT/<machine_id>/` (default `aidd_docs/results/machines/`) holding `runtime.jsonl`, `quality.jsonl`, `refusals.jsonl`. The `.gitignore` rule covers only top-level `aidd_docs/results/*.jsonl`, so the location is tracked without a negation. | Acceptance line 1: one location per machine, three record kinds; a file per machine means two machines' PRs never touch the same file. |
| The pre-flight writes refusal records straight into the location (`<root>/<machine_id>/refusals.jsonl`); `REFUSALS_DIR` is replaced by `MACHINE_RESULTS_ROOT`. Promotion does not handle refusals. | A refusal record carries no `run_id` (its contract, story order 4), so it cannot be promoted by one; story 4 already published it to a tracked per-machine file, which is now the location's third file rather than a second tracked copy. |
| Promotion copies each selected line byte-for-byte, skipping a line already present (idempotent), and writes nothing unless every named `run_id` resolves and every row passes. A row is accepted when its `machine_id` is the location's, or `not_applicable` on a cloud-subject quality row; anything else (another machine, a pre-"23" row with no `machine_id`) is refused naming the row. | Acceptance line 1 and its tests; a cloud row is produced by no machine (`row_contract.MACHINE_NOT_APPLICABLE`) yet is run from one, so it travels in the PR of the machine that ran its CLI. |
| Fiches are copied file-for-file from the live registry (`FICHE_REGISTRY_DIR`) into the tracked one (`TRACKED_FICHE_REGISTRY_DIR`, default `aidd_docs/results/fiches`); a tracked file already present with other bytes is refused, never overwritten; a cited fiche absent from the live registry is refused. | Content-addressed: two machines' PRs add distinct file names, or the identical file. |
| The merge reads the declared machines' locations in sorted machine-id order and each file in append order, writes each line unchanged, and keys every row carrying a declared `machine_id` by `fiche_hash`. Two rows claiming one hash under different machine ids are refused naming both rows (kind, `run_id`, `item_id`), both machine ids and the hash. Cloud rows (`not_applicable`) cite their running machine's fiche, so they are excluded from the keying, not counted as a third machine. | Acceptance line 2; deterministic byte output; never chooses. |
| The merge also refuses: a location directory named for an undeclared machine, a row or refusal whose `machine_id` resolves to no declared entry, a row filed under another machine's location, and one `run_id` present in two locations. | Acceptance line 3; the last two close the paths by which one row could reach the bundle twice. |
| The bundle is three files: `runtime-reference.jsonl`, `quality-reference.jsonl` and the new `refusals-reference.jsonl`. Refusal records go only into the third. | Acceptance "refusal records are carried into the bundle and never into a runtime file". |
| Transition until order 6: the committed bundle is the schema-"7" curated snapshot, no location holds a row, and the snapshot cannot be derived (its rows predate `machine_id`). `bundle_merge.PRE_MERGE_SNAPSHOT` pins its two files by sha256 (line endings normalised). `--check` passes that exact state only while every location is empty and reports it; any edit to those bytes, any promoted row, or any other bundle fails. Write mode refuses to overwrite the pinned snapshot: order 6 `git mv`s it to `*.schema-7.jsonl` first, then deletes the pin. | The story publishes no bundle (order 6 does) and the brief forbids editing the committed stores; without the pin CI would be red from this story to order 6, with it a hand edit still fails. |
| Comparison and digests normalise `\r\n` to `\n`. | No `.gitattributes`; this machine checks out with `core.autocrlf=true`, the Linux CI leg without. |
| The three bundle-level assertions in `tests/test_reference_bundle.py` run against the committed bundle and also against a constructed two-machine bundle (so each provably bites today); against the schema-"7" snapshot the machine-id and collision assertions see no row carrying `machine_id` and the refusal assertion sees no refusal file. | Order 6 republishes; until then the committed bundle has nothing for them to resolve, which the test states rather than hides. |
| Entry points `wave-local-ai-v2-promote` (`machine_results.py:main`) and `wave-local-ai-v2-merge-bundle` (`bundle_merge.py:main`). | "Code it changes": two commands in `pyproject.toml`. |
| Evidence: a constructed dry run (two fake locations in a temp dir, merged, then a collision injected) quoted in `evidence/`; per-machine PR flow proven with throwaway local git repositories only. | Night-run rules: no push, no PR, no remote. |
| Review round 1: each machine pull request regenerates the bundle (`merge-bundle`, then `--check`) and commits it with its location; when another machine lands first, the branch rebases, takes `main`'s bundle files and re-runs the merge, never hand-resolving them. A row with no `run_id` is refused by name. | A location-only PR fails its own Derived bundle step (reviewer reproduction); proven in `evidence/gitflow-output.txt` with throwaway local repositories. |
