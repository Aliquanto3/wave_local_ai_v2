# Unattended implementation run, 2026-10-01

Branch `feat/ready-stories-unattended` (worktree `wave_local_ai_v2-impl`), cut from `docs/slice-remaining-epics` at `ef1249e`.

## Final report

_Pending: written at the end of the run._

## Setup

- Environment: `uv sync`, `uv run pre-commit install`. No `.env` in the worktree, and no cloud API key in the shell environment: no paid call is reachable.
- Baseline: `uv run pytest` => 1015 passed, coverage 95.74% (floor 95%). `uv run pre-commit run --all-files` => ruff check, ruff format, mypy, detect-secrets all passed.
- Local evidence prerequisites: pinned build `llama-b10537-bin-win-cuda-12.4-x64/llama-server.exe` present; `D:\ia\models` holds all four roster GGUFs. Local runs pass `LLAMA_SERVER_PATH`/`SLM_MODELS_DIR` explicitly, with `QUALITY_PROVIDERS=local` and results paths outside the committed stores.
- Side effect: `pre-commit install` in the worktree rewrote the shared `.git/hooks/pre-commit` and `pre-push` to point at the worktree venv. After removing the worktree, re-run `uv run pre-commit install` in the main repo.

## Stories

| # | Story | Outcome | Commits | Evidence |
| - | ----- | ------- | ------- | -------- |
| 1 | every-quality-batch-publishes-its-interval-and-what-it-could-resolve | skipped: acceptance wrong against the math | none | The acceptance requires the bootstrap to agree with Wilson 95% within 0.01 on each bound at n=20, p=0.80. Wilson(16/20) = [0.5840, 0.9193]. A bootstrap quantile over 20 binary items lies on the 0.05 grid, so the upper bound misses by at least 0.019. Checked with a stdlib percentile bootstrap (10 000 resamples, seeds 1/2/3 => [0.60, 0.95]). n=100 passes or fails depending on the seed (upper bound 0.87 or 0.88 vs 0.8666). Owner fix options: widen the tolerance at n=20, check Wilson only at n>=100, or use exact binomial quantiles as the reference. Also open: the story does not define the minimum detectable effect beyond "read off the same resample". No in-scope story depends on it. |
| 2 | every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens | done (review: round 1 changes required, round 2 pass) | `0a6bdfb` feat, `af67610` done | `uv run pytest` => 1074 passed, coverage 95.88%; pre-commit all passed. Stubbed judged row in task `evidence/`. Round 1 blocker fixed: Google's reasoning count is derived from the usage totals when `thoughtsTokenCount` is absent (new sixth field `reasoning_tokens_source`), so the judge cost stays reportable. For the owner: AC4 literally says a provider that does not report reasoning tokens gets a null; the derived 0 is a defensible reading that the owner should confirm. Mistral's `inside_output` billing is an assumption, not confirmed live. `judge_backends.py` still binds Mistral/Google as judges, which the epic says to retire. |

## Phase C queue: PR #54 extras (owner instruction, 2026-10-01: continue with them if the planned list finishes before the owner returns)

PR #54's head is `docs/slice-remaining-epics`. It gained nine owner-answer commits after this run's base (`116a3ad`..`20bc76d`). They are not merged here: a cherry-pick of `116a3ad` was refused by the permission classifier. So stories are read from the PR head (`git show docs/slice-remaining-epics:<path>`). A story absent from this branch gets code commits only; its `status: done` is set after the PR merges.
Planned stories that changed on the PR head: the licence story (Q43 acceptance line), the certification story (`depends_on` the suite-as-data story), the bundle story (a cross-reference only).

| # | Story | Gate |
| - | ----- | ---- |
| C1 | every-row-records-whether-its-prompt-left-the-machine | none |
| C2 | a-publication-size-cloud-batch-survives-its-rate-limits-and-resumes-per-item | none (stubbed HTTP) |
| C3 | each-quality-item-records-the-tokens-and-the-first-token-time-its-generation-took | after story 3 |
| C4 | the-composition-check-names-every-size-class-and-refuses-an-unlabelled-single-family-one | after story 12 |
| C5 | each-suite-and-machine-publishes-the-local-models-not-distinguishable-from-the-best | after story 11 |
| C6 | comparison-family-and-leader-set-records-read-as-a-fifth-table | after stories 4, 11 |
| C7 | a-campaign-is-declared-as-data-and-an-empty-cell-fails-it | after stories 3, 14 and a-gpu-run-and-a-cpu-only-run-never-share-a-fiche (check its Needs) |
| C8 | the-terse-output-variant-runs-every-item-and-meets-baseline-in-a-paired-test | after C7, story 10; check whether the local run is evidence-only |
| C9 | the-constrained-output-variant-runs-under-a-llama-cpp-grammar-and-names-its-mechanism | after C8 |
| C10 | task register-the-closed-harness-candidate-set-and-its-three-row-fields | check |
| skip | the-tabular-export-carries-the-interval-and-the-comparison-record | depends on story 1 (acceptance conflict) |

## Stories (continued)

