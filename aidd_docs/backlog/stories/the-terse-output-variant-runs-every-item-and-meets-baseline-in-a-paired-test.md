---
type: story
status: ready
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/a-campaign-is-declared-as-data-and-an-empty-cell-fails-it.md
  - aidd_docs/backlog/stories/two-configurations-on-the-same-items-receive-a-paired-test-or-a-refusal.md
order: 4
---

# Story: The terse-output variant runs every item and meets baseline in a paired test

**As** the consultant asked whether a terse-output instruction helps a small model
**I want** an `output_compressed` variant that runs every item of the suites it declares, records a no-op where it does not apply, changes nothing but the prompt, and is compared with `baseline` through the paired test on the same items
**So that** I can say whether the Caveman-style instruction helps or hurts a small model on a task family with a test behind it, and an unparseable terse answer shows up as the finding it is

Maps to: PRD AC "given a claim that two models, engines or prompt variants differ, it is shown with a paired ... test's p-value and effect direction, or it is not presented as a difference"; PRD Open Question "Whether prompt compression helps or hurts a small model..."; Methodology 2, 3, 9, 22, 24; epic Boundaries "a prompt variant registry with four versioned entries", "variant applicability declared per suite, without ever changing the item set", "item scores staying per item across every variant and engine"; epic decisions "Variant is a prompt transformation and nothing else", "Pairing is preserved by construction", "A negative result is a result".

Needs: a real local model run (llama.cpp on the laptop, one roster entry, the classification suite under both variants). No API key, no extra hardware, no operator beyond the run.

## Acceptance

- The variant registry gains `output_compressed`, version 1: a declared terse-output instruction whose exact wording is its definition, versioned and hashed under order 2's rule.
- A variant entry declares the task families it applies to, with its reason written in the entry. An item of a declared suite where the variant does not apply is still run; its row records that the transformation was a no-op, and its pre-template prompt equals the authored text. No variant ever removes an item: the variant's item ids for a suite equal `baseline`'s.
- The variant changes the prompt and nothing else: the suite's caps, stop sequences, context length, thinking policy, scorer, parser, expected output and item set are identical between `baseline` and `output_compressed` rows of one suite, asserted by a test rather than by convention. A terse answer the unchanged parser cannot read scores 0 with its Methodology 9 failure reason.
- A paired comparison between `baseline` (reference) and `output_compressed` (candidate) over one suite, one roster entry, one engine and one campaign is produced by the analysis command of `two-configurations-on-the-same-items-receive-a-paired-test-or-a-refusal` with no second statistics path. Its differing-field set names exactly the variant fields (`prompt_variant_id`, `prompt_variant_version`); any further differing field publishes it as an observation under that story's rule.

## Code it changes

- The variant registry entry and the applicability declaration; the variant function from order 2 extended with the no-op record.
- `row_contract.py`: the no-op field, `SCHEMA_VERSION` bumped.

## Tests it needs

- Applicability: an undeclared family records a no-op and keeps the item; item ids identical across the two variants.
- Invariance: caps, scorer and parser identical across variants for every existing suite.
- An unparseable terse output scores 0 with its reason and stays in the denominator.
- A constructed baseline-versus-variant pair yields a comparison whose differing-field set is exactly the variant fields.

## Evidence it publishes

- One campaign cell pair on the laptop: one roster entry, the classification suite, `baseline` and `output_compressed`, its comparison record and the observed output-token difference, recorded in `aidd_docs/results/README.md`. A `not distinguishable` result is published as the answer it is.

## Cancellation

n/a: not cancelled.
