---
type: story
status: ready
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/the-terse-output-variant-runs-every-item-and-meets-baseline-in-a-paired-test.md
order: 5
---

# Story: The constrained-output variant runs under a llama.cpp grammar and names its mechanism

**As** an academic or technical reviewer reading a constrained-output score
**I want** a `constrained_output` variant whose grammar-restricted output format is declared per task family, applied on llama.cpp through its grammar mechanism, and named on every row
**So that** the DSL technique's output-side descendant is measured against `baseline` on the same items, and a later cross-engine comparison can tell a comparison of engines from a comparison of two constraint mechanisms

Maps to: PRD AC "Given a campaign, every row records its engine ... and its prompt variant..."; Methodology 2, 3, 9, 22, 24; epic Boundaries "a prompt variant registry with four versioned entries" (`constrained_output` as "the DSL technique's descendant, expressed as a grammar-restricted output format"), "the constrained variant's mechanism recorded per engine"; epic decisions "Variant is a prompt transformation and nothing else", "Pairing is preserved by construction".

Needs: a real local model run (llama.cpp on the laptop, one roster entry, the classification suite under `baseline` and `constrained_output`). No API key, no extra hardware.

## Acceptance

- The variant registry gains `constrained_output`, version 1. Its definition declares, per task family it applies to, the output format and the grammar that expresses it, plus any format instruction added to the prompt; all of it is versioned and hashed under order 2's rule, and families it does not apply to record a no-op under order 4's rule.
- On llama.cpp the grammar is sent with each request through llama.cpp's own grammar mechanism, and each row records the mechanism applied (`gbnf` for this engine) and the content hash of the grammar sent. Any instruction the variant adds is visible in the published rendered prompt.
- The scorer, parser, caps, expected output and item set are unchanged from `baseline`, under order 4's invariance test. An output the grammar admits but the parser cannot score still scores 0 with its reason.
- A paired comparison of `constrained_output` against `baseline` on one suite, roster entry and campaign is produced by the existing analysis command, its differing-field set naming only the variant fields and the constraint mechanism.
- The engine registry's llama.cpp entry declares the constraint mechanisms it supports, so a campaign declaring `constrained_output` on an engine that declares none is refused at declaration until order 8 records that engine's outcome.

## Code it changes

- The variant registry entry with its per-family grammars; the request path in `local_client` passing the grammar; the engine entry's supported mechanisms.
- `row_contract.py`: the mechanism and grammar hash fields, `SCHEMA_VERSION` bumped.

## Tests it needs

- The grammar is sent only under `constrained_output` and only for declared families; its hash is on the row.
- Invariance and pairing as in order 4; a declaration of the variant on an engine declaring no mechanism is refused.

## Evidence it publishes

- One campaign cell pair on the laptop (the same roster entry and suite as order 4's), its comparison record, and the share of baseline outputs that fell outside the declared format, recorded in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
