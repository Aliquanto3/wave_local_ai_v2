# Review: Row contract and suite gate

- **Verdict**: approve
- **Diff**: `main (bcc6d72)...working tree` (12 modified, 4 untracked source/test files)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 1 critical, 2 warning, 5 minor — the 🔴 and both 🟡 fixed in this branch (`aidd_docs/GUIDELINES.md:19`), the 5 🟢 routed to `aidd_docs/backlog/tech-debt.md`. Gate after the fixes: `ruff check` / `ruff format --check` / `mypy src/ scripts/` clean, 132 passed, coverage 97.26%.

## Phases

### Phase 1 — Row contract + writer gate + schema_version

- [x] `validate_row` exists, is importable, `REQUIRED_FIELDS` covers exactly what the two writers produce plus `schema_version` — `src/wave_local_ai_v2/row_contract.py:18,86`; runtime set matches the `__init__.py:223-239` assembly key-for-key, quality base set matches `quality_cli.py:213-232`
- [x] Complete row writes and reads back; incomplete raises naming the missing field and appends nothing; `read_rows(path, schema_version=)` filters — `src/wave_local_ai_v2/results.py:34,41,47,57`; `tests/test_results.py:38,70,82,96`
- [x] Both CLIs' rows carry `schema_version` and satisfy `validate_row` for their kind — `src/wave_local_ai_v2/__init__.py:224,240`, `src/wave_local_ai_v2/quality_cli.py:214,245`; the write itself is the gate, asserted at `tests/test_cli.py:133` and `tests/test_quality_cli.py:86`
- [x] `uv run pytest` passes with no regressions — 130 passed in 5.57s, coverage 97.23%

### Phase 2 — Suite caps/tags/hash + suite_gate

- [x] Every item exposes `language`/`provenance`/`contamination_risk`; `SUITE_ID`, `SUITE_VERSION`, `MAX_OUTPUT_TOKENS`, `STOP_SEQUENCES`, `CONTEXT_LENGTH` are module constants; `prompt_set_hash` is deterministic and prompt-sensitive — `src/wave_local_ai_v2/classification_suite.py:33-47,52-58,66-77,132-147`; `tests/test_classification_suite.py:37-62`
- [x] `gate_suite` raises on a missing/inconsistent provenance, returns `indicative=True` with a named reason under 20 items or under 25% share, flags a per-language cell under 10 items independently, returns `indicative=False` for a compliant suite — `src/wave_local_ai_v2/suite_gate.py:39-84`; `tests/test_suite_gate.py:28-89`
- [x] `gate_suite(CLASSIFICATION_TASK_SUITE)` returns `indicative=True` and never raises, reasons naming both the count and the FR/DE share — `tests/test_suite_gate.py:92-99`
- [x] `uv run pytest tests/test_classification_suite.py tests/test_suite_gate.py` passes — included in the 130-pass run

### Phase 3 — quality_cli writes suite fields, contract extended

- [x] `REQUIRED_FIELDS["quality"]` includes the new field names and a row missing any one is refused — `src/wave_local_ai_v2/row_contract.py:66-76` (eleven names; the phase-3 criterion says "ten" while its own task lists eleven — the code follows the task)
- [x] A row `quality_cli.py` writes carries every new field with the value the suite/gate actually declared for it — fixed: `complete_prompt` now takes a required `max_tokens` and sends Mistral's `max_tokens` (`mistral_client.py:47-83`), fed the suite's cap from `_run_cloud_suite` (`quality_cli.py:185-201`); the row assertion keys by `(provider, item_id)` and covers all 20 rows (`tests/test_quality_cli.py:95-131`); the `SuiteGateError` abort was already proven (`tests/test_quality_cli.py:127-141`)
- [x] `uv run pytest tests/test_row_contract.py tests/test_cli.py tests/test_quality_cli.py` passes — included in the 130-pass run

### Phase 4 — Docs: README tag example, codebase map, CHANGELOG

- [x] No `<version>` placeholder remains; all three occurrences read `v0.1.0` — `README.md:118,126,132`; `grep -n "<version>" README.md` returns nothing, and `v0.1.0` exists on `origin` at `bcc6d72`
- [x] `row_contract.py` and `suite_gate.py` are named in the codebase map — `aidd_docs/memory/codebase-map.md:22`
- [x] `CHANGELOG.md`'s `[Unreleased]` describes the row contract, the writer gate, and the suite's caps/tags/gate — `CHANGELOG.md:10-19`

### Story — Rows carry a schema version and a writer gate refuses an incomplete row

