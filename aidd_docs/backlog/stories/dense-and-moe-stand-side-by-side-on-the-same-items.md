---
type: story
status: ready
source: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
depends_on: aidd_docs/backlog/stories/quality-runtime-and-energy-read-at-pitch-distance.md
order: 4
---

# Story: Dense and MoE stand side by side on the same items

**As** a client decision-maker deciding which model class to put on their own hardware
**I want** the roster's MoE candidate and its dense candidates shown as columns over the same suite items, each column naming its architecture, its quant and the policy it answered under
**So that** I can see which family actually wins my use case instead of being told which one the benchmark chose

## Acceptance

- PRD AC "at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side, and each of them cites its entry in the versioned roster file": for each suite present in the store, the quality surface shows one column per model over the same items, and every column names the `roster_entry_id` it cites.
- Methodology 13: each column carries its architecture from the roster entry — `dense`, or `moe` with its expert count and active-parameter figure — plus its quant. The roster's four entries today are one MoE flagship and a three-rung dense ladder; a column set of any size renders without a change to this surface, which is what the epic asks of it.
- The comparison is quality-only. No runtime, energy or cost column is reachable from it, and it reads the quality view model alone — the same boundary order 3 establishes, held where the temptation to breach it is strongest.
- **A caveat the column set carries travels with the column, never averaged away.** Where two columns sit at different `suite_version` values, both versions are on screen and the difference is stated rather than smoothed: the live store's `gemini-3.5-flash-lite` rows are cited at classification `"2"` and translation `"1"` against the local ladder's `"3"` and `"2"`, with identical items and identical `prompt_set_hash` on both sides. Identical prompt sets are what makes those columns comparable, and the surface shows the reader that fact instead of hiding the version gap.
- An item present in one column's suite version and absent from another's is shown as not compared, never as equal and never as a blank that reads like a zero.
- Methodology 3: each column names its `thinking_policy`. The dense ladder's published scores exist under `disabled`; the same models with thinking allowed spend the whole cap reasoning and return nothing. A column that does not name the policy is a column two readers will read two ways.
- Methodology 4: every per-language cell in the comparison keeps its `n` and its indicative mark. All of today's per-language cells are indicative at n=5 and n=7 against the 10-item floor, so the mark is on nearly every cell and is not an edge case.
- A `roster_entry_id` that does not resolve against the roster file is a declared absence naming the id, never a column rendered with a missing architecture.

## Code it changes

- `src/wave_local_ai_v2/read_model.py` — resolves `roster_entry_id` to the entry's `architecture`, `quant` and `display_id`, and assembles the column set for a suite by `(suite_id, item_id)` across models, carrying each column's own `suite_version` rather than assuming one.
- `src/wave_local_ai_v2/service.py` — the comparison read exposed under the quality route family, so nothing about it can reach a runtime row.
- `frontend/src/views/comparison/` (new) — the side-by-side table and its column headers.
- `frontend/src/labels/` — reused unchanged; a mark rendered here is the same component order 3 defined.

## Tests it needs

- `tests/test_read_model.py` — a column set spanning two `suite_version` values keeps both versions and marks the items only one of them holds; an unresolvable `roster_entry_id` yields a declared absence; the comparison model exposes no runtime, energy or cost field (asserted over the type, not by inspecting one fixture).
- `frontend/src/views/comparison/*.test.tsx` — four columns from a fixture render four architectures and four quants; an item missing from one column renders as not compared; a column's `thinking_policy` is shown; an indicative cell keeps its mark in the side-by-side layout.

## Evidence it publishes

- The four-model comparison captured over the live store's chat-templated batches — the classification ladder at 0.45 / 0.60 / 0.70 / 1.00 and the translation ladder at 0.5121 / 0.7107 / 0.7252 / 0.8002, already recorded in `aidd_docs/results/README.md` — shown beside the cited cloud column at its own suite version, so the screen and the README's tables can be checked against each other.

## Cancellation

n/a — not cancelled.
