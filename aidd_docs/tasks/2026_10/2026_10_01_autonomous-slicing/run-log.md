# Run log: autonomous slicing run (2026-10-01)

## Final report

Branch `docs/slice-remaining-epics`, ten commits, nothing pushed. No step failed; no file was deleted. Steps 4, 5, 6 and 8 ran in parallel at the owner's request mid-run; commits stayed in step order.

### Per epic

| Epic | Stories ready | Stories proposed | Spikes | Other |
| --- | --- | --- | --- | --- |
| a-score-is-published-with-its-interval-a-difference-with-its-test | 5 | 4 | 2 | |
| any-open-ended-output-carries-two-judges-or-an-honest-flag (amendment) | 1 | 4 | 3 | Mistral probe fate is Q6 |
| every-size-class-spans-two-families-or-says-it-does-not | 3 | 5 | 1 | |
| the-engine-and-the-prompt-variant-are-measured-not-assumed | 5 | 7 | 4 | |
| no-use-case-is-silently-absent | 2 | 8 | 2 | 1 task (proposed) |
| one-download-holds-the-tables-their-licences-and-how-to-cite-them | 5 | 2 | 1 | |
| quality-scored-comparison-first-three-use-cases | 0 | 2 | 0 | judge story mismatches logged (Q50-Q58) |
| a-release-is-called-credible-only-by-its-logged-client-sessions (new) | - | - | - | epic created, proposed, no stories |
| **Total** | **21** | **32** | **13** | |

Owner questions: **53** decision entries (Q1-Q12, Q20-Q24, Q30-Q34, Q40-Q43, Q50-Q76) plus 8 mechanical findings, in `owner-questions.md`. Numbering has gaps by design (per-step ranges during the parallel phase).

### Ready stories an unattended implementation run on this PC could take

Ordered by dependency. Covers every `ready` story in the backlog, not only this run's. Excluded: `judge-scoring-with-inter-judge-agreement-proves-judged-machinery` (blocked in prose by Q51), `the-judged-probe-runs-both-paths-in-three-languages` (blocked by Q6), and `a-run-started-from-the-browser-streams-until-its-row-lands` (already implemented on the unmerged branch `feat/browser-console-run-streams-to-row`; merge it first).

**No dependency** (code and tests only; items marked "local evidence" also need one local run of the already-downloaded `qwen3-0.6b-q8` for the published evidence, possible unattended if this PC is the dev laptop)

1. a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli (take before 6: same suite files, see Q70)
2. every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish
3. every-quality-batch-publishes-its-interval-and-what-it-could-resolve
4. two-configurations-on-the-same-items-receive-a-paired-test-or-a-refusal
5. a-comparison-family-carries-its-adjusted-p-values-and-is-superseded-not-edited
6. a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source
7. a-publication-subset-redraws-to-the-same-items-from-its-recorded-rule
8. every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens
9. every-roster-entry-states-its-family-its-licence-and-its-language-claim
10. a-thinking-switch-the-template-ignores-is-refused-never-published-as-disabled (local evidence)
11. a-candidate-model-enters-the-roster-only-through-the-verification-gate-or-leaves-a-recorded-refusal (local evidence)
12. every-row-names-its-prompt-variant-and-a-baseline-row-carries-the-authored-prompt
13. every-row-names-the-engine-that-produced-it-and-the-fiche-hashes-it (local evidence; touches the fiche hash like machine story `a-gpu-run-and-a-cpu-only-run-never-share-a-fiche`, see Q74)
14. the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives
15. the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary

**Needs a paid API key**

- None of this run's ready stories.
- the-playground-reaches-a-cloud-subject-only-when-configured-and-says-so-first (pre-existing): needs a configured cloud subject key, and waits on the unmerged browser console branch through `a-client-types-to-a-local-roster-model-and-nothing-is-recorded`.

**Needs physical hardware or an operator**

- the-professional-pc-is-confirmed-able-to-take-part-before-code-depends-on-it: operator on the professional PC. It gates the whole machine chain below.
- Machine chain, in order: a-gpu-run-and-a-cpu-only-run-never-share-a-fiche, each-model-machine-and-mode-runs-under-its-own-named-profile, a-model-below-its-declared-minimum-refuses-and-the-refusal-is-published, every-view-names-the-machine-and-mode-and-cpu-only-vram-reads-not-applicable, the-laptop-proves-both-modes-and-republishes-the-bundle-once, the-tower-walks-the-fresh-clone-and-returns-both-modes, the-no-gpu-professional-pc-publishes-rows-and-refusals-beside-the-gpu-machines, each-machine-returns-its-rows-by-pull-request-and-a-hash-collision-is-refused.
- Engine stories gated transitively by that chain (`a-campaign-is-declared-as-data-and-an-empty-cell-fails-it` depends on `a-gpu-run-and-a-cpu-only-run-never-share-a-fiche`): a-campaign-is-declared-as-data-and-an-empty-cell-fails-it, then the-terse-output-variant-runs-every-item-and-meets-baseline-in-a-paired-test and the-constrained-output-variant-runs-under-a-llama-cpp-grammar-and-names-its-mechanism (both real local runs).
- one-citation-names-the-release-and-is-the-attribution-a-reuser-copies: the owner supplies the author identity.
- each-release-attaches-one-archive-that-needs-no-clone: the owner pushes a `v*` tag; someone opens the asset without a clone.
- parquet-copies-ship-beside-the-csv-and-never-disagree-with-it: an operator triggers the on-demand CI run.
- the-second-laptop-walks-the-pitch-and-the-walk-is-recorded: a second physical laptop.

## Steps

| Step | Artifact | Outcome | Commit |
| --- | --- | --- | --- |
| 0 | aidd_docs/backlog/stories/dense-and-moe-stand-side-by-side-on-the-same-items.md | status ready -> done (review passed 2026-09-22) | 807a8ac |
| 1 | epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md | 9 stories (5 ready, 4 proposed), 2 spikes, 5 questions | 48732f0 |
| 2 | epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md (amendment only) | 5 stories (1 ready, 4 proposed), 3 spikes, 4 questions | ebda4b2 |
| 3 | epics/every-size-class-spans-two-families-or-says-it-does-not.md | 8 stories (3 ready, 5 proposed), 1 spike, 3 questions | a83fa3a |
| 4 | epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md | 12 stories (5 ready, 7 proposed), 4 spikes, 5 questions (Q20-Q24) | baa9184 |
| 5 | epics/no-use-case-is-silently-absent.md | 10 stories (2 ready, 8 proposed), 1 task (proposed), 2 spikes, 5 questions (Q30-Q34) | 18d6362 |
| 6 | epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md | 7 stories (5 ready, 2 proposed), 1 spike, 4 questions (Q40-Q43) | 3e97e5c |
| 7 | epics/quality-scored-comparison-first-three-use-cases.md | 2 stories (0 ready, 2 proposed), 0 spikes, 10 questions (Q50-Q59); judge story order 2 mismatches the amended judge epic on 8 points (Q50-Q56, Q58), logged, not rewritten | 9f15db4 |
| 8 | epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md (new, proposed, no stories) | 1 epic, 10 questions (Q60-Q69) | c3dbb4e |
| 9 | aidd_docs/backlog/ (read-only health pass) | 7 decision findings (Q70-Q76), 8 mechanical findings; 3 PRD AC sub-clauses unowned (Q71-Q73); nothing changed | this commit |
