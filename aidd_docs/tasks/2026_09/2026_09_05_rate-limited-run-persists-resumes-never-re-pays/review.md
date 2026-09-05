# Review: A rate-limited run persists, resumes, and never re-pays

- **Verdict**: blocked
- **Diff**: `main...feat/paced-resumable-cloud-runs`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_05
- **Findings**: 2 critical, 3 warning, 3 minor

## Phases

### Phase 1 — The pacing/retry primitives (`retry.py`)

- [ ] A fake-clock `Pacer` fed a scripted sequence of `.wait()` calls sleeps exactly the amounts the Journey table states, and the first call never sleeps — the first-call half holds (`tests/test_retry.py:38`), the Journey's other half ("each call is `>= min_interval_s` after the previous") does not: `retry.py:47` advances `_last_call_at` by exactly `min_interval_s` even when no sleep happened, so a call that outlasts the interval leaves a deficit the pacer then spends as unpaced back-to-back requests. `tests/test_retry.py:48` scripts only `elapsed == interval` and never the `elapsed > interval` path.
- [x] `call_with_retry` on a fn raising once then succeeding returns `(result, 1)` and calls the stub `sleep` exactly once — `tests/test_retry.py:82-83`
- [x] `is_retryable` returning `False` re-raises with no sleep and no budget consumption — `tests/test_retry.py:126-127`
- [x] A present `retry_hint_s` value is passed to `sleep` verbatim — `tests/test_retry.py:106` (jitter stubbed at 999.0 to prove no blend)
- [x] `RetryBudget(max_retries=N)` exhausted raises `RetryBudgetExhausted` whose `__cause__` is the last exception — `tests/test_retry.py:148`
- [x] With no hint, three consecutive retries sleep strictly increasing durations bounded by `max_delay_s` — `tests/test_retry.py:170`

### Phase 2 — Clients raise a typed retryable error

- [x] A stubbed 429 from Mistral raises `RetryableRequestError` with `status_code == 429` — `tests/test_mistral_client.py:194`
- [x] A stubbed 500 from Mistral raises it with `status_code == 500` — `tests/test_mistral_client.py:207`
- [x] A stubbed 400 from Mistral still raises plain `MistralRequestError` — `tests/test_mistral_client.py:220`
- [x] `Retry-After: 7` sets `retry_after_s == 7.0`; absent sets `None` — `tests/test_mistral_client.py:233,247`
- [x] A stubbed 429 with `RetryInfo.retryDelay == "13s"` gives `retry_after_s == 13.0` — `tests/test_google_client.py:143`
- [x] A stubbed 503 raises `RetryableRequestError` — `tests/test_google_client.py:181`
- [x] A stubbed 404/400 still raises the existing non-retryable types — `tests/test_google_client.py:194`; the 404 paths live in `check_model_available`, untouched by the diff (`google_client.py:304-317`)
- [x] `check_context_fits` on a stubbed 429 from `countTokens` raises `RetryableRequestError` — `tests/test_google_client.py:426`

### Phase 3 — `quality_cli.py` wiring + `--resume`

- [ ] `GOOGLE_REQUEST_PACING_S=6` (etc.) overrides the default; a non-numeric or negative value raises `SettingsError` naming the var — no test exists: `tests/test_settings.py` is untouched by the diff though `phase-3.md:22` projects it as modified, and none of the three new vars appears anywhere in it. `settings.py`'s 100% line coverage comes from the pre-existing `_require_numeric` callers, not from these.
- [x] `rows_for_run` on an empty/absent store returns `[]`; filters by `run_id` otherwise — `tests/test_results.py:164,171,178`
- [x] Writing a quality row missing `retries` or `resumed` raises `RowContractError` naming the field — `tests/test_row_contract.py:378`
- [x] A Mistral stub that 429s once then 200s succeeds and the row's `retries == 1` — `tests/test_quality_cli.py:1305`
- [x] The stubbed `sleep` records the Google batch's per-item pacing, with no sleep before the first item — `tests/test_quality_cli.py:1044,1053`; asserted as `>= interval` rather than `== interval` because `time.monotonic` is unstubbed while `time.sleep` is, so the pacer's own bookkeeping compounds against a clock that never advances. Harness artifact, independent of the phase-1 defect.
- [x] `--resume <run_id>` on a complete `(run_id, "mistral")` calls the stub zero times and prints the skip line — `tests/test_quality_cli.py:1349-1352`
- [x] `--resume <run_id>` on zero `(run_id, "google")` rows re-runs 20 items, every row `resumed: true` — `tests/test_quality_cli.py:1375-1378`
- [x] An always-429 Mistral exhausts the budget, prints the skip line, `main()` exits 0, Google still runs — `tests/test_quality_cli.py:1327-1331`

