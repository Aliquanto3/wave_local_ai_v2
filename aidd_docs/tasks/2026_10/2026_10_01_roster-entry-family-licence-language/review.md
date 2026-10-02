# Review: Every roster entry states its family, its licence and its language claim

## Round 1

VERDICT: PASS

### Gates

- `uv run pytest -q` => `1458 passed, 2 warnings in 51.39s`, coverage 97.36% (floor 95%).
- `uv run ruff check .` => all checks passed; `uv run ruff format --check .` => 545 files already formatted; `uv run mypy src/ scripts/` => no issues in 53 source files.
- detect-secrets on `models.json`, `evidence/*`, `roster.py`, `tests/test_roster.py` => exit 0 once the updated baseline is staged (in a scratch index). Against the real index it exits 1 only with "baseline is unstaged", a working-tree artifact.
- Scratch export of the committed bundle: `roster.csv` carries `licence_*` and `language_claim_*` on all four rows; the flagship lists `language_claim_statement` in `fields_not_carried`.

### Acceptance, condition by condition

1. `KNOWN_FAMILIES` grows additively (adds `ibm`, `liquid`, `microsoft`; vendor lineage per Q11; no `glm`/`deepseek`) => `roster.py:79-94`; `test_an_entry_declaring_a_candidate_vendor_family_loads_and_resolves` (6 families). Met.
2. Unknown family refused at load, naming entry and value => `roster.py:303-310`; `test_load_roster_refuses_an_entry_declaring_an_unknown_family` (`acme`, `gemma`, `""`, `None`, list). The flagship still resolves through `MODEL_FAMILIES`, and `REQUIRED_FIELDS` is unchanged. Met, with the version-line note below.
3. Licence block plus shape validation (non-bool flag, unparseable date, empty id, and also empty URL, non-object block, missing key) => `roster.py:373-394`; `test_load_roster_refuses_a_malformed_licence_field_naming_it` and `..._block_that_is_not_an_object_or_lacks_a_field`. Met.
4. Language claim (subset of en/fr/de, source URL, read date) => `roster.py:397-426`; malformed-claim tests. "Never a score" holds structurally: only the roster file writes the claim, and no code path writes `models.json`. Met.
5. All four shipped entries carry both blocks, sourced at the pinned revision (flagship at `main`) => `models.json`; `test_every_shipped_entry_carries_a_licence_and_a_language_claim` also asserts each URL is `blob/<revision>/`. Met.
6. `roster_version` 2 => 3. No results row or fiche is touched (git status). `tests/test_reference_bundle.py` is unchanged and passes. All 82 published rows still state `roster_version: 1`. Met.

### Points judged

- **Empty `languages`.** The acceptance asks for "which of EN, FR and DE the vendor states", which is a subset, and the empty subset is legitimate. No "not claimed" state is required. For a reader this is unambiguous enough: the dictionary unit says "[] when the card names none of the three", the verbatim `statement` ("100+ languages") travels beside it, and the flagship's missing statement is named in `fields_not_carried`. `[]` never reads as a negative claim under that definition. Choosing not to infer EN/FR/DE from "100+ languages" is the correct reading of "claim, not measurement".
- **Edited "unchanged" test.** At HEAD, the only shipped-version assertion (`roster_version == 2`) lives inside `test_the_shipped_moe_entry_still_loads_with_no_family_of_its_own`. Acceptance bullet 6 requires that assertion to follow the file, so the 2 => 3 edit cannot be avoided: the acceptance contradicts itself, and the family half of the test is untouched. Replacing `test_family_of_refuses_an_entry_declaring_an_unknown_family` is also necessary, because load now refuses before `family_of` can be reached. `family_of`'s own guard stays covered via `dataclasses.replace` in `test_family_of_still_refuses_a_constructed_entry_with_an_unknown_family`.
- **Bundle and version citations.** `roster_file_version` now asserts against the file's value instead of a literal, and `results/README.md` reports the gap as rows at `1` and the file at `3`. `bundle_export.py` lies outside the story's "Code it changes" list, but the change is needed because the exporter refuses undescribed fields. It also matches the epic's "the published table carries them".
- **Evidence.** The evidence folder holds 108 KB: four card copies plus four LICENSE files. The flagship card is cut to lines 1-354, as documented, to keep an API-key placeholder out. `sources.md` records the URL and revision for each entry, plus the flagship's `main` resolved to `a483e9e6...` (matching `docs/setup.md`) and the upstream LICENSE sha.

### Non-blocking

1. Acceptance inconsistency (bullet 2 "unchanged" vs bullet 6 "assertion follows the file"): note for the backlog, no code change.
2. `aidd_docs/results/README.md:638` still says "The model set is `roster_version` 2". It should read 3, or drop the number.
3. The flagship's resolved sha `a483e9e6...` is recorded only in `evidence/sources.md`, not in `models.json`. This is acceptable because the acceptance makes the read date the stand-in.
4. `date.fromisoformat` (Python 3.12) also accepts ISO basic and week forms (`20261002`, `2026-W40-5`). They are still ISO 8601, so harmless.
