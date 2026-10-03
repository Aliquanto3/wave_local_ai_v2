# Run log: backlog refinement run (2026-10-02)

Branch `docs/refine-proposed-items-2026-10-02` (worktree `wave_local_ai_v2-refine`), cut from `main` at `c68b23e`. Unattended; runs beside the implementation session on `feat/night-run-2026-10-02`. Desk research only: no model run, no install, no download, no account, no provider call.

## Final report

Pending; written at the end of the run.

## Setup

- `git worktree add ../wave_local_ai_v2-refine -b docs/refine-proposed-items-2026-10-02 main` (main at `c68b23e`, equal to `origin/main`). `uv sync` done. `pre-commit install` not run (shared hooks).
- Read: `aidd_docs/memory/*` (not `external/`), the PRD, the 2026-10-01 slicing run log and owner questions (Q1-Q76, all answered), the 2026-10-01 implementation run log's "Code against the backlog".
- Spike status convention: a spike concluded from evidence is `resolved`; one that still needs a live run or an owner choice keeps its findings and moves to `blocked` (the spike lifecycle's non-terminal state for a named dependency), with what remains written in its Outcome. Either way a `blocked` spike still blocks its parents.

## Step 1: spikes

| Spike | Status | What remains | Commit |
| --- | --- | --- | --- |
| is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms | blocked | Live calls with a paid key (10 listed in the spike); Q102 (no dated id: names repointed in place), Q103 (training opt-out). Terms are compatible with the egress non-goal (training on inputs unless opted out, PRC storage, no fixed retention). | d842df4 |
| is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms | blocked | Live calls with a paid Z.ai key (8 listed in the spike); Q102 (release ids only, e.g. `glm-5.2`, and no documented model-list endpoint). `glm-5.3` excluded (forced thinking). Terms are compatible with the egress non-goal (no training on API content without consent, processed in Singapore, not stored). | 81b6634 |
| which-public-classification-benchmark-seeds-the-publication-suite-and-on-what-terms | blocked | Rung settled: permissive (both qualifying sources are CC BY 4.0). Remains Q105: MInDS-14 (support-routing intents, recommended) or MASSIVE 1.1 (the epic's lead, voice-assistant scenarios). SIB-200 and MTOP are share-alike; Amazon Reviews Multi is no-republish. | 56ad9da |
| which-public-translation-benchmark-seeds-the-publication-suite-and-on-what-terms | blocked | Source found: WMT24++ (`google/wmt24pp`, Apache-2.0, EN->FR, FR->DE, DE->EN by joining two pairs on `segment_id`). The agent marked it `resolved`; set to `blocked` here because the permissive rung rests on Google's label over WMT24 source text released "for research purposes" only, a risk for the owner: Q106. FLORES+ is share-alike and gated against re-hosting. Noted, not asked: the PRD open question's "republishes ... under CC-BY 4.0" wording does not fit an Apache-2.0 item, which keeps its own licence per Methodology 5. | 570bb17 |
| which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them | blocked | Every shortlisted family has a GGUF pinned by commit sha per class; all eight architectures are in b10537's `src/llama-arch.cpp`. MoE found below the top class (Granite 3.1 1B-A400M, 3B-A800M, Phi-tiny-MoE). Remains: one live gate load per architecture (`uv run wave-local-ai-v2-candidate-gate --candidate <entry>.json`, 8 runs), Q107 (which LFM2 models), Q108 (fold those loads into the class stories). | 939b311 |
| does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it | blocked | Dense Qwen3 uses Hermes-style `<tool_call>` JSON (b10537's autoparser, no unit test for that exact template); the MoE's Unsloth template uses Qwen3-Coder XML (dedicated, tested handler). Open engine bugs #27767, #24807, #28522 hit the probe set. All four frameworks can drive llama-server natively; Q33 overhead is readable through a recording proxy. Remains: live probes P1-P5 per roster entry, attribution with `parse_tool_calls: false`, a framework driver run on a throwaway branch; Q109, Q110. | (this commit) |
