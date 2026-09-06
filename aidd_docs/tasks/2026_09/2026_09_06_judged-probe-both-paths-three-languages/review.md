# Review: The judged probe runs both paths in three languages

- **Verdict**: blocked
- **Diff**: `main...feat/judged-probe` (`fa134c5`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_06
- **Findings**: 11 critical, 11 warning, 6 minor

## Phases

### Phase 1 — The probe items, its runner, its path, and stubbed tests

- [x] Resume skipped by name when complete, re-run when empty, refused when partial, against a caller-supplied item count — `src/wave_local_ai_v2/results.py:71-113`, `tests/test_results.py:202-241`
- [x] Quality CLI rows unchanged in shape; `tests/test_quality_cli.py` passes with no edit — `git diff main...HEAD -- tests/test_quality_cli.py` empty, `uv run pytest` 631 passed
- [x] `PROMPT_SET_HASH` unchanged and the probe hashes through the same function — `src/wave_local_ai_v2/classification_suite.py:205,226`, `src/wave_local_ai_v2/judge_probe.py:262`
- [x] `load_settings` defaults and overrides `judge_probe_reference_path` — `src/wave_local_ai_v2/settings.py:202-204`, `tests/test_settings.py:547,567`
- [x] Ten items, 4 en / 3 fr / 3 de, hand_written, uncontaminated, unique ids, no label or scoring key — `src/wave_local_ai_v2/judge_probe.py:157-253`, `tests/test_judge_probe.py:264-291`
- [x] FR and DE prompts native in instruction and material, no item repeated across languages — `src/wave_local_ai_v2/judge_probe.py:198-252` (read in full; each is distinct source material)
- [x] A stubbed run writes eleven rows, every one `row_contract.validate_row`-valid — `tests/test_judge_probe.py:304-321`
- [x] Ten local rows: `single_judge false`, two judges, one and the same non-null agreement naming its statistic — `src/wave_local_ai_v2/judge_probe.py:795-808`, `tests/test_judge_probe.py:324-351`
- [x] Cloud row: `single_judge true`, `cloud_subject_other_family_only`, `agreement is None`, one Mistral judge — `tests/test_judge_probe.py:379-399`
- [x] Every row null on `expected_label` / `predicted_label` / `correct` / `suite_accuracy`, with a non-empty `subject_output` — `src/wave_local_ai_v2/judge_probe.py:702-706,732`, `tests/test_judge_probe.py:402-415`
- [x] Every row `indicative true` with a reason naming the sub-20 count — `src/wave_local_ai_v2/judge_probe.py:717-718`, `tests/test_judge_probe.py:418-425`
- [x] Every row's verdict is `not_comparable` naming that the probe publishes no label and no score — `src/wave_local_ai_v2/judge_probe.py:725-730`, `tests/test_judge_probe.py:428-436`
- [x] An `fr` row names the French shell, a `de` row the German one, neither the English — `tests/test_judge_probe.py:519-542`; confirmed on written rows (see Verification)
- [x] An unparseable judge reply leaves `score` null with a named reason and its `raw_text`, and is counted in `n_items_excluded` — `tests/test_judge_probe.py:561-585`
- [x] A missing key or a provider absent from `QUALITY_PROVIDERS` exits 1 naming it, writes no row, launches no server — `src/wave_local_ai_v2/judge_probe.py:502-530`, `tests/test_judge_probe.py:637-665`
- [x] `--resume` against a complete run makes no cloud call and appends nothing — `tests/test_judge_probe.py:673-693`
- [x] No probe run creates or writes the quality results path — `tests/test_judge_probe.py:506-511`
- [x] `wave-local-ai-v2-judge-probe --help` prints the probe's own usage including `--resume` — `pyproject.toml:32`; run: usage block printed, exit 0

### Phase 2 — The live run: eleven judged rows, both paths, three languages

- [ ] The run completes in one invocation or through `--resume`, no setting widened — never completed; Mistral workspace returns 429 `x-ratelimit-limit-req-minute: 0` on every `POST /v1/chat/completions` (`fa134c5` commit body)
- [ ] Eleven rows, ten `local` and one `google` — `aidd_docs/results/judge-probe-reference.jsonl` does not exist
- [ ] Every row passes the contract, verified by the validator over the file — no file to validate
- [ ] Ten local rows carry a two-judge agreement whose value is a number or a non-`insufficient_items` null — no rows
- [ ] The cloud row carries `single_judge: true`, a null agreement and one Mistral judge — no rows
- [ ] An `fr` row's template hash is the French shell's and a `de` row's the German — no rows
- [ ] Each item's two scores and contested marking recorded; headline exclusion equals the contested count — no rows
- [ ] `quality.jsonl` unchanged by the run — no run reached the writer (commit body records it byte-identical, unverifiable now)
- [ ] `wave-local-ai-v2-validate` over the probe file exits 0 naming the checked count — no file
- [ ] `tests/test_reference_bundle.py` passes with no edit — passes today, but as evidence of a probe file outside the bundle it is untested: no probe file exists
- [ ] Transcript, figures, wall clock, retries and resumes recorded for phase 3 to quote — only the failure is recorded, in the commit body

### Phase 3 — The README section, the three answers, CHANGELOG and memory

- [ ] `aidd_docs/results/README.md` carries a probe section naming the file, run, subjects and judges — file untouched by the diff
- [ ] The section states the probe is not a task suite, publishes no benchmark score, sits below the gate, and does not pre-empt the rewriting suite — not written
- [ ] The section states the probe file is outside the auditor's bundle and is the one reference-named file a CLI writes — not written
- [ ] Every number in the section appears on a row — not written
- [ ] The first two-judge agreement figure stated with statistic, value or null reason, and item counts — not written; no figure exists
- [ ] The contested threshold answered in whichever of the three honest shapes the rows show — not written; no rows
- [ ] The free-tier answer gives wall clock, call count, pacing, retries, resumes and labelled arithmetic — not written
- [ ] The epic's Success Evidence block named as where the three answers are also owed — not written
- [ ] `CHANGELOG.md` gains one `Unreleased`/`Added` entry — file untouched by the diff
- [ ] `aidd_docs/memory/cli.md` documents the command's refusal, output path and resume semantics — file untouched by the diff
- [ ] `aidd_docs/memory/codebase-map.md` lists `judge_probe.py` and the fourth entry point — file untouched by the diff
- [x] The before-commit gate and the full test suite both pass — `uv run pre-commit run --all-files` four hooks Passed; `uv run pytest` 631 passed, coverage 95.94% (re-runs after phase 3's edits)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | functional | 2 | `aidd_docs/results/judge-probe-reference.jsonl` | The run never completed: every Mistral chat-completion returns 429 with `x-ratelimit-limit-req-minute: 0`, an account state no retry reaches, and the probe refuses rather than publishing single-judge rows as the two-judge path. No file exists. | Clear the Mistral workspace limit (verify or upgrade the account, or supply another key), then run `uv run wave-local-ai-v2-judge-probe`. Nothing in the code is at fault. |
| 🔴 | functional | 2 | `aidd_docs/results/judge-probe-reference.jsonl` | Eleven rows, ten `provider: local` and one `provider: google`, are not published. | Produced by the run above. |
| 🔴 | functional | 2 | `aidd_docs/results/judge-probe-reference.jsonl` | No row has been validated by `wave-local-ai-v2-validate` over the written file. | Run the validator over the file once it exists; record the checked count and exit code. |
| 🔴 | functional | 2 | `aidd_docs/results/judge-probe-reference.jsonl` | No real two-judge agreement figure exists; the only kappa produced so far is over stubbed scores. | Read `agreement` off a local row after the run. |
| 🔴 | functional | 2 | `aidd_docs/results/judge-probe-reference.jsonl` | The single-judge path is proven by a test, not by a row — the story requires "rows, not stubs". | Read the google row's `single_judge`, `single_judge_reason` and null `agreement` after the run. |
| 🔴 | functional | 2 | `aidd_docs/results/judge-probe-reference.jsonl` | No FR or DE row exists to read the French and German shell hashes off. | Read `judge_prompt_template_hash` off an `fr` and a `de` row after the run. |
| 🔴 | functional | 2 | `aidd_docs/results/judge-probe-reference.jsonl` | The per-item score pairs, the contested marking and the headline exclusion count are unrecorded. | Record them off the rows after the run. |
| 🔴 | functional | 2 | `aidd_docs/results/quality.jsonl` | "Unchanged by the run" is asserted in a commit body, not by a before/after diff a reader can repeat. | Snapshot `quality.jsonl` before the live run and diff after. |
| 🔴 | functional | 2 | `tests/test_reference_bundle.py` | The test passes, but "the probe file is not part of the bundle" is untested while no probe file exists. | Re-run the test after the file lands. |
| 🔴 | functional | 2 | `aidd_docs/tasks/.../phase-2.md` | The transcript, wall clock, retry and resume counts phase 3 must quote are not recorded. | Keep the full stdout/stderr transcript of the successful run. |
| 🔴 | functional | 2 | `src/wave_local_ai_v2/judge_probe.py` | No setting was widened to force completion — correct, but the criterion is unverifiable until a run completes. | Re-check after the run; do not widen `CLOUD_RETRY_MAX_ATTEMPTS` or the pacing intervals. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | No probe section: the file, its run, its two subjects and its two judges are undocumented. | Write it off the published rows once phase 2 lands. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | The probe's non-suite status, its zero benchmark score, its deliberate sub-gate size and its non-pre-emption of the rewriting suite are stated only in the module docstring, not in the README a reader opens. | Write the paragraph phase 3 task 1.2 specifies. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | The probe file's exclusion from the auditor's bundle, and its status as the one reference-named file a CLI writes, are stated only in `settings.py:25-31`. | Write the paragraph phase 3 task 1.3 specifies. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | The per-item table, batch block, single-judge row, language evidence and cost/egress figures are unpublished. | Publish them off the rows. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | The epic's first closing question — what the first real two-judge agreement figure was — is unanswered. | Answer with the statistic name, value or null reason, `n_items` and `n_items_excluded`. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | The epic's second closing question — whether the contested threshold met genuine disagreement — is unanswered. | Answer in whichever of the three honest shapes the rows show. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | The epic's third closing question — free-tier impractical or merely slow — is unanswered. | Answer with wall clock, call count, pacing, retries, resumes and labelled extrapolation arithmetic. |
| 🟡 | functional | 3 | `aidd_docs/results/README.md` | The epic's Success Evidence block is not named as the second place the three answers are owed. | Name the file and the block without editing the backlog. |
| 🟡 | functional | 3 | `CHANGELOG.md` | No `Unreleased`/`Added` entry for the probe, its two divergent behaviours, or what it deliberately does not do. | Write the entry phase 3 task 3 specifies. |
| 🟡 | functional | 3 | `aidd_docs/memory/cli.md` | The fourth command is undocumented: the next session will not know it exists. | Add the entry, refusal behaviour, output path and resume semantics included. |
| 🟡 | functional | 3 | `aidd_docs/memory/codebase-map.md` | `judge_probe.py` and the fourth entry point are absent from the map. | Add both inside the existing structure. |
| 🟢 | rot | 1 | `src/wave_local_ai_v2/judge_probe.py:548-588,312-313` | `_generate_local_outputs` is a near-verbatim copy of `quality_cli._run_local_suite` (`quality_cli.py:515-553`) — same POST, same two-branch content validation, same message strings — and `LocalCompletionError` is a second class with the same name and docstring as `quality_cli.py:124-125`. The same argument the branch used to create `quality_rows.py`. Not fixed here: extracting the POST would move both test suites' `requests.post` patch targets, breaking phase 1's criterion "`tests/test_quality_cli.py` passes with no edit". | Extract to a `local_client.py` beside `mistral_client`/`google_client`, returning `(content, truncated, generated_tokens)`, and re-point both test suites' patches — in an increment that is allowed to edit `test_quality_cli.py`. |
| 🟢 | rot | 1 | `src/wave_local_ai_v2/judge_probe.py:73,78,89-105` | `REQUEST_TIMEOUT_S`, `_RETRY_BASE_DELAY_S` and the two subject sampling blocks are copied from `quality_cli.py:74,121,86-115` with comments stating they must stay identical. Nothing enforces it, so the first edit to one silently makes a probe generation unlike a quality generation. | Move the two sampling blocks and the timeout into a shared module (`quality_rows.py` already imports nothing from either CLI), or assert equality in a test. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/judge_probe.py:766-768` | The subject's family is resolved after `measure_energy` has launched llama-server and generated ten outputs. A roster entry whose family is undeclared and unknown to `MODEL_FAMILIES`, or one colliding with a judge's family, aborts only then — against the module's own "a probe missing a judge must cost nothing at all". Unreachable today: the roster holds one Qwen entry. | Resolve `roster.family_of(roster_entry.display_id, roster_entry)` and call `judge.select_judges` in `_preflight_judges`, before the server launches. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/judge_probe.py:605-617` | `_judge_item_naming_failures(item_id, **kwargs: Any)` erases `judge.judge_item`'s keyword-only signature, so mypy checks neither call site against it. | Spell the parameters out, or accept a pre-bound `Callable[[], dict[str, Any]]` and keep the typed call at the site. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/judge_probe.py:368-390` | `main()` catches ten exception types but not `judge.JudgeFamilyCollisionError` nor the bare `ValueError`s `_item_by_id:545` and `_judge_score:625` raise, so those surface as a traceback rather than the one stderr line and exit 1 the module promises. | Add `ValueError` to the caught set (it covers both, `JudgeFamilyCollisionError` included), or raise named errors already in the set. |
| 🟢 | conform | 1 | `src/wave_local_ai_v2/judge_probe.py:446-447,878-904` | One `RetryBudget` per provider spans two batches for Google (ten judge calls plus the subject's two requests), against `retry.RetryBudget`'s own docstring, "One instance per provider batch, not one per call". Ten judge retries therefore leave the cloud generation none. | Either give the cloud-subject batch its own budget, or amend the docstring to say a caller may scope one across a whole run and why the probe does. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 46% (19/41)                                       |
| Files checked | `src/wave_local_ai_v2/judge_probe.py`, `quality_rows.py`, `results.py`, `settings.py`, `classification_suite.py`, `quality_cli.py`, `tests/test_judge_probe.py`, `tests/test_results.py`, `tests/test_settings.py`, `pyproject.toml`, `.env.example` |
| Unchecked     | Phase 2, all eleven criteria — `fix`; Phase 3, eleven of twelve criteria — `fix` |
| Unplanned     | none — every changed file appears in phase 1's architecture projection |
| Rows read     | `aidd_docs/results/judge-probe-reference.jsonl` absent, so the three row-level checks below were run against the only probe rows that exist: those a stubbed end-to-end run writes. They verify the machinery, not the live rows. |
| Judge prompt language, off the rows | the four `en` rows carry `judge-prompt-en`/`1677b9311946…`, the three `fr` rows `judge-prompt-fr`/`e25b3dcd0c70…`, the three `de` rows `judge-prompt-de`/`d0dc7cd302f1…`; no non-`en` row carries the English hash. The FR and DE shells (`judge_protocol.py:63-90`) are written natively in their own language. |
| Kappa recomputed from the rows | mistral `[5,4,3,5,4,3,5,4,3,5]` vs google `[5,4,4,5,3,3,5,4,5,5]`: an independent quadratic-weighted Cohen's kappa over the rubric's five ordered points gives `0.5522388059701493`, equal to the `agreement.value` published on all ten rows. Both the normalised and unnormalised weight forms give that value, confirming `agreement.py`'s docstring claim that `/(k−1)²` cancels. |
| Agreement/contested consistency | `exact_match_rate` 0.7 = 7/10 identical pairs; `within_one_rate` 0.9 = 9/10 within one point; `n_items` 10 / `n_items_excluded` 0 match the ten usable pairs; the one contested row is `summarise-de-01` (3 vs 5, \|Δ\|=2 > `max_ordinal_delta` 1) reasoned `ordinal_delta_above_threshold`; `judged_headline_excluded_n` 1 equals the contested count and `judged_headline_score` 4.2222… equals the mean of the nine non-contested item means. The google row carries `agreement: null`, `agreement_statistic: null`, `single_judge: true` / `cloud_subject_other_family_only`, one Mistral judge record. |
