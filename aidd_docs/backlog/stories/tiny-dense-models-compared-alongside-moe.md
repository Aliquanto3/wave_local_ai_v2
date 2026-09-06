---
type: story
status: done
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
depends_on:
  - aidd_docs/backlog/stories/deterministic-classification-scoring-proves-quality-table-split.md
  - aidd_docs/backlog/stories/judge-scoring-with-inter-judge-agreement-proves-judged-machinery.md
  - aidd_docs/backlog/stories/translation-scoring-extends-deterministic-coverage.md
order: 4
---

# Story: Tiny dense models compared alongside MoE across all three use cases

**As** a consultant
**I want** tiny dense candidates (e.g. Granite 4 350M/1B, Qwen3 0.6B/1.7B/4B, Phi-4-mini, SmolLM3, Llama 3.2) scored on classification, translation, and rewriting alongside the MoE candidate already benchmarked
**So that** I can recommend whichever architecture actually performs best per use case, not assume MoE by default

## Acceptance

- For each of the three use cases, at least one tiny dense model and the MoE candidate are both present in the quality table with directly comparable scores.
- Results are shown side by side per use case, distinguishing which model produced which score.

## Divergences from what was built

This story was written on 2026-08-21, before the benchmark-methodology epic
landed, and its acceptance is two lines. Where it conflicted with the PRD's
Goals or Benchmark Methodology 13, with the shipped code, or with the
published-evidence discipline, the implementation followed those and recorded
the conflict. Delivered by
`aidd_docs/tasks/2026_09/2026_09_06_tiny-dense-models-alongside-moe/`.

| # | The story says | What was built | Why |
| - | -------------- | -------------- | --- |
| D1 | Scored "on classification, translation, **and rewriting**" | Classification and translation only | The rewriting suite does not exist; it arrives with the provider phase of the use-case epic. Two of three use cases are covered for real and nothing fabricates a rewriting row — the same divergence the translation story recorded as its D2. |
| D2 | "at least one tiny dense model" | Three, one per size slot (0.6B / 1.7B / 4B) | The PRD's Goal is "whichever model family performs best per use case", and one dense point cannot separate "dense wins" from "this particular small model wins". Three sizes make the axis readable for 4.63 GiB of download. It earned its keep: the ladder does **not** rank by size — the 1.7B is the worst of the four on classification and the 4B only ties the 0.6B — which one point would have hidden. |
| D3 | Silent on where the rows are published | The untracked live stores plus a dated section in `aidd_docs/results/README.md`; the committed reference bundle is **not** touched | The bundle is frozen at `schema_version` `"7"` and `tests/test_reference_bundle.py` asserts it; today's rows are `"10"`. Adding them would break that test or force the full regeneration job already filed as separate work. The fiches the rows cite **are** committed, so the numbers stay checkable. Same precedent as the translation suite's live run the day before. |
| D4 | Assumes the harness can launch a dense model | `settings.host_n_cpu_moe` becomes `int \| None` and `server.build_flags` omits `--n-cpu-moe` when it resolves to `None` | It could not: `SERVER_N_CPU_MOE` defaulted to `37`, `build_flags` always emitted the flag, and `validate_host_fit` refuses any non-`None` value on a dense entry — correctly, per Methodology 13. The smallest change that lets a dense entry launch **without** weakening that refusal. |
| D5 | Silent on the cloud comparator | The existing `google` rows are cited, not re-run | The live store already held `gemini-3.5-flash-lite` rows on the same suites, versions and items. Methodology asks that scores be comparable, not that they be regenerated per subject. |

The acceptance holds for the two use cases that exist, with one qualification
worth carrying forward: the dense rows measure instruction-following on a raw
`/completion` endpoint rather than classification or translation ability. The
cause, the verbatim evidence and the suite-level decision it implies are in
`aidd_docs/results/README.md` and `aidd_docs/backlog/tech-debt.md`.

## Cancellation

n/a — not cancelled.
