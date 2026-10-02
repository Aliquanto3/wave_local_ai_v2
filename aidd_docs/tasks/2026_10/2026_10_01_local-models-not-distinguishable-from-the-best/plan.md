---
objective: "The analysis command, run over the published bundle, writes one immutable leader-set record per suite and machine class naming every local subject not distinguishable from the best under the suite's Holm-adjusted comparison family, and the pitch overview reads its leader membership from the current record instead of a row field."
status: implemented
---

# Plan: Each suite and machine publishes the local models not distinguishable from the best

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Derive the leader set (best local subject plus every local subject the paired tests cannot tell from it) per suite and machine class, publish it as its own superseded-not-edited record beside the comparison families, and make the overview read it |
| **Source** | `aidd_docs/backlog/stories/each-suite-and-machine-publishes-the-local-models-not-distinguishable-from-the-best.md` (branch `docs/slice-remaining-epics`), owner answer Q42 (a) |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | The leader-set derivation and its record | [`phase-1.md`](./phase-1.md) |
| 2   | The analysis command writes the family and the leader-set records | [`phase-2.md`](./phase-2.md) |
| 3   | The overview reads the record; the records over the committed bundle; docs | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The derivation lives in a new `leader_set.py`; the analysis command is still `wave-local-ai-v2-compare`, which gains `--leader-sets` and hands the run to `leader_set.publish` (imported inside `main`, since `leader_set` imports `comparison`). | The acceptance names the analysis command of orders 2 and 3. A separate module keeps `comparison.py` (already 1,600 lines) about tests and families, and lets `read_model` import only the leader-set *read* functions by name. |
| A subject is one local batch: a `run_id` plus its `model_id` (the selector the committed family already uses). Only rows whose `provider` is `local` make subjects. Cloud rows are never subjects, so never members, excluded or not compared. | The story records "each subject's run id"; the existing family's sides are `run_id` + `model_id`, so a leader comparison and a committed comparison of the same two batches have the same member key. |
| Machine class = the fiche fields `machine_id`, `compute_mode`, `cpu`, `ram_gb`, `gpu_name`, `os`. A field the fiche does not carry is listed under `grouping_not_recorded` and groups as not recorded; the record names every grouping field and value. | Hardware identity plus compute mode, as the acceptance asks; `machine_id`/`compute_mode` do not exist yet (story `a-gpu-run-and-a-cpu-only-run-never-share-a-fiche`) and are read as soon as fiches carry them, so a `gpu` and a `cpu_only` fiche of one machine never share a group. Driver, CUDA ceiling, build, quant and model hash are software or model fields, not a machine class. Refusing every fiche without `compute_mode` would publish nothing over the committed bundle, which the story names as the first real case. |
| The best subject has the highest published suite score (`suite_accuracy` for exact-match rows, `suite_score` for graded rows, the one non-null value its rows carry). Tie rule: among subjects tied at the top score, the one whose (`run_id`, `model_id`) sorts first. A subject with no suite score (a batch left partial) is still compared, never the reference. | Deterministic and recomputable from the bundle alone; captured-at ordering would need a further tie-break anyway. |
| The leader comparisons (reference against every other local subject of the group) join the suite's one `model` x `score` family: the command declares the current family head's comparisons plus every group's leader comparisons, so Holm runs over that whole closed family (cloud comparisons included), and the family grows by supersession under order 3's rules. | Order 3 defines the family as one suite by one dimension and refuses a shrinking re-declaration; a per-group family would collide with that definition. More members only makes the adjustment more conservative. |
| Status: `not distinguishable` => member; `distinguishable` => excluded; any `not comparable` (a refusal, or an observation such as a partial batch, a confound, or two batches of the same model) => `not compared`, naming the refused fields or the observation reason, and the record states `incomplete`. | The acceptance defines refusal as not compared; an observation is equally not a test, so reading it as a member would publish a confounded pair as a finding. |
| One record per group; a group with one local subject is a set of one with `comparison_ran: false` and no family id; a group whose local subjects carry no suite score publishes nothing and the command names it on stderr. | Acceptance bullets 5 and 6; with no score there is no best. |
| Leader-set records live in `aidd_docs/results/leader-sets/` (own NOTICE.md, own LICENSE-DATA entry), named `<suite>@<version>.<leader_set_id[:12]>.json`. `leader_set_id` hashes the canonical content including `supersedes` (a list of `{"leader_set_id": ...}`). A changed group record supersedes every head of that group; an identical one is re-emitted. | Same immutability and id scheme as family records; a sibling directory keeps `read_family_records` and the record kinds apart. The data-licence test requires every results subdirectory in scope. |
| The overview's `leader` is the current record(s) of the use case's suites: `{"members": [...], "leader_sets": [{id, suite, grouping values, incomplete}]}`; no record => `pointer_unresolved` naming `leader_set` and the suites; a member whose rows the store does not hold => the same absence naming the record. `leader_set_member` and its comment are removed. | Keeps the frontend's `Absent | {members}` contract and the three finite absence reasons; the record is a pointer the read model resolves like a fiche. |
| The fifth export table is not touched. | Its story (`comparison-family-and-leader-set-records-read-as-a-fifth-table`) and order 6 are not built; the export dictionary already names leader sets as not carried. |
| The record names each subject by `run_id` and `model_id` and the machine class by its grouping values; it does not repeat the fiche hashes. | A bare 64-hex `fiche_hash` value on its own line is flagged by detect-secrets (no `_id` key), JSON holds no inline pragma, and the hash is one lookup away through the run id in the rows file the record names. |
