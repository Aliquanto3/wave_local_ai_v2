---
type: story
status: proposed
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/ollama-runtime-rows-stand-beside-llama-cpp-rows-on-the-same-artifact.md
  - aidd_docs/backlog/stories/every-row-names-its-prompt-variant-and-a-baseline-row-carries-the-authored-prompt.md
order: 7
---

# Story: Ollama quality rows pass a prompt-parity gate or publish as observations

**As** an academic or technical reviewer reading a cross-engine quality comparison
**I want** Ollama's quality rows to publish the prompt Ollama actually received, or its explicit absence, and every cross-engine quality cell to be gated on a byte-for-byte comparison of the two engines' rendered prompts
**So that** a quality difference between engines is never a template difference read as an engine difference, and a cell that cannot be checked says so

Maps to: PRD AC "given a claim that two models, engines or prompt variants differ, it is shown with a paired ... test ... or it is not presented as a difference"; Methodology 2 ("the final prompt string as rendered for that provider"), 3, 22, 24; epic Boundaries "the runtime protocol and the quality path both run per engine, unchanged in shape", "item scores staying per item across every variant and engine"; epic decisions "Prompt parity across engines is a gate, not an assumption", "Thinking control is per engine as well as per model"; epic success check 3.

Needs: a real local model run on the reference machine with the pinned Ollama build installed (order 6). No API key.

Blocked: spike `aidd_docs/backlog/spikes/does-ollama-expose-the-prompt-it-finally-rendered.md` (which `prompt_capture` value Ollama rows can carry, and whether its thinking switch can be verified by render comparison).

## Acceptance

- The quality path runs on Ollama for a local roster entry, writing ordinary quality rows with per-item scores in the shape the store already holds, under the same suite, caps, scorer and variant function as on llama.cpp.
- Each Ollama quality row publishes the prompt Ollama received with its `prompt_capture` kind, or carries an explicit absence of a rendered prompt; it never publishes the authored or pre-template prompt as if it were the rendered one.
- A parity command compares, for one model and the same items, the two engines' rendered prompts byte for byte and writes a tracked parity record: `identical`, or `divergent` naming the first divergence per item, or `unavailable` where one engine cannot expose its prompt. It runs for at least one model and its record is published (epic success check 3).
- A cross-engine quality comparison whose parity record is `divergent` or `unavailable`, or absent, is published as an observation naming the parity result, never as a paired comparison.
- Ollama's thinking switch is declared in its engine entry and verified as order 1 verifies llama.cpp's. Where Ollama offers no control, or the control cannot be verified, its rows declare `thinking_policy: allowed`, and a cross-engine comparison then refuses on `thinking_policy` under the paired-test story's rule rather than comparing `disabled` against `allowed`.

## Code it changes

- The Ollama client from order 6 extended to the quality path and to prompt capture; the parity command and its record; the Ollama thinking switch in the registry.
- The comparison command from `two-configurations-on-the-same-items-receive-a-paired-test-or-a-refusal`: reads the parity record for a cross-engine pair.

## Tests it needs

- Parity: identical, divergent (first divergence named) and unavailable records from constructed renders; a cross-engine comparison is an observation unless parity is `identical`.
- An Ollama row never carries the authored prompt in the rendered field; an absent render is explicit.
- An unverifiable switch yields `allowed` and the comparison refuses on `thinking_policy`.

## Evidence it publishes

- The parity record for `qwen3-0.6b-q8` on the classification suite, and one Ollama quality batch beside the llama.cpp batch of the same roster entry, with the resulting comparison or observation, recorded in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
