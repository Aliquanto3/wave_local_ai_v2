---
type: story
status: proposed
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/the-terse-output-variant-runs-every-item-and-meets-baseline-in-a-paired-test.md
order: 9
---

# Story: The input-compression variant records its compressor as a step of its own

**As** the consultant asked whether compressing a prompt saves anything on a small model
**I want** an `input_compressed` variant whose compressor runs per item inside the measured path, with its own identity, token counts, ratio, duration, energy and placement on the row
**So that** "compression saves tokens" is weighed against what the compression itself cost, and the engine's TTFT is never silently mixed with a client-side duration

Maps to: PRD Open Question "Whether prompt compression helps or hurts a small model, in quality and in TTFT..."; Methodology 2, 15, 20, 22; epic Boundaries "`input_compressed` recording its compressor as a step of its own", "variant applicability declared per suite"; epic decisions "Compressor cost is counted and kept separate", "Pairing is preserved by construction"; epic Unknowns "Whether an LLMLingua-2-class compressor fits on the reference machine", "Whether input compression is meaningful at all on short items".

Needs: a real local model run on the reference machine (the compressor model and a llama.cpp subject). No API key.

Blocked: spike `aidd_docs/backlog/spikes/which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement.md`, which settles which compressor, at which setting and in which placement.

## Acceptance

- The variant registry gains `input_compressed`, version 1, naming its compressor by id, version, repo, revision and checksum, its compression setting, its declared placement (CPU, or a separate phase before generation), and the task families and languages it applies to, each versioned and hashed under order 2's rule. The compressor's weights are fetched by revision with a checksum verification, like a roster entry.
- The compressor's runtime dependencies enter the project as one optional, pinned dependency group used only by `input_compressed`, as Q23 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles: locked in `uv.lock`, excluded from the default install and from the published container image, never a required dependency. Every other variant, and the package itself, imports and runs without the group installed; selecting `input_compressed` without it refuses the run naming the missing group.
- The dependency audit (`scripts/audit_dependencies.py`) covers the optional group's packages, and `docs/setup.md` documents the one extra install step a reproduction of the `input_compressed` cells needs.
- The compressor runs per item, inside the measured path, and the row records the compressor's identity, its placement, the token count before and after with the tokenizer that counted them, the resulting ratio, and the compressor's wall-clock duration and energy as fields of their own, never merged into the generation's.
- TTFT stays the engine's own figure under its `ttft_source` label; the compressor's duration is published beside it and never added to it.
- An item where compression is declared not applicable, or changes nothing, is still run and records its no-op under order 4's rule; the item ids equal `baseline`'s.
- A paired comparison against `baseline` on the same items is produced by the existing analysis command, as in order 4.

## Code it changes

- A compressor step ahead of the variant function's output; its registry entry; the optional dependency group in `pyproject.toml` and `uv.lock`; the dependency audit's coverage of that group.
- `row_contract.py`: the compressor fields, `SCHEMA_VERSION` bumped; `docs/setup.md`: the compressor's install and download.

## Tests it needs

- Compressor fields present and separate from generation fields; TTFT unchanged by the compressor duration.
- A no-op item kept with its record; item ids equal across variants.
- A checksum mismatch on the compressor weights refuses the run.
- With the optional group absent, the other variants run and `input_compressed` is refused naming the group; the audit's exported dependency set includes the group's packages.

## Evidence it publishes

- One campaign cell pair (`baseline` and `input_compressed`) on the reference machine, with the per-language compression ratios, the compressor's total duration and energy, and the comparison record, in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
