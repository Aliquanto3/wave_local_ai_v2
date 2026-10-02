---
type: spike
status: open
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parents:
  - aidd_docs/backlog/stories/the-input-compression-variant-records-its-compressor-as-a-step-of-its-own.md
---

# Spike: Which LLMLingua-2-class compressor fits the reference machine, and in which placement

## Question

Which pinned LLMLingua-2-class compressor model can run per item on the reference machine beside a roster model under test, in which placement (CPU in the same phase, or a separate phase before generation), handles the suites' EN, FR and DE items, and at what measured per-item duration and dependency footprint?

## Decision

The `input_compressed` variant entry's build inputs (order 9): the compressor's id, repo, revision and checksum; its declared placement; whether it is applied to all three languages or declares a language as not applicable; the token counter used for "before" and "after" and whether it is the subject model's tokenizer or the compressor's; and the dependency set the owner's answer to Q23 then decides how to admit.

## Bounds

- Evidence needed: on the reference machine (the laptop under Q22's recommended default), for the reference LLMLingua-2 checkpoint the literature names and at most one alternative: its licence and pinned revision; the packages and versions it requires and their installed size; peak VRAM and RAM when run on GPU beside `qwen3-0.6b-q8` and the flagship's profile, and when run on CPU; per-item compression duration on the classification and translation suites' items in each placement; the before and after token counts and the resulting ratio on those items, per language, including the items where the compressor changes nothing; one EN, one FR and one DE example of input and compressed output, recorded as evidence of whether the meaning-bearing tokens survive.
- Stop when: one compressor and placement are shown to run on the reference machine without displacing the subject model's declared profile, with per-item duration and per-language ratios recorded, or no candidate is shown to fit, which is recorded as the finding that blocks the variant on that machine.
