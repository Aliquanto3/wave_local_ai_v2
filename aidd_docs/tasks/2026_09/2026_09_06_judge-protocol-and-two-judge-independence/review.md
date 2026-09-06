# Review: A judge call carries its versioned prompt and rubric, and two judges of different families or an honest single-judge flag

- **Verdict**: changes-requested
- **Diff**: `main...feat/judge-protocol-and-agreement`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_06
- **Findings**: 0 critical, 2 warning, 4 minor

## Phases

### Phase 1 — Versioned judge prompts and rubrics, the judge call, the contract bump

- [x] Rendering an item tagged `fr` returns `template_id == "judge-prompt-fr"` and the French shell — `src/wave_local_ai_v2/judge_protocol.py:288`, `tests/test_judge_protocol.py:38`
- [x] Rendering the same item tagged `de` returns the DE id and a different hash from the FR one — `tests/test_judge_protocol.py:48`
- [x] Editing a shell's text yields a different hash while the rubric version is unchanged — `tests/test_judge_protocol.py:56`
- [x] A rubric revised to `version="2"` reports the new version and byte-identical template hashes — `tests/test_judge_protocol.py:63`
- [x] `template_hash` of the filled prompt differs from the recorded hash — `src/wave_local_ai_v2/judge_protocol.py:116`, `tests/test_judge_protocol.py:87`
- [x] A missing shell and a missing rubric text each raise `UnsupportedJudgeLanguageError` naming the language — `src/wave_local_ai_v2/judge_protocol.py:234,245`
- [x] A `Rubric` whose kind and populated field disagree is refused at construction — `src/wave_local_ai_v2/judge_protocol.py:150`
- [x] A stubbed backend returning the expected answer form yields a score in `rubric.scale`, `failure_reason is None`, `raw_text` unchanged — `src/wave_local_ai_v2/judge.py:161`, `tests/test_judge.py:60`
- [x] `"7"` on the 1-5 rubric yields `score is None` and `judge_score_out_of_scale`, asserted as `is None` — `tests/test_judge.py:74`
- [x] Prose with no score yields `judge_response_unparseable` and keeps the prose — `tests/test_judge.py:82`
- [x] `""` yields `judge_response_empty` — `src/wave_local_ai_v2/judge.py:115`
- [x] A backend raising an arbitrary exception propagates out of `run_judge_call` — `src/wave_local_ai_v2/judge.py:159`, `tests/test_judge.py:132`
- [x] `judge.py` names no provider client — `tests/test_judge.py:141`, `tests/test_judge.py:294`
- [x] A deterministic quality row validates under `SCHEMA_VERSION == "9"` — `src/wave_local_ai_v2/row_contract.py:365`, `tests/test_row_contract.py:456`
- [x] A judged row stripped of exactly one judge field is refused by name, once per field — `src/wave_local_ai_v2/row_contract.py:373`, `tests/test_row_contract.py:471`
- [x] An empty `judges` list, or a first entry lacking `raw_text`, is refused structurally — `src/wave_local_ai_v2/row_contract.py:387,397`
- [x] `judge_prompt_language == "es"` and an unknown `rubric_kind` are each refused by value — `src/wave_local_ai_v2/row_contract.py:405,412`

### Phase 2 — Agreement statistics and the contested rule

