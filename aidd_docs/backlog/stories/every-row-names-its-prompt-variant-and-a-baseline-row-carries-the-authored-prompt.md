---
type: story
status: ready
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
order: 2
---

# Story: Every row names its prompt variant, and a baseline row carries the authored prompt

**As** an academic or technical reviewer reading a quality score
**I want** every row to name the prompt variant and variant version it ran under, and the writer gate to refuse a row that claims `baseline` while its prompt was transformed
**So that** every number the repository publishes says which prompt shape produced it, and "baseline" is a checked claim rather than a label

Maps to: PRD AC "Given a campaign, every row records its engine ... and its prompt variant..."; Methodology 2 ("a variant's definition is versioned like a prompt template"), 19, 22; epic Boundaries "a prompt variant registry with four versioned entries", "the rendered prompt showing the transformation"; epic decision "Variant is a prompt transformation and nothing else"; epic success check 1 (the variant half: a hand-built row claiming `baseline` while carrying a transformed prompt is refused by the writer gate, verified against the gate).

Needs: none. Constructed rows prove the gate; no model run, API key, hardware or operator is required.

Current state: a suite item's prompt reaches the model as authored; `prompt_template_id` names the model's own chat template, not any transformation before it; the row's `prompt` field holds the string after templating (`quality_cli.py`, `rendered_prompts`), so it never equals the authored text even on today's baseline path.

## Acceptance

- A tracked prompt variant registry exists with one entry, `baseline`, version 1, declared as the identity transformation. Each entry carries its id, its version, its definition, and a content hash of that definition. Editing a definition without bumping its version is refused at load, naming the variant, the way an edited prompt without a suite version bump is refused today. The other three variants are added by their own stories (orders 4, 5 and 9).
- The variant is applied to the item's authored prompt before the engine's own templating, through one function, never at a call site. The row keeps publishing under Methodology 2 the string the engine finally received, so a non-baseline variant's effect is visible in it.
- Every quality row and every runtime row carries `prompt_variant_id` and `prompt_variant_version`, and the prompt as the variant left it, before templating, as its own field beside the existing template id and hash. A cloud subject's quality row carries them too: the variant applies to every subject, and today's cloud rows are `baseline`.
- The writer gate refuses, naming the field: a row missing either variant field; a row naming a variant or a version absent from the registry; a row declaring `baseline` whose pre-template prompt differs from the item's authored text.
- The schema version is bumped with its history comment; rows below it are read under their own version and never back-filled with `baseline`.

## Code it changes

- New tracked variant registry (proposed beside the suite definitions) and its loader with the definition-hash check.
- One variant-application function on the quality and runtime paths, ahead of `local_client.render_prompt` and the cloud clients' request building.
- `row_contract.py` (fields, gate rules, `SCHEMA_VERSION`); the writers (`__init__.py`, `quality_cli.py`, `judge_probe.py`); `CHANGELOG.md`.

## Tests it needs

- Registry: `baseline` loads; an edited definition at an unchanged version is refused.
- Gate, against constructed rows: the hand-built `baseline` row with a transformed pre-template prompt is refused naming the field; an unregistered variant and an unknown version are refused; a genuine baseline row passes.
- The variant function runs before templating on both local and cloud paths; the runtime fixed prompt passes through it.

## Evidence it publishes

- The gate's refusal of the hand-built row, run through the gate in a test whose output is cited in the plan's evidence file (epic success check 1, variant half).

## Cancellation

n/a: not cancelled.
