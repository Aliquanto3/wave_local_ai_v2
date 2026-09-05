# Review: A second cloud provider answers suite items as a subject

- **Verdict**: approve (post-fix; the reviewed diff was changes-requested)
- **Diff**: `main...feat/google-client-subject`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_05
- **Findings**: 1 critical, 5 warning, 6 minor -- every critical and warning fixed in the review commit, every minor filed to `aidd_docs/backlog/tech-debt.md`, per `aidd_docs/GUIDELINES.md`'s severity gate

## Phases

### Phase 1 — `google_client.py`, settings, and its own tests

- [x] 1a — a well-shaped 200 body yields content, finish_reason, both token counts, model_version — `src/wave_local_ai_v2/google_client.py:226`, `tests/test_google_client.py:71`
- [x] 1b — `candidatesTokenCount` absent yields `generated_tokens == 0` — `src/wave_local_ai_v2/google_client.py:199`, `tests/test_google_client.py:142`
- [x] 1c — `content: {}` yields `content == ""` — `src/wave_local_ai_v2/google_client.py:171`, `tests/test_google_client.py:159`
- [x] 1d — blocked or unmapped `finishReason` raises `GoogleBlockedError` verbatim — `src/wave_local_ai_v2/google_client.py:187`, `tests/test_google_client.py:188`
- [x] 1e — non-string finish_reason / non-int token count raise at the boundary — `src/wave_local_ai_v2/google_client.py:183`, `tests/test_google_client.py:215`
- [x] 2a — catalog 404 raises `ModelUnavailableError` naming the id — `src/wave_local_ai_v2/google_client.py:253`, `tests/test_google_client.py:277`
- [x] 2b — probe 404 raises naming the id and **both** endpoints — `src/wave_local_ai_v2/google_client.py:280`; the vacuous test assertion was replaced with one checking both URLs (`tests/test_google_client.py:304`). The message's latent wrong-URL interpolation for a non-default `model` went to tech-debt.
- [x] 2c — a successful pair returns `GoogleModelInfo(version, input_token_limit)` — `src/wave_local_ai_v2/google_client.py:302`, `tests/test_google_client.py:254`
- [x] 3a — `countTokens` over the limit raises, no `generateContent` call — `src/wave_local_ai_v2/google_client.py:340`, `tests/test_google_client.py:343`
- [x] 4 — `google_api_key` reads `GOOGLE_API_KEY`, defaults `""`, absent from repr — `src/wave_local_ai_v2/settings.py:86`, `tests/test_settings.py:394`

### Phase 2 — Quality CLI wires Google in as a third batch

- [x] 1 — `GOOGLE_PRICE_TABLE` keyed by the literal id, import guard, Mistral untouched — `src/wave_local_ai_v2/cost.py:64`, `tests/test_cost.py:112`
- [x] 3 — `truncation_reason` override wins over the token comparison — `src/wave_local_ai_v2/scoring.py:116`, `tests/test_scoring.py:119`
- [x] 4.1 — three batches written local → mistral → google, each on disk first — `src/wave_local_ai_v2/quality_cli.py:224`, `tests/test_quality_cli.py:995`
- [x] 4.2 — unset `GOOGLE_API_KEY` writes zero google rows, exits 0 — `src/wave_local_ai_v2/quality_cli.py:360`, `tests/test_quality_cli.py:984`
- [x] 4.3 — google row carries provider/model_id/sampling/cost + `model_version`/`api_version`, `REQUIRED_FIELDS` unchanged — `src/wave_local_ai_v2/quality_cli.py:581`, `tests/test_quality_cli.py:1030`
- [ ] 4.4 — `GoogleBlockedError` caught by `main`, one stderr line, **exit 1** — not-applicable: superseded on this branch by the QUALITY_PROVIDERS scope change, now a provider skip with exit 0 (`src/wave_local_ai_v2/quality_cli.py:373`, `tests/test_quality_cli.py:1121`). The supersession is recorded in `phase-2.md:7` as of the review commit.
- [x] 4.5 — a context-fits failure scores `truncated_context` with no generate call for that item — `src/wave_local_ai_v2/quality_cli.py:533`, `tests/test_quality_cli.py:1141`

### Phase 3 — One live three-provider run, docs, memory

