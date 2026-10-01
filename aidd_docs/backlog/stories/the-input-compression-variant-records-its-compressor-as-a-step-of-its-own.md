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

Blocked: spike `aidd_docs/backlog/spikes/which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement.md`; Q23 (how the compressor's dependencies enter the project).

## Acceptance

- The variant registry gains `input_compressed`, version 1, naming its compressor by id, version, repo, revision and checksum, its compression setting, its declared placement (CPU, or a separate phase before generation), and the task families and languages it applies to, each versioned and hashed under order 2's rule. The compressor's weights are fetched by revision with a checksum verification, like a roster entry.
- The compressor runs per item, inside the measured path, and the row records the compressor's identity, its placement, the token count before and after with the tokenizer that counted them, the resulting ratio, and the compressor's wall-clock duration and energy as fields of their own, never merged into the generation's.
- TTFT stays the engine's own figure under its `ttft_source` label; the compressor's duration is published beside it and never added to it.
- An item where compression is declared not applicable, or changes nothing, is still run and records its no-op under order 4's rule; the item ids equal `baseline`'s.
- A paired comparison against `baseline` on the same items is produced by the existing analysis command, as in order 4.

## Code it changes

- A compressor step ahead of the variant function's output; its registry entry; its install path as Q23 decides.
- `row_contract.py`: the compressor fields, `SCHEMA_VERSION` bumped; `docs/setup.md`: the compressor's install and download.

## Tests it needs

- Compressor fields present and separate from generation fields; TTFT unchanged by the compressor duration.
- A no-op item kept with its record; item ids equal across variants.
- A checksum mismatch on the compressor weights refuses the run.

## Evidence it publishes

- One campaign cell pair (`baseline` and `input_compressed`) on the reference machine, with the per-language compression ratios, the compressor's total duration and energy, and the comparison record, in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