- [x] Quadratic kappa on `A=[1,2,3,4,5]`, `B=[1,2,3,4,4]` equals `16/17` — re-derived by hand in `Verification` below, not read from the test constant — `src/wave_local_ai_v2/agreement.py:120`
- [x] The same pair unweighted equals `0.75` (`po=0.8`, `pe=0.2`) — re-derived by hand below — `src/wave_local_ai_v2/agreement.py:118`
- [x] Both judges constant at `3`: `value is None`, reason `zero_variance` — `src/wave_local_ai_v2/agreement.py:93`
- [x] One judge constant, the other varying: `None` with `zero_variance`, not the defined `0` — `tests/test_agreement.py:71`
- [x] An ordinal `Agreement` names the quadratic statistic, a categorical one the unweighted — `src/wave_local_ai_v2/agreement.py:202`
- [x] A categorical `Agreement` carries `within_one_rate is None`; the ordinal one `1.0` — `src/wave_local_ai_v2/agreement.py:210`
- [x] One `(4, None)` pair lowers `n_items`, sets `n_items_excluded == 1`, leaves kappa unchanged — `src/wave_local_ai_v2/agreement.py:186`
- [x] An empty pair list returns `value is None` with a null reason and raises nothing — `src/wave_local_ai_v2/agreement.py:93` (reason is `zero_variance`; see finding 1)
- [x] `(3,4)` not contested, `(2,4)` contested by delta, a category mismatch contested by category — `src/wave_local_ai_v2/agreement.py:249,259`
- [x] `max_ordinal_delta=2` stops `(2,4)` being contested — the threshold is read, not hardcoded — `src/wave_local_ai_v2/agreement.py:255`
- [x] A pair with a `None` score is not contested — `src/wave_local_ai_v2/agreement.py:246`
- [x] Five items with one contested: four averaged, `n_excluded == 1`, headline moves when un-flagged — `src/wave_local_ai_v2/agreement.py:286`
- [x] All five contested: `score is None`, `n_included == 0`, `n_excluded == 5` — `src/wave_local_ai_v2/agreement.py:297`
- [x] `CONTESTED_ORDINAL_MAX_DELTA` unset resolves `1`, `2` resolves `2`, `-1` raises `SettingsError` naming it — `src/wave_local_ai_v2/settings.py:295`

### Phase 3 — Independence by family, refusals, egress and judge cost

- [x] `family_of` resolves the three named model ids — `src/wave_local_ai_v2/roster.py:78`
- [x] A `RosterEntry` carrying `family` resolves through the entry; `family=None` falls back to `MODEL_FAMILIES` — `src/wave_local_ai_v2/roster.py:267`
- [x] An unknown model raises `RosterError` naming the id, nothing defaulted — `src/wave_local_ai_v2/roster.py:274`
- [x] The shipped roster still loads, `family` is `None`, `roster_version` unchanged at `1` — `tests/test_roster.py:375`
- [x] The Mistral backend maps a stubbed 200 body to a `JudgeResponse` with provider, family, model id and token counts — `src/wave_local_ai_v2/judge_backends.py:72`
- [x] The Google backend returns the equivalent shape; the same `run_judge_call` consumes both — `tests/test_judge.py:249`
- [x] A stubbed 429 exhausting the budget propagates out of the backend — `tests/test_judge.py:274`
- [x] `judge_backends.py` is the only judge-path module naming a client — `tests/test_judge.py:294`
- [x] A Mistral judge on a Mistral subject raises `JudgeFamilyCollisionError` with zero HTTP calls — `src/wave_local_ai_v2/judge.py:196`, `tests/test_judge.py:307`
- [x] A local `qwen` subject yields two `judges`, non-null `agreement`, `single_judge is False`, `providers == ["google","mistral"]`, `judge_call_count == 2` — `src/wave_local_ai_v2/judge.py:254` (the `agreement` object is non-null but its `value` is always null; see finding 1)
- [x] A `mistral` cloud subject yields one entry, `agreement is None`, `single_judge is True` with a reason, `judge_call_count == 1` — `src/wave_local_ai_v2/judge.py:265` (the reason is a constant, not derived; see finding 2)
- [x] The block's key set equals `row_contract.JUDGED_FIELDS` by set equality — `tests/test_judge.py:342`
- [x] A 2-point disagreement sets `contested` with its reason and keeps both scores; the single-judge block is not contested — `src/wave_local_ai_v2/judge.py:262,272`
- [x] A Mistral and a Google record are each costed at their own table's rates, aggregate is their sum — `src/wave_local_ai_v2/cost.py:186`
- [x] `tokens_in=None` makes that provider's and the aggregate `cost_total` `None` — `src/wave_local_ai_v2/cost.py:189`
- [x] A judge model absent from its price table raises `CostTableError` naming it — `src/wave_local_ai_v2/cost.py:176`
- [x] A judged row's top-level `cost_total` is unmoved by the judge block — `tests/test_row_contract.py:610`; structurally guaranteed by `JUDGED_FIELDS & REQUIRED_FIELDS["quality"] == ∅`
- [x] `agreement=None` with `single_judge=False` is refused naming both — `src/wave_local_ai_v2/row_contract.py:422`
- [x] `single_judge=True` with a non-null `agreement` is refused naming the contradiction — `src/wave_local_ai_v2/row_contract.py:429`
- [x] `judge_call_count` disagreeing with `len(judges)` is refused — `src/wave_local_ai_v2/row_contract.py:446`
- [x] `SCHEMA_VERSION` is still `"9"` after this phase — `src/wave_local_ai_v2/row_contract.py:52`