- [x] 1 — live run: Mistral failed, the failure is recorded and phase 2 was revised (the criterion's own escape clause) — `aidd_docs/tasks/2026_09/2026_09_05_google-cloud-subject/phase-3.md:103`
- [x] 2 — CHANGELOG names the provider and its pinned id — `CHANGELOG.md:12`
- [x] 3 — `.env.example` documents `GOOGLE_API_KEY` — `.env.example:4`
- [x] 4 — setup.md states both env vars and the skip-not-fail degradation — `docs/setup.md:272`
- [x] 5 — ecosystem.md names Google as the second cloud subject — `aidd_docs/memory/ecosystem.md:23`
- [x] 6 — codebase-map.md lists `google_client.py` — `aidd_docs/memory/codebase-map.md:22`

### Story — acceptance lines

- [x] Dated model id, never a floating alias, plus the API version on the row — `src/wave_local_ai_v2/quality_cli.py:594`, `tests/test_google_client.py:370`
- [ ] A run **refuses to start** when the dated id is absent from the live list — not-applicable: superseded, the provider's batch is skipped and the run continues (`src/wave_local_ai_v2/quality_cli.py:373`). The refusal does name the id and both endpoints. Recorded in the story's "Delivered with two deviations" section as of the review commit.
- [x] Sampling controls are required arguments, the row records what was pinned — `src/wave_local_ai_v2/google_client.py:111`, `src/wave_local_ai_v2/quality_cli.py:111`
- [ ] Finish reason mapped to cap / context / block; **a blocked generation is recorded as blocked** — not-applicable: cap and context are mapped (`src/wave_local_ai_v2/quality_cli.py:567`, `:548`); a block raises and writes no row, deferred by an explicit plan decision to the row-schema story (`aidd_docs/memory/external/google-ai-studio-api.md`). Recorded in the story's "Delivered with two deviations" section as of the review commit.
- [x] Token counts read off the response, cost from a dated table keyed by the literal id, unpriced id fails at import — `src/wave_local_ai_v2/cost.py:76`, `tests/test_cost.py:112`
- [x] Contract-valid rows under `provider == "google"`, no change to the quality required-field list — `src/wave_local_ai_v2/quality_cli.py:849`, `tests/test_quality_cli.py:1053`
- [x] Key read from the environment, absent from repr, no key reports skipped not failed — `src/wave_local_ai_v2/settings.py:86`, `tests/test_quality_cli.py:984`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | code | 2 | `tests/test_quality_cli.py:1083` | The google pre-flight test injects `mistral_client.ModelUnavailableError` (the bare name imported at line 22), not `google_client.ModelUnavailableError`. It passes only because that type is not a `GoogleRequestError` and so escapes `_try_run_cloud_provider`'s handler — so the test name and its `pytest.raises` assert an abort, the exact opposite of the branch's own skip-not-abort contract. Google's model-gone path has no coverage. | **Fixed.** `tests/test_quality_cli.py:1078` now injects `google_client.ModelUnavailableError` and asserts the skip line, zero google rows and no generate call. |
| 🟡 | code | 1 | `tests/test_google_client.py:304` | `assert "generateContent" in str(...) or "countTokens" not in str(...)` — the right disjunct is always true (the message never mentions `countTokens`), so the assertion can never fail. Criterion 2b ("names the id and both endpoints") is unverified. | **Fixed.** `tests/test_google_client.py:304` asserts both URLs. |
| 🟡 | code | 2 | `src/wave_local_ai_v2/quality_cli.py:373` | `_try_run_cloud_provider` catches only the provider's own error type, so a transport-level `requests.RequestException` (connection reset, read timeout, DNS) from either cloud client escapes to `main`'s `OSError` clause and exits 1. That falsifies the contract stated at `quality_cli.py:17-23` and `docs/setup.md:280-287`: every cloud-provider failure degrades to a skip. | **Fixed.** `src/wave_local_ai_v2/quality_cli.py:373`, covered by `tests/test_quality_cli.py::test_a_cloud_transport_failure_skips_that_provider_rather_than_aborting`. |
| 🟡 | rot | 2 | `src/wave_local_ai_v2/quality_cli.py:567` | Truncation is decided from a hardcoded `"MAX_TOKENS"` literal while the mistral path one function above reads `mistral_client.TRUNCATING_FINISH_REASONS` (`:506`). `google_client._TRUNCATING_FINISH_REASONS` exists and holds exactly that value but is private and unused outside its own module, so the provider's protocol literal is duplicated across the boundary the plan said to mirror. | **Fixed.** `src/wave_local_ai_v2/google_client.py:44` is now public, read at `quality_cli.py:567`. |
| 🟡 | rot | 2 | `aidd_docs/tasks/2026_09/2026_09_05_google-cloud-subject/phase-2.md:30,116` | The phase is `status: done` while its User Journey still says an unset `MISTRAL_API_KEY` raises `SettingsError` before any network call, and criterion 4.4 still says a `GoogleBlockedError` exits 1. Both were deliberately replaced on this branch. Only phase-3's Evidence section records the scope change; a reader of phase-2 gets the old contract as shipped fact. | **Fixed.** Superseded block at `phase-2.md:7`. |
| 🟡 | fit | - | `aidd_docs/backlog/stories/a-second-cloud-provider-answers-suite-items-as-a-subject.md:15,21` | Two acceptance lines describe behavior the branch deliberately did not ship: "a run refuses to start" (now a per-provider skip) and "a blocked generation is recorded as blocked" (a block raises and writes no row, deferred to the row-schema story). Flipping the story to `done` with that text unamended publishes two false claims about shipped behavior. | **Fixed.** "Delivered with two deviations" section added to the story alongside `status: done`. |
| 🟢 | rot | 1 | `src/wave_local_ai_v2/google_client.py:45` | `_BLOCKED_FINISH_REASONS` is never read — the raise at `:187` tests `_OK_FINISH_REASONS` only — yet `GoogleBlockedError`'s docstring (`:85`) says it "covers every `finishReason` in `_BLOCKED_FINISH_REASONS`", implying the constant drives the behavior. | **Fixed** (entangled with the warning above, which rewrote the same block): constant deleted, docstring restated. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/google_client.py:289` | The probe-404 message interpolates module-level `CATALOG_URL` instead of the `catalog_url` built from the `model` argument at `:246`, so a non-default `model` yields a message naming the wrong catalog endpoint. Latent: no call site passes one. | → tech-debt.md, 2026-09-05. |
| 🟢 | rot | 2 | `src/wave_local_ai_v2/quality_cli.py:242` | `for provider in ("mistral", "google")` restates the keys of `_CLOUD_PROVIDERS` right below it. The cloud provider set is now spelled out in four places (`_CLOUD_PROVIDERS`, this tuple, `settings.KNOWN_QUALITY_PROVIDERS`, `cost.PRICE_TABLES`), against the plan Decision that a fourth provider should "slot in later without duplicating". | → tech-debt.md, 2026-09-05. |
| 🟢 | conform | 3 | `CLAUDE.md:62-64` | A file explicitly commented "read on demand, not auto-loaded" was added inside the `<aidd_project_memory>` block, whose contents are auto-loaded and hook-refreshed; the rule two lines below ("Load `aidd_docs/memory/external/*` when the user asks") already covers it. Duplicated instruction, and a hook refresh drops the manual line. | → tech-debt.md, 2026-09-05. |
| 🟢 | code | 2 | `tests/test_quality_cli.py:1046` | `from wave_local_ai_v2.row_contract import REQUIRED_FIELDS` sits inside a test body; every other import in the file is module-level. | → tech-debt.md, 2026-09-05. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/quality_cli.py:255,284` | `_mistral_batch`/`_google_batch` return a positional 6-tuple annotated inline, unpacked over six lines at the call site (`:365`); position is the only thing binding `sampling` to `batch_fields`. | → tech-debt.md, 2026-09-05. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 90% (27/30) post-fix (87%, 26/30 as reviewed)      |
| Files checked | `src/wave_local_ai_v2/google_client.py`, `quality_cli.py`, `cost.py`, `scoring.py`, `settings.py`, `prompt_provenance.py`, `tests/test_google_client.py`, `test_quality_cli.py`, `test_cost.py`, `test_scoring.py`, `test_settings.py`, `CHANGELOG.md`, `.env.example`, `docs/setup.md`, `CLAUDE.md`, `aidd_docs/memory/*`, `aidd_docs/tasks/2026_09/2026_09_05_google-cloud-subject/*` |
| Unchecked     | Phase 1 · 2b — fixed (the vacuous assertion now checks both endpoints; the latent wrong-URL interpolation went to tech-debt); Phase 2 · 4.4 — not-applicable (superseded by the QUALITY_PROVIDERS scope change, recorded in phase-3 Evidence and CHANGELOG, but not in phase-2 itself); Story · "refuses to start" — not-applicable (same supersession); Story · "a blocked generation is recorded as blocked" — not-applicable (deferred by plan decision to the row-schema story) |
| Unplanned     | `settings.QUALITY_PROVIDERS` / `KNOWN_QUALITY_PROVIDERS` and the uniform optional-skip shape for both cloud providers (mid-phase product-owner scope change, recorded in phase-3's Evidence); `GOOGLE_REQUEST_PACING_S` (`quality_cli.py:125`, a live 429 fix); `CLAUDE.md` / `aidd_docs/memory/README.md` external-memory pointers |