### Phase 4 — Live three-provider evidence + docs

- [x] The live run's full stdout/stderr is quoted, not paraphrased — `decision.md:17-27`, with the exit code and the row counts
- [x] `QUALITY_PROVIDERS`'s documented default is left as it is — `settings.py:61` unchanged; `decision.md:55-62` records the Mistral 429 as evidence rather than walking the default back
- [x] `CHANGELOG.md`'s entry sits under `## [Unreleased]` / `### Added` and does not contradict the Google entry below it — `CHANGELOG.md:12-26`
- [x] `cli.md` names `--resume` and all three env vars with their defaults — `aidd_docs/memory/cli.md:22-37`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | functional | 1 | `src/wave_local_ai_v2/retry.py:47` | `_last_call_at` advances by exactly `min_interval_s` on every `.wait()`, including the branch where no sleep happened. Any call that outlasts the interval (a retry's backoff sleep, a `retryDelay` hint of 30s, a slow `generateContent`) leaves `_last_call_at` behind the wall clock by that overrun, and the pacer then issues `overrun / interval` requests back to back with no spacing at all. A single Google 429 with a 30s hint buys ~8 unpaced requests immediately after it — the burst that caused the 429 in the first place, now fired at a provider that has just said it is rate-limited, against a batch-wide budget of 4 retries. | `self._last_call_at = max(now, self._last_call_at + self._min_interval_s)`. When a sleep happened, `now < last + interval`, so the plan's "advance by exactly `min_interval_s`, never by the clock read after sleeping" still holds; when none did, the pacer resets to the real call time instead of carrying a deficit. Add a `test_retry.py` case advancing the fake clock past the interval and asserting the next `.wait()` still sleeps a full interval. |
| 🔴 | conform | 3 | `aidd_docs/results/quality-reference.jsonl:1-80`, `aidd_docs/results/runtime-reference.jsonl:1-2` | All 82 published rows were hand-edited to keep `tests/test_reference_bundle.py:66` green under `SCHEMA_VERSION` `"8"`: `schema_version` rewritten `"7"` → `"8"` on every row, and `"retries": 0, "resumed": false` injected into the 80 quality rows. Those rows still carry `captured_at` `2026-08-27` and `commit_sha` `9bc9da88…`, a tree in which neither field nor schema `"8"` existed, and `aidd_docs/results/README.md:24-28` still states the bundle was produced at `schema_version` `"7"` by a CLI run on that date. The repo's declared discipline is the opposite — `README.md:217-220` "They were **not** back-filled. A hand-edited row is no longer the row the harness wrote", and Story 19's acceptance "never deleted and never back-filled" — and the epic these files serve is `every-published-row-explains-and-reproduces-itself`. No phase of this plan projects a change to either file. | Restore both files to their committed bytes (`git checkout main -- aidd_docs/results/*-reference.jsonl`). The bundle then honestly reads `"7"`, one version behind the code, which is the true state until it is regenerated by real runs. Retarget `test_every_row_carries_the_current_schema_version` at a declared `PUBLISHED_BUNDLE_SCHEMA_VERSION` constant naming the version the bundle was published under, with the reason the assertion is not `row_contract.SCHEMA_VERSION` (that coupling is what forces a back-fill on every bump). Record the gap in `aidd_docs/results/README.md` and file the regeneration — two runtime runs plus two quality runs under `"8"`, the Story-19 protocol — as tech debt. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/quality_cli.py:297-302` | `_provider_batch_complete` is a `>= len(SUITE)` count, so a `(run_id, provider)` batch holding 1..19 rows reads as "incomplete" and `_score_and_write` appends a further 20 — the store then carries two rows for each `(run_id, provider, item_id)` already present, with different `captured_at` and possibly different labels, and `verdict.select_quality_references` would see the item twice. `plan.md:41` asserts a partial batch is unreachable ("a mid-batch failure never got as far as `_score_and_write`"), but nothing enforces it: `_score_and_write:999-1001` appends row by row, so an interrupt or an `OSError` on row 5 of 20 leaves exactly that state, and `main()` catches `OSError` and exits 1 without cleanup. | Count distinct `item_id`s rather than rows, and split the three cases: zero rows → run; a full set → skip as today; a partial set → skip with its own line naming the count (`"<provider> skipped: run <id> is partially written (N/20 rows); re-running would duplicate them"`), so the invariant the user asked for — resume never duplicates an existing `(provider, item)` pair — is enforced rather than assumed. Per-item resume stays out of scope per `plan.md`'s Decision. |
| 🟡 | functional | 3 | `tests/test_settings.py` | Phase 3's first acceptance criterion (`MISTRAL_REQUEST_PACING_S` / `GOOGLE_REQUEST_PACING_S` / `CLOUD_RETRY_MAX_ATTEMPTS` override their defaults, and a non-numeric or below-minimum value raises `SettingsError` naming the var) has no test; `phase-3.md:22` projects the file as modified and the diff never touches it. The `minimum=0.0` / `minimum=1` choices and the `int` cast on the attempts var are unguarded against a later edit. | Add the three override cases and at least one rejection case per var, following the file's existing `_require_numeric` test pattern (`tests/test_settings.py:268` and neighbours). |
| 🟡 | rot | 3 | `src/wave_local_ai_v2/settings.py:63-65` | The constants' comment carries an unedited self-correction: "each item costs two Mistral requests? no -- one; Google costs two". A committed comment asking and answering its own question reads as a draft left in place, in the one file an operator reads to understand what the env vars do. | Rewrite as the fact: one request per Mistral item, two per Google item (`check_context_fits` + `complete_prompt`), which is why Google's interval sits closer to the 15 RPM ceiling. |
| 🟢 | rot | 2 | `src/wave_local_ai_v2/google_client.py:167-171`, `:344-348` | The 429/503 branches call `_retry_hint(response)` for the message and `_parse_retry_delay_s(response)` for the attribute, and `_retry_hint` delegates to `_parse_retry_delay_s`, so the error body is JSON-parsed twice per failure and the same value is formatted and re-derived. | Parse once into a local (`delay_s = _parse_retry_delay_s(response)`), format it inline, and pass it to both the message and `retry_after_s`. |
| 🟢 | rot | 3 | `src/wave_local_ai_v2/settings.py:72`, `quality_cli.py:562,628` | `CLOUD_RETRY_MAX_ATTEMPTS` (minimum reason: "at least one attempt must be allowed") is passed straight to `RetryBudget(max_retries=...)`, so the configured number is retries, not attempts: `=1` yields two attempts. The name comes from `plan.md`, so the value is right and the label is not. | Either rename to `CLOUD_RETRY_MAX_RETRIES`, or state in the constant's comment and `cli.md` that the value counts retries beyond the first attempt. |
| 🟢 | code | 3 | `src/wave_local_ai_v2/quality_cli.py:644-655` | `context_retries` is initialised to 0 and only assigned on the success path of `call_with_retry`, so when `check_context_fits` retries a 429 twice and then raises `ContextWindowExceededError`, the refusal row publishes `retries: 0`. The story requires the run to record how many retries each call took. | Track the count across both outcomes — a mutable counter closed over by the `is_retryable` callback, or catch and re-raise with the attempt count — so a refused pre-flight still reports the retries it cost. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 92% (24/26)                                       |
| Files checked | `src/wave_local_ai_v2/retry.py`, `mistral_client.py`, `google_client.py`, `quality_cli.py`, `settings.py`, `results.py`, `row_contract.py`, `tests/test_retry.py`, `tests/test_mistral_client.py`, `tests/test_google_client.py`, `tests/test_quality_cli.py`, `tests/test_results.py`, `tests/test_row_contract.py`, `CHANGELOG.md`, `aidd_docs/memory/cli.md`, `aidd_docs/results/quality-reference.jsonl`, `aidd_docs/results/runtime-reference.jsonl`, plan + 4 phase files + `decision.md` |
| Unchecked     | Phase 1, "a fake-clock `Pacer` sleeps the amounts the Journey states" — fix; Phase 3, "`GOOGLE_REQUEST_PACING_S=6` overrides the default, a bad value raises `SettingsError`" — fix |
| Unplanned     | `aidd_docs/results/quality-reference.jsonl` and `aidd_docs/results/runtime-reference.jsonl` back-filled to `schema_version` `"8"` (80 rows also gaining `retries`/`resumed`); no phase's architecture projection lists either file |
