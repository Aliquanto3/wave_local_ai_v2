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

Blocked: by the spike `aidd_docs/backlog/spikes/does-ollama-expose-the-prompt-it-finally-rendered.md` (`blocked`; desk research done, only its live session remains: `_debug_render_only` renders on Ollama v0.35.1 for the first EN and the first FR classification item, `think` on and off, byte diff against llama.cpp b10537 `/apply-template`). And through `depends_on` on `aidd_docs/backlog/stories/ollama-runtime-rows-stand-beside-llama-cpp-rows-on-the-same-artifact.md` (order 6, `proposed`), blocked in turn by the live session of spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`, whose running instance this spike's commands also need. Its other `depends_on` is `done`.

Current state (verified on `main` at `c68b23e`, 2026-10-03):

- Local llama.cpp quality rows carry `prompt_capture: reconstructed` (`quality_cli._local_call_path`: the string comes from `/apply-template`, not from the generation's response); `prompt_provenance` knows `captured` and `reconstructed` only, with no value for an absent render.
- `thinking_policy` is the suite's declared policy, published unchanged on every row of a batch (`row_contract` comment above `THINKING_POLICY_DISABLED`; `quality_cli` writes `spec.thinking_policy`); both suites in `suite_data/` declare `disabled`.
- `local_client.thinking_kwargs` refuses a `disabled` batch on an engine whose `thinking_switch` is `none`, and `local_client.check_engine_carries` refuses a roster control not spelled in the engine's `request_field`. Every roster entry's `thinking_control` is spelled `{"chat_template_kwargs": {"enable_thinking": false}}` (`aidd_docs/roster/models.json`), so an Ollama entry whose field is `think` refuses every entry under `disabled` until the control has a per-engine spelling.
- `local_client.verify_thinking_control` verifies a switch by rendering through `/apply-template` with and without it; no parity command or parity record exists; `comparison.DIMENSIONS` has no engine axis, and `thinking_policy` is among `comparison._ABSENCE_REFUSAL_FIELDS`.
- Spike desk findings, unverified until the live session: no `captured` path exists on Ollama, so its rows can carry `reconstructed` at most; the candidate render path `_debug_render_only` is undocumented, so the engine entry must pin the version it was verified on; the switch is spelled `think` and reaches the template as `chat_template_kwargs.enable_thinking`.

## Acceptance

- The quality path runs on Ollama for a local roster entry, writing ordinary quality rows with per-item scores in the shape the store already holds, under the same suite, caps, scorer and variant function as on llama.cpp.
- Each Ollama quality row publishes the prompt Ollama received with its `prompt_capture` kind, or carries an explicit absence of a rendered prompt; it never publishes the authored or pre-template prompt as if it were the rendered one.
- A parity command compares, for one model and the same items, the two engines' rendered prompts byte for byte and writes a tracked parity record: `identical`, or `divergent` naming the first divergence per item, or `unavailable` where one engine cannot expose its prompt. It runs for at least one model and its record is published (epic success check 3).
- A cross-engine quality comparison whose parity record is `divergent` or `unavailable`, or absent, is published as an observation naming the parity result, never as a paired comparison.
- Ollama's thinking switch is declared in its engine entry and verified as order 1 verifies llama.cpp's. Where Ollama offers no control, or the control cannot be verified, an Ollama quality batch of a suite declaring `thinking_policy: disabled` is refused before any generation, under the shipped rule (`local_client.thinking_kwargs`, `local_client.check_engine_carries`, `local_client.verify_thinking_control`), and that suite's cross-engine quality cells are listed as refused in order 3's completeness listing, with the spike `does-ollama-expose-the-prompt-it-finally-rendered.md` as their reason. `thinking_policy` keeps meaning the suite's declaration (owner answer Q117 (a), 2026-10-03).

## Code it changes

- The Ollama client from order 6 extended to the quality path and to prompt capture; the parity command and its record; the Ollama thinking switch in the registry, and the roster entry's thinking control carried in that switch's spelling.
- The comparison command from `two-configurations-on-the-same-items-receive-a-paired-test-or-a-refusal`: reads the parity record for a cross-engine pair.

## Tests it needs

- Parity: identical, divergent (first divergence named) and unavailable records from constructed renders; a cross-engine comparison is an observation unless parity is `identical`.
- An Ollama row never carries the authored prompt in the rendered field; an absent render is explicit.
- An absent or unverifiable Ollama switch refuses a `disabled` batch before any generation, and the suite's cross-engine quality cells are listed as refused with the render spike as their reason.

## Evidence it publishes

- The parity record for `qwen3-0.6b-q8` on the classification suite, and one Ollama quality batch beside the llama.cpp batch of the same roster entry, with the resulting comparison or observation, recorded in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