- [x] Methodology 19: every runtime and quality row carries `schema_version`; a reader selects rows by that version — `__init__.py:224`, `quality_cli.py:214`, `results.py:47-57`
- [x] Methodology 19: the store is never rotated; versions coexist in one file and are separated at read time — `results.py:53-57`; `tests/test_results.py:96-103` writes `"1"` and `"2"` to one path and separates them
- [x] A row missing a required field cannot be written: the writer raises, names the missing fields, appends nothing — `results.py:41`, `row_contract.py:92-97`; `tests/test_results.py:70-92` asserts both the absent-file and the pre-existing-file cases
- [x] The contract is declared in one place per kind and is the single list every later story extends; adding a field fails the tests of any writer that does not supply it — `row_contract.py:18-79`; phase 3 extended that same dict rather than adding a second one
- [x] A genuinely unavailable value is written as an explicit null, which the gate accepts; an absent key is not — `row_contract.py:92`; `tests/test_row_contract.py:75-78`

### Story — A suite declares its caps, tags and language mix, and a short suite publishes indicative

- [x] Methodology 3: the suite declares max output tokens, stop sequences and context length; every row records those three, and two models compared on one item record identical values — fixed: both halves now run under the suite's cap (`quality_cli.py:167` local `n_predict`, `quality_cli.py:199` cloud `max_tokens`), and `tests/test_quality_cli.py:124-131` asserts the local and mistral rows for one item carry identical `max_output_tokens`/`stop_sequences`/`context_length`; `tests/test_mistral_client.py:34-45,71-90` prove the cap reaches the request body
- [x] Methodology 2: suite id, suite version and a SHA-256 prompt-set hash; every row records all three; editing a prompt changes the hash — `classification_suite.py:36-37,132-147`; `quality_cli.py:236-238`; `tests/test_classification_suite.py:53-62`
- [x] Methodology 4: every item carries a language tag among `en`, `fr`, `de`; the gate computes item count and each language's share — fixed: `_check_item_declaration` (`suite_gate.py:88-101`) refuses an item whose `language` is missing or outside `LANGUAGES` before any count is taken; `tests/test_suite_gate.py:58-76` covers both, including the 40-item + 10-untagged case that previously returned `indicative=False` and now raises
- [x] Methodology 4: a suite below 20 items or below a 25% EN/FR/DE share is marked indicative with the reason named, every row carries the mark, and today's 10-item EN-only suite is marked indicative rather than passing — `suite_gate.py:60-71`; `quality_cli.py:242-243`; `tests/test_suite_gate.py:92-99`, `tests/test_quality_cli.py:107-109`
- [x] Methodology 4: the gate reports n per language and marks any cell under 10 items indicative under the same rule — `suite_gate.py:51,73-75`; `tests/test_suite_gate.py:72-82`
- [x] Methodology 5: every item declares provenance among the three values; a `public` item is marked contamination-risk on every row; the gate refuses a missing or self-inconsistent declaration and verifies nothing about its truth — `classification_suite.py:52-58`, `suite_gate.py:87-106`, `quality_cli.py:239-241`; `tests/test_suite_gate.py:51-69`
- [x] The gate validates fields, not a suite shape — `suite_gate.py:39` takes `Iterable[Mapping[str, object]]`; `tests/test_suite_gate.py:7-13` exercises it with plain dicts, never `_item()`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | functional | 3 | `src/wave_local_ai_v2/quality_cli.py:233`, `src/wave_local_ai_v2/mistral_client.py:59-72` | Every mistral row publishes `max_output_tokens: 32`, but `complete_prompt` sends only `model`, `messages`, `temperature`, `random_seed` — no output cap. The local half is truncated at `n_predict: 32` (`quality_cli.py:161`); the cloud half generates to Mistral's own default. Half the published rows carry a generation-cap claim they did not run under, and the head-to-head is not the like-for-like comparison Methodology 3 exists to guarantee. The plan's scope-out at `phase-3.md:65` reasons about `STOP_SEQUENCES` only and does not cover this. | **Fixed.** `complete_prompt` gained a required `max_tokens: int` keyword sent as Mistral's `max_tokens` (`mistral_client.py:47-83`), fed `classification_suite.MAX_OUTPUT_TOKENS` from `_run_cloud_suite` (`quality_cli.py:199`) — the same treatment `temperature`/`random_seed` already get. Asserted in the request body at `tests/test_mistral_client.py:45,90` and on the live call at `tests/test_quality_cli.py:336-343`. `STOP_SEQUENCES` is empty today, so no `stop` field is sent to either provider and the phase-3 follow-up note stands (🟢 row below). |
| 🟡 | functional | 2 | `src/wave_local_ai_v2/suite_gate.py:47-58` | `gate_suite` enforces the `provenance`/`contamination_risk` declaration but not the `language` one. An item whose `language` is absent or out of `LANGUAGES` still increments `item_count` while entering no bucket, so `language_shares` silently sums to less than 1: a 40-item suite with 10 untagged items and 14/13/13 EN/FR/DE returns `indicative=False`, hiding a quarter of the suite from the mix check the gate exists to make falsifiable. | **Fixed.** `_check_provenance_consistency` is now `_check_item_declaration` (`suite_gate.py:88`) and refuses a missing or out-of-`LANGUAGES` tag before any count is taken. `tests/test_suite_gate.py:58-76` covers the missing-key case and the 40-item + 10-untagged case named in this finding, which now raises instead of returning `indicative=False`. |
| 🟡 | code | 3 | `tests/test_quality_cli.py:95` | `rows_by_item = {row["item_id"]: row for row in read_rows(...)}` keys 20 rows (2 models × 10 items) by `item_id`, so the 10 local rows are overwritten by their mistral twins and only the cloud half is ever asserted. The inner `if r["item_id"] == item["item_id"]` filter over an already-`item_id`-keyed dict is a no-op that hides the collapse. The test reads as full-coverage and is not. | **Fixed.** Rows are keyed by `(provider, item_id)` with `assert len(rows_by_key) == 2 * len(CLASSIFICATION_TASK_SUITE)` guarding a future collapse (`tests/test_quality_cli.py:95-116`), and a second loop asserts the local and mistral rows for one item carry identical caps (`:124-131`), which is Methodology 3's "two models record identical values" stated as its own check. |
| 🟢 | rot | 2 | `src/wave_local_ai_v2/classification_suite.py:47` | `CONTEXT_LENGTH = server.CONTEXT_SIZE` binds the suite's declared context to the local server's launch flag, but the value is published on cloud rows too and the cloud provider never passes through `server.py`. Retuning the local launcher would silently rewrite a field every mistral row publishes as the suite's own declaration. | Declare the value on the suite and have `server.py` read it, or keep the literal with the cross-reference comment `phase-2.md:74` allowed. |
| 🟢 | rot | 3 | `tests/test_row_contract.py:32-57`, `tests/test_results.py:6-31` | The 24-key `COMPLETE_QUALITY_ROW` literal is duplicated across two test files, once bound to `SCHEMA_VERSION` and once hardcoded to `"1"`. Every future contract extension means editing both, and only one of the two will fail if a writer forgets the field. | Move the fixture to `tests/conftest.py` and import it in both. |
| 🟢 | code | 3 | `src/wave_local_ai_v2/quality_cli.py:240` | `phase-3.md:65` asked for a follow-up note that `STOP_SEQUENCES` is declared and published on every row while sent to neither provider. No such note exists in the code or the backlog; the field is truthful only because the list is empty today. | This row is the note, now also in `tech-debt.md`. The cap is threaded through both HTTP paths by the 🔴 fix; thread the stop sequences the same way the first time a suite declares a non-empty list. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/suite_gate.py:108,112` | The invalid-provenance-value and missing-`contamination_risk` branches are the only uncovered lines in the two new modules (`pytest --cov` after the fixes: `suite_gate.py 49 2 96% 107, 112`), though `phase-2.md:85` specifies both as distinct outcomes ("missing key vs. mismatched value"). | Two cases in `tests/test_suite_gate.py`: an item with `provenance="scraped"`, and one with `provenance` present but no `contamination_risk` key. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/suite_gate.py:114` | `item["contamination_risk"] != expected_risk` compares by value, so on the arbitrary mappings the gate is documented to accept, `0` passes as `False` and `1` as `True`. The consistency check is looser than the `bool` the contract publishes. | Require `isinstance(item["contamination_risk"], bool)` before comparing, raising `SuiteGateError` naming the item otherwise. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (26/26) after the fixes; 88% (23/26) as first reviewed |
| Files checked | `src/wave_local_ai_v2/row_contract.py`, `suite_gate.py`, `results.py`, `classification_suite.py`, `quality_cli.py`, `__init__.py`, `mistral_client.py`, `hardware.py`, `server.py`, `tests/test_row_contract.py`, `test_suite_gate.py`, `test_results.py`, `test_classification_suite.py`, `test_quality_cli.py`, `test_cli.py`, `test_mistral_client.py`, `README.md`, `CHANGELOG.md`, `aidd_docs/memory/codebase-map.md` |
| Unchecked     | Phase 3 criterion 2 (row values match what the run actually used) — fixed; Story "caps/tags/language mix" Methodology 3 (two models record identical values they both ran under) — fixed; Story "caps/tags/language mix" Methodology 4 (language tag among en/fr/de enforced by the gate) — fixed |
| Unplanned     | `tests/test_cli.py:74-84` — the `capture_fiche` stub gained `gpu_driver_version` and `cuda_ceiling`, named in no phase task but required by `REQUIRED_FIELDS["runtime"]`; traces to phase 1 criterion 3 and is correct. `src/wave_local_ai_v2/mistral_client.py` and `tests/test_mistral_client.py` are outside both stories' file lists but are where the 🔴 fix had to land: the cloud request body is the only place the suite's declared cap can actually be applied |
