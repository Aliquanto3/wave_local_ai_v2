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

Blocked: nothing. The spike `aidd_docs/backlog/spikes/which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement.md` is `resolved` (2026-10-04, live CPU measurement): `microsoft/llmlingua-2-xlm-roberta-large-meetingbank` on CPU in the same phase, 1.22 to 1.29 s median per item, peak RSS 1.9 GB, VRAM unchanged; its Outcome recommends compressing the payload alone, because on the whole prompt the compressor dropped the label `other` from the instruction in 14 of 20 classification items. Its `depends_on`, `the-terse-output-variant-runs-every-item-and-meets-baseline-in-a-paired-test.md` (order 4), is `done`.

Current state (verified on `main` at `c68b23e`, 2026-10-03):

- `prompt_variants.REGISTERED_VARIANTS` holds `baseline` only; the module docstring names `input_compressed` as added by its own story.
- `pyproject.toml` declares one dependency group, `dev`, and no optional group or extra; no compressor runtime (`llmlingua`, `torch`, `transformers`) is a dependency.
- `scripts/audit_dependencies.py` exports `uv.lock` through `uv export --format pylock.toml` with no group or extra named, so an optional group stays outside the audited set until that call names it.
- `local_client.count_tokens` counts through llama-server `/tokenize` (`LOCAL_TOKENIZE_ENDPOINT`), the subject's own tokenizer the spike names for the before and after counts.
- `row_contract.SCHEMA_VERSION` is `"22"`: quality rows carry `item_tokens_in`, `item_tokens_out` and a per-item TTFT under `item_ttft_source`; no compressor field exists. `docs/setup.md` names no compressor install.

## Acceptance

- The variant registry gains `input_compressed`, version 1, naming its compressor by id, version, repo, revision and checksum, its compression setting, its declared placement (CPU, in the same phase, per item just before the request, per owner answer Q115 (a), 2026-10-03), and the task families and languages it applies to, each versioned and hashed under order 2's rule. The compressor's weights are fetched by revision with a checksum verification, like a roster entry, and so is every file the compressor package fetches when it loads (the `cl100k_base` encoding file, per the spike), each loaded from its verified local copy.
- The compressor's runtime dependencies enter the project as one optional, pinned dependency group used only by `input_compressed`, as Q23 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles: locked in `uv.lock`, excluded from the default install and from the published container image, never a required dependency. Its torch is the plain PyPI wheel (a CPU-only build on Windows), so the group needs no extra package index (owner answer Q115 (a), 2026-10-03). Every other variant, and the package itself, imports and runs without the group installed; selecting `input_compressed` without it refuses the run naming the missing group.
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
- A checksum mismatch on the compressor weights or on the encoding file refuses the run.
- With the optional group absent, the other variants run and `input_compressed` is refused naming the group; the audit's exported dependency set includes the group's packages.

## Evidence it publishes

- One campaign cell pair (`baseline` and `input_compressed`) on the reference machine, with the per-language compression ratios, the compressor's total duration and energy, and the comparison record, in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
