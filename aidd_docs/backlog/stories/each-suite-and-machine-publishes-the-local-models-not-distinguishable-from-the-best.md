---
type: story
status: ready
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-comparison-family-carries-its-adjusted-p-values-and-is-superseded-not-edited.md
order: 10
---

# Story: Each suite and machine publishes the local models not distinguishable from the best

**As** a consultant opening the pitch on a use case
**I want** a published leader set per suite and machine class, naming every local model whose score the paired tests cannot distinguish from the best, with the tests behind it
**So that** the overview names the best local model from evidence rather than from the highest raw score, and anyone holding the bundle can recompute who leads

Maps to: PRD Non-goals ("the leader set for a given suite and machine class, the models whose scores are not statistically distinguishable from the best under the paired tests of Methodology 24, is a published derived output ... recomputable by anyone holding that bundle"); PRD AC "Given the pitch overview, it shows one card per use case: the best local model as the published leader set names it ... and a stated absence when no leader set is published"; Methodology 24; epic Dependencies row "A derived leader set, and which epic owns it"; owner answer to Q42 (option a, 2026-10-01). No epic success check names it; it closes under gate two of the epic, as the owner set gate one to orders 1, 2, 3 and 6 (Q5).

Needs: none. Constructed rows prove the computation and the committed bundle supplies the first real case; no model run, API key, hardware or operator is required.

Current state: nothing writes a leader set. The pitch overview (`the-pitch-opens-on-one-card-per-use-case-read-from-published-rows.md`, `done`) shows a stated absence on every card, and `src/wave_local_ai_v2/read_model.py` anticipates membership as a per-row field, `leader_set_member`, which no row carries. A per-row field would mean rewriting published rows whenever the set changes; under Q42 the set is its own record instead. The committed classification pairs hold one local subject (`Qwen3.6-35B-A3B`) and one cloud subject (`mistral-small-2603`). The rows carry no machine-class field; each cites its machine through `fiche_hash`.

## Acceptance

- The analysis command of orders 2 and 3, run over the published bundle, writes one leader-set record per suite (id and version) and machine class into the bundle, beside the comparison and family records, as its own tracked artifact. Nothing computes a leader set at read time and no published row is rewritten.
- The machine class is read from what the row's fiche records (its hardware identity and compute mode), and the record names the fields it grouped on, so a `gpu` and a `cpu_only` run of one machine never fall into one group.
- Only local subjects enter a leader set; cloud subjects stay the pitch's comparators and are never members, as the pitch AC states.
- The best subject is the one with the highest published suite score in the group; a tie for the top score names the reference by a deterministic rule stated on the record. Every other local subject in the group is compared against it in one comparison family (order 3), with Holm-adjusted p-values over that closed set.
- Members are the best subject plus every subject whose comparison against it reads `not distinguishable` at the declared alpha. A subject whose comparison reads `distinguishable` is listed as excluded. A subject whose comparison was refused is neither: it is listed as not compared, naming the refused field, and a record with any such subject states that it is incomplete.
- A group with one local subject publishes a set of one that states no comparison ran. A group with no local subject publishes no record.
- The record carries the suite id and version, the level, the grouping fields and their values, the reference subject and the tie rule, the family record id it was read from, and each subject's run id and status (member, excluded, not compared).
- A leader-set record is immutable once written: a new family for the same group writes a new leader-set record superseding the old by id, the old one unchanged.
- The pitch overview's leader membership resolves from the current leader-set record rather than from the `leader_set_member` row field, so a published set reaches the card and a group without a record keeps its stated absence. The overview still scores, ranks and derives nothing.
- Re-running the analysis command over the published bundle alone, through no private path, returns identical leader-set records.

## Code it changes

- The comparison module and analysis command of orders 2 and 3: the leader-set derivation and its record file under `aidd_docs/results/`.
- `src/wave_local_ai_v2/read_model.py`: leader membership read from the leader-set record in place of the anticipated row field, and the comment that calls the derivation unowned.
- The column definitions order 6 supplies to the fifth export table (`comparison-family-and-leader-set-records-read-as-a-fifth-table.md`), which flattens the record like any other.

## Tests it needs

- Constructed groups: three local subjects where one is distinguishable from the best and one is not (two members, one excluded); a refused comparison (not compared, record incomplete); a tie at the top score (the stated rule names the reference); a single local subject (set of one, no comparison); a cloud subject present (never a member); a `gpu` and a `cpu_only` run of one model (two groups).
- A family superseded by a larger one writes a new leader-set record and leaves the old file byte-identical.
- `tests/test_read_model.py`: the overview renders members from a leader-set record, and a suite without one keeps its stated absence.

## Evidence it publishes

- The leader-set records the analysis command writes over the committed bundle, recorded in `aidd_docs/results/README.md` beside the comparison and family records.

## Cancellation

n/a: not cancelled.
