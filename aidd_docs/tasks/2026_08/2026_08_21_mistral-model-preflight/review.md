# Review: Pre-flight the Mistral model id

- **Verdict**: changes-requested
- **Diff**: `b03bd5c...a4b9588`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_21
- **Findings**: 0 critical, 1 warning, 5 minor

## Phases

### Phase 1 — Catalog check in the Mistral client

- [x] No module or test refers to `API_URL`; `CHAT_COMPLETIONS_URL` is used by `complete_prompt`, `MODELS_URL` by the catalog check — `mistral_client.py:25-26`, `:60`, `:101`; `grep -rn "API_URL" src/ tests/` returns nothing (exit 1)
- [x] The catalog request's timeout is `CATALOG_TIMEOUT_S`, strictly less than `REQUEST_TIMEOUT_S`, read from the recorded call arguments — `mistral_client.py:32` (15 vs 60), `tests/test_mistral_client.py:116-117`
- [x] A listed id with `deprecation: null` returns `None` and issues exactly one GET to `MODELS_URL` carrying the bearer header — `mistral_client.py:100-104`, `:130-133`; `tests/test_mistral_client.py:108-117` asserts `call_count == 1`, the URL and the `Authorization` header
- [x] A deprecated entry returns a string carrying the id, the timestamp and the replacement, no exception — `mistral_client.py:134-139`, `tests/test_mistral_client.py:120-130`
- [x] An absent id raises `ModelUnavailableError` naming it, still caught by `except MistralRequestError` — `mistral_client.py:39-44`, `:123-127`, `tests/test_mistral_client.py:132-148`
- [x] A 401 raises `MistralRequestError` carrying the status and never parses the error body as a catalog — `mistral_client.py:106-110`, `tests/test_mistral_client.py:150-162` asserts `json.assert_not_called()`
- [x] A 200 whose body has no `data`, or a non-list `data`, raises `MistralRequestError`, no bare `KeyError`/`TypeError` — `mistral_client.py:112-117`, `tests/test_mistral_client.py:164-170`
- [ ] Every assertion about the outgoing request reads the recorded call arguments; no test asserts a value against the module constant that produced it — first clause met (`tests/test_mistral_client.py:113-117` reads `get.call_args`), second clause unmet: `:114` compares the recorded URL to `MODELS_URL`, the same symbol `mistral_client.py:101` passes to `requests.get`, and no literal models-endpoint URL exists under `tests/`
- [x] One live call returns `None` for `MODEL` and raises for a wrong id, outcome and date recorded — `phase-1.md:107` records the 2026-08-21 run (`None` for `mistral-small-2603`, `ModelUnavailableError` for `mistral-small-9999`, plus the deprecation branch on `mistral-medium-2505`)

### Phase 2 — Pre-flight before the local suite

