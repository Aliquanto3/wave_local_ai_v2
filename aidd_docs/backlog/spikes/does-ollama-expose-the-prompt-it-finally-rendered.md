---
type: spike
status: open
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parents:
  - aidd_docs/backlog/stories/ollama-quality-rows-pass-a-prompt-parity-gate-or-publish-as-observations.md
---

# Spike: Does Ollama expose the prompt it finally rendered

## Question

Can the harness obtain, from a running Ollama instance, the exact string the model received after Ollama's own chat templating, by a documented or observable path, so that it can be published under Methodology 2 and compared byte for byte with llama.cpp's `/apply-template` output for the same model and item?

## Decision

Whether Ollama's quality rows (order 7) can carry a rendered prompt at all, and with which `prompt_capture` value: `captured` (the engine returns what it received), `reconstructed` (rendered by a separate call on the same template, as llama.cpp's path does today), or an explicit absence. The answer decides whether cross-engine quality cells can be paired comparisons or only observations, under the epic's prompt-parity decision. It also decides how the Ollama thinking switch is verified: by comparing a render with the switch against one without it, or not at all.

## Bounds

- Evidence needed: against a running pinned Ollama instance (the same one spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol` installs), for `qwen3-0.6b-q8` and two classification items, one EN and one FR: every candidate path tried and its captured output (a render or template endpoint if one exists, the template the server reports for the model, a raw or pre-templated request mode, server debug logging), and for each the string obtained; the same items rendered by llama.cpp's `/apply-template` on the same GGUF; the byte-level diff between the two; whether the path still reflects the thinking switch when it is set. A path that requires logging the prompt to a file is recorded with where that file lives, because rows and logs have different retention rules.
- Stop when: one path is shown to return the rendered string with its capture kind named, and the diff against llama.cpp is recorded, or every candidate path is shown to fail, which is recorded as "no rendered prompt available" with the attempts.
