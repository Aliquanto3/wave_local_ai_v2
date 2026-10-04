# Phase 3: Docs and the laptop evidence

## Steps

1. Memory docs (`codebase-map.md`, `cli.md` if it names variants), `aidd_docs/results/README.md` share of baseline outputs outside the declared format.
2. Live: a per-request `grammar` check on b10537; campaign `constrained-output-laptop` (llama.cpp x {baseline, constrained_output} x qwen3-0.6b-q8 x classification-support-routing); both runs; completeness; `wave-local-ai-v2-compare --dimension prompt_variant`; validate. All outputs in `evidence/`.