### Phase 4 — CHANGELOG and memory

- [x] Every module, constant, default and env var named in the CHANGELOG resolves in the tree — each opened and confirmed
- [x] The entry states the bump, the conditional requirement, the cost treatment and the absence of live calls, in the file's voice — `CHANGELOG.md:12`
- [x] The entry names the kappa divergence from the PRD and the epic — `CHANGELOG.md:50`
- [x] `codebase-map.md` names all four modules and which may import a client; the mermaid block is unchanged — `aidd_docs/memory/codebase-map.md:22`
- [x] `ecosystem.md` states the refusal, the single-judge consequence and the call volume; the mermaid block is unchanged — `aidd_docs/memory/ecosystem.md:29`
- [x] `uv run pre-commit run --all-files` and `uv run pytest` both pass — 4 hooks passed; 586 tests passed, coverage 96.05%

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | fit | 2, 3 | `src/wave_local_ai_v2/agreement.py:93`, `src/wave_local_ai_v2/judge.py:257` | `judge_item` computes the suite-level statistic over a single pair, so `agreement["value"]` is `None` on **every** two-judge row and the reason published is `zero_variance` — vacuously true for `n=1` and false as an explanation. A reader sees "a judge's scores had no variance" where the truth is "kappa is not a per-item quantity". Story 4 asks for kappa "over the suite's judged items"; the reason field is the row's only account of why the figure is absent. | Add `KAPPA_NULL_INSUFFICIENT_ITEMS = "insufficient_items"`, returned before the variance check when fewer than two usable items are given, so a per-item block and an empty pair list both say why they carry no kappa and the suite-level computation keeps `zero_variance` for the case it names. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/judge.py:267` | `single_judge_reason` is hardcoded to `SINGLE_JUDGE_REASON_CLOUD_SUBJECT` for any one-judge call. `judge_item` cannot know why one judge was passed — `select_judges` refuses rather than filters, so the collision never happens inside it. A local subject judged by one judge (one provider key absent, the case `quality_cli._try_run_cloud_provider` already handles) publishes "cloud_subject_other_family_only" on a row whose subject is local: a false reason in the field whose whole job is to be honest. | Take the reason from the caller: keyword-only `single_judge_reason: str \| None = None`, refused when one judge is selected and none is given, and name the second case (`SINGLE_JUDGE_REASON_ONE_JUDGE_AVAILABLE`) so story 6 has both to choose from. |
| 🟢 | rot | 2 | `src/wave_local_ai_v2/agreement.py:147` | `exact_match_rate` returns `0.0` over an empty input — the same fabricated figure the module's own docstring says `cost.total_or_none` and `aggregation.spread` refuse. `n_items` beside it is the only thing telling a reader the rate is over nothing. | Widen to `float \| None` and return `None`, or keep the convention and say in `Agreement` that `exact_match_rate` is meaningless when `n_items == 0`. |
| 🟢 | rot | 1, 3 | `src/wave_local_ai_v2/row_contract.py:279` | The comment says "the inner key sets a judged row's three records carry. Declared here, on the contract, rather than in the modules that build them", then declares two: the third, `JUDGE_CALL_RECORD_FIELDS`, is imported from `judge.py:100`. The stated principle and the code disagree in adjacent lines. | Either move the judge-call key set onto the contract beside the other two, or reword the comment to say two are declared here and one is derived from the `TypedDict` that defines it. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/agreement.py:93` | The zero-variance return precedes the unknown-category check, so a constant score set holding a value outside `categories` returns `zero_variance` instead of the `ValueError` the same input raises when it varies. Same input class, two outcomes. | Validate the scores against `categories` before the variance return. |
| 🟢 | conform | 2 | `src/wave_local_ai_v2/agreement.py:228` | `DEFAULT_CONTESTED_THRESHOLD` is built from the module constant `settings.DEFAULT_CONTESTED_ORDINAL_MAX_DELTA`, never from `load_settings().contested_ordinal_max_delta`. A caller passing `agreement.DEFAULT_CONTESTED_THRESHOLD` silently ignores `CONTESTED_ORDINAL_MAX_DELTA`, which `.env.example:35` presents as live. Harmless today (no caller), a trap for story 6. | Have story 6 build `ContestedThreshold(settings.contested_ordinal_max_delta)` from the loaded settings, and say on `DEFAULT_CONTESTED_THRESHOLD` that it is the unconfigured default. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (56/56) |
| Files checked | `src/wave_local_ai_v2/judge_protocol.py`, `judge.py`, `judge_backends.py`, `agreement.py`, `roster.py`, `cost.py`, `row_contract.py`, `settings.py`, `.env.example`, `CHANGELOG.md`, `aidd_docs/memory/codebase-map.md`, `aidd_docs/memory/ecosystem.md`, `tests/test_judge_protocol.py`, `test_judge.py`, `test_agreement.py`, `test_roster.py`, `test_cost.py`, `test_row_contract.py`, `test_settings.py` |
| Unchecked     | none |
| Unplanned     | none — `tests/test_settings.py` and `tests/test_cost.py` are not in phase 2's and phase 3's projections but every added test traces to a stated criterion |

**Kappa re-derived by hand, independently of the tests' constants.** `A=[1,2,3,4,5]`, `B=[1,2,3,4,4]`, categories `(1,2,3,4,5)` at positions `0..4`, `N=5`. Confusion matrix `O`: `O[0][0]=O[1][1]=O[2][2]=O[3][3]=1` and `O[4][3]=1`, every other cell `0`. Row marginals `p̂(A) = (0.2, 0.2, 0.2, 0.2, 0.2)`; column marginals `p̂(B) = (0.2, 0.2, 0.2, 0.4, 0.0)`.

Quadratic, `W(i,j) = (i−j)²`. Numerator `ΣΣ W·Õ`: only the off-diagonal cell contributes, `(4−3)²·1/5 = 0.2`. Denominator `ΣΣ W·Ẽ = Σ_j p̂(B)_j · Σ_i (i−j)² · 0.2`, with `Σ_i (i−j)²` equal to `30, 15, 10, 15, 30` for `j = 0..4`, giving `0.2·(0.2·30 + 0.2·15 + 0.2·10 + 0.4·15 + 0.0·30) = 0.2·17 = 3.4`. `κ = 1 − 0.2/3.4 = 16/17 = 0.9411764705882353`.

Unweighted, `W(i,j) = 0 if i == j else 1`. Numerator `= 1/5 = 0.2`, so `po = 0.8`. Denominator `= 1 − Σ_i p̂(A)_i·p̂(B)_i = 1 − 0.2·(0.2+0.2+0.2+0.4+0.0) = 0.8`, so `pe = 0.2`. `κ = 1 − 0.2/0.8 = 0.75`.

Both match `src/wave_local_ai_v2/agreement.py:117-133` as implemented and the values the acceptance criteria name. Omitting the conventional `/(k−1)²` on the quadratic weights is confirmed harmless: the factor divides numerator and denominator alike and cancels.
