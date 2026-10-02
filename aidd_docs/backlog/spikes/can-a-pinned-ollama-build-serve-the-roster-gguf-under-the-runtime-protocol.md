---
type: spike
status: open
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parents:
  - aidd_docs/backlog/stories/ollama-runtime-rows-stand-beside-llama-cpp-rows-on-the-same-artifact.md
  - aidd_docs/backlog/stories/what-a-default-ollama-install-costs-is-published-as-its-own-figure.md
---

# Spike: Can a pinned Ollama build serve the roster's own GGUF under the runtime protocol

## Question

Can a pinned, installable Ollama build on the reference machine load a roster entry's own GGUF file with a checksum a run can match against the entry's `sha256`, report its own version, its effective context and every configuration default it applies, show what it has loaded and whether another client is using it, and keep the model loaded across the runtime protocol's warm-up, counted repetitions and recorded cooldowns without a silent reload?

## Decision

Whether Ollama can be registered as the `attached` comparator engine entry (order 6) and with which build inputs: the pinned version and the live endpoint that reports it; the health and chat endpoints and the default port; how a model definition points at a roster GGUF and whether `artifact_parity: same_gguf` is reachable, or only `engine_supplied`; the endpoint that lists loaded models and whether concurrent clients are observable at all; the keep-alive setting, its default, and how it is pinned for a run; the effective context the engine reports and whether a prompt longer than it is truncated silently or refused; the per-generation timings it reports and whether its first-token time is server-reported (Methodology 20); and the thinking control's spelling, if any. The same answers fix what the defaults side-run (order 11) records about a default install: its quant choice, its context default and whether a library tag matches a roster entry.

## Bounds

- Evidence needed: captured live requests and responses against a running instance of a named, pinned Ollama version on the reference machine, never a documentation page alone (the epic's rule for these unknowns). For `qwen3-0.6b-q8`: a model created from the roster entry's own file and the checksum the engine reports or the file it reads; the version endpoint's response; the loaded-model listing before, during and after a run; whether a second client's request is visible from the harness side; generation timings across a warm-up plus five counted repetitions separated by the 10 s default cooldown, with any reported load duration per repetition; the configured and the reported context, and the result of one prompt deliberately longer than the default context; the configuration defaults the server reports for the loaded model, each marked engine-reported or not reported; whether the Qwen thinking control is forwarded, spelled as its own parameter, or absent. For the defaults side-run: the quant and context a default install picks when the matching library tag is pulled, and whether a tag exists for the MoE flagship (input to Q21).
- Stop when: each build input above is answered from a captured call, or Ollama is shown unable to hold the model loaded across the protocol, unable to report its version by live probe, or unable to state its effective context; any of these three is recorded as the finding that blocks the comparator entry, with the evidence.