| # | Story | Outcome | Commits | Evidence |
| - | ----- | ------- | ------- | -------- |
| 3 | every-row-names-its-prompt-variant-and-a-baseline-row-carries-the-authored-prompt | done (review round 1 pass) | `29e46ed` feat, see the next commit for done | `uv run pytest` => 1105 passed, coverage 96.01%; pre-commit passed. Gate refusal in task `evidence/baseline-gate-refusal.txt`; `wave-local-ai-v2-validate` is clean on all four committed stores. At commit time detect-secrets flagged the variant `definition_hash` (a public SHA-256); fixed with the repo's inline `pragma: allowlist secret` idiom. Gap: `pre-commit run --all-files` cannot catch this, because the secrets hook scans nothing without staged filenames. Non-blocking follow-ups: an unhashable `prompt_variant_version` raises `TypeError`, not `RowContractError`; `row_contract` imports `judge_probe` for the probe items; CHANGELOG has no schema "13" entry; `verdict.py` does not treat the variant as a comparability field; the variant registry is not exported into the published bundle. |
| 4 | the-published-bundle-reads-as-four-flat-tables-and-their-column-dictionary | done (review round 1 pass) | `8f21d7e` feat, `11c1ef3` done | `uv run pytest` => 1137 passed, coverage 96.44% (`bundle_export.py` 100%); pre-commit passed; per-file secrets scan clean. Recomputing all four runs' `suite_accuracy` (0.8, 0.95, 0.8, 0.9) and the per-language values from `quality_items.csv` alone matches (task `evidence/recomputation.md`); two runs are byte-identical. Implemented against the owner-approved fifth-table reference from the PR head. Non-blocking follow-ups: no guard against a stale cited roster entry (the bundle cites `roster_version` 1, the file is v2, and the cited entry is byte-identical today); a non-object JSONL line crashes instead of refusing; byte-identity is not proved across OSes. Stale doc: `aidd_docs/results/README.md` still says `SCHEMA_VERSION` "8" (the live value is "14"). |

## Paused 2026-10-02 after story 4 (owner needed the PC)

Code state: clean and committed at the commit that adds this section. The last full gate is story 4's: 1137 passed, coverage 96.44%.
Resume with story 5, then the Phase B gate (Q1, Q4, Q11, Q20, Q30, Q43, Q70 and Q74 are all answered "(a), the recommended default" in the live `owner-questions.md`), then the Phase C queue above.
Subagent briefs: `implementer-brief.md` and `reviewer-brief.md` in this folder.
Run rules learned: a subagent that stalls gets resumed with SendMessage, reading and writing files in smaller pieces. Run detect-secrets on the staged files: `--all-files` scans nothing for that hook. The cherry-pick of `116a3ad` was refused by the permission classifier, so read PR #54 stories from `docs/slice-remaining-epics` read-only. Licence story 15: implement against the owner's Q43 line (on the PR head), not the worktree copy.
Update: the owner cherry-picked `116a3ad` by hand as `2e7b7d5`. The worktree copies of the licence story (Q43 line) and the certification story (`depends_on`) are now current. The later PR #54 commits (`52eb15e`..`20bc76d`) are still not on this branch.

## Resumed 2026-10-02

Baseline on resume: `uv sync`, `uv run pytest` => 1137 passed, coverage 96.44%, matching story 4's gate. Phase B gate re-read in the live `owner-questions.md`: Q1, Q4, Q11, Q20, Q30, Q43, Q70 and Q74 all carry "(a), the recommended default".

| # | Story | Outcome | Commits | Evidence |
| - | ----- | ------- | ------- | -------- |
| 5 | a-thinking-switch-the-template-ignores-is-refused-never-published-as-disabled | done (review round 1 pass) | `e9c1c69` feat, `898f1dd` done | `uv run pytest` => 1163 passed, coverage 96.47%; pre-commit passed; staged-file secrets scan clean. Live verification on `qwen3-0.6b-q8` under b10537: the render with the control ends in an empty think block, the render without it does not, verified (task `evidence/live-verification.md`, no results store written). Outside the story's file list, `bundle_export.py` (roster table refuses an undescribed field) and `judge_probe.py` (also a `disabled` batch) had to change. Non-blocking follow-ups: a control naming `messages`, `max_tokens` or a sampler key is accepted and overrides them; the fiche is written before the verification, so a refused batch leaves a fiche (no row); `allowed` byte-identity is proved at client level only; the committed `quality-reference.jsonl` local rows predate the chat path, so the "published row" invariance holds for rows since schema 11. |
| 6 | a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli | done (review round 1 pass) | `d66f760` feat, `8fe1211` done | `uv run pytest` => 1201 passed, coverage 96.70%; pre-commit passed; staged-file secrets scan clean. Both prompt-set hashes unchanged and pinned; regenerating the snapshots leaves `git diff --exit-code aidd_docs/results/` at 0 (task `evidence/snapshot-regeneration.txt`); an unregistered id is refused naming the registered ones (`evidence/unregistered-suite-refusal.txt`). User-visible: `--suite classification|translation` is now refused, the ids are `classification-support-routing` and `translation-business-short-form`; the default run is unchanged. Backlog contradictions: the licence story's Q43 line names `classification_suite.py` and `translation_suite.py` as holding item literals, which they no longer do (items are in `src/wave_local_ai_v2/suite_data/*.json`, `judge_probe.py` still holds `JUDGE_PROBE_ITEMS`); interval order 4 describes its level and licence fields as module literals, now data keys. Non-blocking: `exact_label_match` scores against the fixed classification `LABELS`; unknown definition keys are carried, not refused. |