- [x] `ModelUnavailableError` propagates from `_run` with `running_server` and `requests.post` never called — `quality_cli.py:91`, `tests/test_quality_cli.py:300-308`
- [x] An empty key still raises `SettingsError` with the catalog never called — `quality_cli.py:89-90` ordered before `:91`, `tests/test_quality_cli.py:311-321`
- [x] The check runs exactly once before the first `running_server` call, rows unchanged — `tests/test_quality_cli.py:324-337` asserts `order == ["check", "server"]`; the pre-existing row tests are untouched and green
- [x] A notice reaches stderr, the run completes, all `2 x 10` rows written — `quality_cli.py:92-95`, `tests/test_quality_cli.py:340-352`; stdout hygiene asserted only negatively (see the `code` finding on `:351`)
- [x] `main()` turns it into exit code 1 with the message on stderr, no traceback — `quality_cli.py:66-78` (the subclass is caught by the existing `MistralRequestError` arm), `tests/test_quality_cli.py:355-365`
- [x] Every test in `tests/test_quality_cli.py` passes with no network — `tests/test_quality_cli.py:59-64` patches the check in the fixture; `uv run pytest -q` => `78 passed in 3.23s`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | functional | 1 | `tests/test_mistral_client.py:114` | The phase's own criterion forbids asserting a recorded call argument against the module constant that produced it, and the URL assertion does exactly that: `args[0] == MODELS_URL` holds for any value of `MODELS_URL`. No literal models-endpoint URL appears under `tests/`, so pointing the constant at the completions endpoint keeps all 78 tests green. The endpoint of a pre-flight whose only job is one correct GET is then verified solely by the one-off live call recorded in `phase-1.md:107`. | Assert the endpoint as the literal recorded in the plan's Resources table (`assert args[0] == "https://api.mistral.ai/v1/models"`), still read from `get.call_args`. `tests/test_mistral_client.py:31` carries the same pre-existing hole for `CHAT_COMPLETIONS_URL` and can be closed in the same edit. |
| 🟢 | fit | 2 | `src/wave_local_ai_v2/quality_cli.py:91`, `src/wave_local_ai_v2/quality_cli.py:116-119` | The ordering rationale at `:90` ("an unset key needs no network round trip to reject") is applied to one of the two offline preconditions only. `_run_local_suite` raises `SettingsError("model file not found: ...")` off a `Path.exists()` call, so a run with no GGUF on disk now pays a live catalog GET before failing for a reason that needed no network at all. | Hoist the `model_path.exists()` check out of `_run_local_suite` (or into a small `_require_local_model(settings)`) and call it in `_run` between the key check and the catalog call, keeping the three preconditions ordered cheapest-first. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/mistral_client.py:112-113` | The shape guard covers a missing or non-list `data` but not a non-dict body: a 200 whose JSON is an array or `null` makes `response_json.get` raise `AttributeError`, which is outside `quality_cli.main`'s `except` tuple and surfaces as a traceback. The sibling `complete_prompt` has no such hole, since `:82-86` catches `TypeError` around its subscripts. | Guard the container too: `entries = response_json.get("data") if isinstance(response_json, dict) else None`, leaving the existing `isinstance(entries, list)` raise to report it. |
| 🟢 | rot | 1 | `tests/test_mistral_client.py:140-148` | `test_model_unavailable_is_caught_by_the_existing_handler` walks the same absent-id path as `:132-138` with a weaker assertion (`MistralRequestError` rather than the subclass), so it cannot fail unless that test fails first. The property it names is the class statement at `mistral_client.py:39`. Commit `4856f9c` in this same range deleted a test on exactly this ground. | Replace the mocked call with the direct statement of the contract, `assert issubclass(ModelUnavailableError, MistralRequestError)`, keeping the comment that explains why it matters to `quality_cli.main`. |
| 🟢 | code | 2 | `tests/test_quality_cli.py:351` | The criterion is "stdout still carries only the two accuracy lines", but the test asserts only that the notice is absent from stdout, and no test in the file asserts stdout's positive content. A new `print()` added to `_run` would pass unnoticed, which is the failure mode the criterion exists to catch (the operator parses stdout). | Assert the whole stream in `test_run_surfaces_a_deprecation_notice_and_still_writes_every_row`: `captured.out.splitlines()` has length 2 and both lines start with `model=`. |
| 🟢 | fit | 1 | `src/wave_local_ai_v2/mistral_client.py:119-127` | The check matches `entry["id"]` only, while the plan's Resources table records that entries also carry `aliases`, and that `mistral-small-latest` is currently an alias of the pinned id. An alias passed as `model=` would raise "is not on the live catalog" for an id the completions endpoint accepts. The only caller passes the dated default, so nothing breaks today; the id-only contract is simply unstated, and the message at `:126` tells the operator to "update `mistral_client.MODEL`" even when the caller supplied its own id. | Add one docstring line stating that aliases are deliberately not matched, since a rotating alias defeats the reproducibility rule the dated id exists for (module docstring, `:9-16`). |

## Verification

| Metric        | Value                                                                        |
| ------------- | ---------------------------------------------------------------------------- |
| Verified      | 93% (14/15)                                                                  |
| Files checked | `src/wave_local_ai_v2/mistral_client.py`, `src/wave_local_ai_v2/quality_cli.py`, `tests/test_mistral_client.py`, `tests/test_quality_cli.py`, `tests/test_cli.py`, `plan.md`, `phase-1.md`, `phase-2.md` |
| Unchecked     | Phase 1 — "no test asserts a value against the module constant that produced it" — fix |
| Unplanned     | `tests/test_cli.py:19-32`, `:113` and the deletion of `test_run_builds_no_real_energy_tracker` (`4856f9c`) trace to the previous review's two warnings, not to this plan; `aidd_docs/tasks/2026_08/2026_08_21_quality-sampling-reproducibility/review.md` added by `efce5e7` is that review's own record; `plan.md`'s status flip to `implemented` and the `phase-1.md` / `phase-2.md` evidence lines trace to no criterion |
