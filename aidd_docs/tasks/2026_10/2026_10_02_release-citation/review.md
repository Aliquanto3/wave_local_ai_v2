# Review: One citation names the release and is the attribution a reuser copies

- **Verdict**: changes-requested (VERDICT: CHANGES-REQUIRED)
- **Diff**: `HEAD...working tree` (LICENSE-DATA, README.md, CITATION.cff, tests/test_citation.py)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 1 warning, 4 minor

## Phases

### Phase 1: `CITATION.cff` and its version and placeholder checks

- [x] CFF 1.2.0 valid: `evidence/cff-schema-validation.txt` (one `uvx cffconvert==2.0.0 --validate` run, a network fetch of a tool into the uv cache, not a dependency; not repeated); structure held on every push by `tests/test_citation.py:131`
- [x] Names title, packaged version, repository URL, MIT + CC-BY-4.0: `CITATION.cff:17-31`, `tests/test_citation.py:131`
- [ ] Author identity the owner supplied: owner-pending (D3), held as `PLACEHOLDER-OWNER-*` at `CITATION.cff:22-25`; no real name, email or ORCID in the diff (only the pre-existing GitHub handle in the repo URL)
- [x] Repository copy names no commit and says why in a comment: `CITATION.cff:6-8`, `tests/test_citation.py:143`
- [x] Version equals packaged version, mismatch reported: `tests/test_citation.py:116`, `:122`
- [x] Tag build cannot publish with placeholders: `tests/test_citation.py:184`, `:197`; `ci.yml` `publish` needs `[test, build, verify-tag]`, `test` runs unfiltered `uv run pytest` on `v*` tags (no `-m`/`-k` in `pyproject.toml` addopts), GitHub sets `GITHUB_REF=refs/tags/...`; `evidence/release-tag-gate.txt` shows the failure

### Phase 2: The README attribution string derived from the citation

- [x] One marked string in the Licence section: `README.md:258-266`, `tests/test_citation.py:162`
- [x] Derived from CITATION.cff, an edited string fails: `tests/test_citation.py:150`, `:156`
- [ ] Reader cites any given release unaided: proven for 0.2.0 (`README.md:265`); for the existing tags v0.1.0/v0.2.0 the instruction at `README.md:268-271` points to a CITATION.cff that exists neither at those tags nor in an archive (order 4 not shipped); author owner-pending
- [x] LICENSE-DATA no longer says "will be stated"; legal-code sha256 holds: `tests/test_data_licence.py::test_the_legal_code_is_the_official_text_verbatim` passes
- [ ] GitHub "Cite this repository" rendering: owner-pending (after push)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 2 | LICENSE-DATA:114-117 | The edit drops the interim rule "name the licensor (Aliquanto3) ... link, changes". With D3 placeholders, the notice now directs a reuser to copy a string whose author is `PLACEHOLDER-OWNER-...`, so the licence notice yields no valid CC-BY attribution until the owner acts. Header line 3 still names the copyright holder, but section 4 no longer says to use it. | Minimal edit: keep the new pointer and restore one sentence: "While the author fields in CITATION.cff are placeholders, attribute as Section 3(a) requires: name the licensor (Aliquanto3) ...". Mirror one line at README.md:275-276. Legal-code hash unaffected (above the marker). |
| 🟢 minor | rot | 1 | CITATION.cff:7-8, README.md:270-272 | Present tense "has the release's commit stamped" / "The archive's copy also names the release's commit": no release archive exists until order 4. | Write "will carry (release archive, order 4)". |
| 🟢 minor | fit | 2 | README.md:268-271 | "Take that release's CITATION.cff" fails for v0.1.0/v0.2.0, which predate the file. | Add: for a release without CITATION.cff, use its tag name and tag year. |
| 🟢 minor | code | 1 | CITATION.cff:20 | `date-released` is not checked against `version`; at the next bump only `version` is forced, so the year in the string can go stale. | Optional: note it in the release procedure, or check it against the tag date on a tag build. |
| 🟢 minor | conform | - | epic Boundaries "`CITATION.cff` ... naming ... the commit" | Contradicts the story's "names no commit"; the story governs and defers the commit to order 4's archive copy. | No change here; order 4 must close the epic line. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 73% (8/11) |
| Files checked | CITATION.cff, tests/test_citation.py, README.md, LICENSE-DATA, .github/workflows/ci.yml, pyproject.toml, tests/test_data_licence.py, evidence/* |
| Unchecked     | author identity (not-applicable: owner-pending D3); GitHub rendering (not-applicable: owner-pending after push); cite any given release (fix, minor: pre-file tags) |
| Unplanned     | none |

Gates: `uv run pytest -q` => `2832 passed, 9 skipped, 2 warnings in 199.12s`, coverage 98.49%. `ruff check` / `ruff format --check` on tests/test_citation.py pass; detect-secrets on the four changed files exits 0.

## Round 2

- **Verdict**: approve (VERDICT: PASS)
- **Date**: 2026_10_03

| Round 1 finding | Status | Evidence |
| --------------- | ------ | -------- |
| 🟡 LICENSE-DATA section 4 dropped the interim licensor rule | fixed | `LICENSE-DATA:118-121` restores "name the licensor (Aliquanto3), the work, the licence with a link, this repository, and any changes made" while the author fields are placeholders; `README.md:279-282` mirrors it; above the legal-code marker, and `test_the_legal_code_is_the_official_text_verbatim` passes |
| 🟢 present-tense archive commit stamping | fixed | `CITATION.cff:7-8` "will have ... once the release job builds one"; `README.md:272-273` "will also name" |
| 🟢 no fallback for tags older than the file | fixed | `README.md:270-272`: tag name as version, year of its `CHANGELOG.md` heading (`## [0.1.0] - 2026-08-22`, `## [0.2.0] - 2026-09-22` exist) |
| 🟢 `date-released` not tied to `version` | fixed | `tests/test_citation.py:95` `release_date_mismatch`; `:157` passes on the committed files (`2026-09-22` == CHANGELOG `[0.2.0]`); `:163` reports both fixtures, the stale date (names `2026-11-02`) and the undated version (names `'0.4.0'`) |
| 🟢 epic "names the commit" | unchanged, not this story's | order 4 closes it |

| Check | Result |
| ----- | ------ |
| Real personal identifiers | none: diff scan for names, email, ORCID-shaped URLs is empty; only the existing GitHub handle `Aliquanto3` (also in `LICENSE`, `LICENSE-DATA:3`, repo URL) |
| Release gate | unchanged: `publish` needs `test`; placeholder test skips off a tag, fails on `refs/tags/` |
| `uv run pytest -q` | `2834 passed, 9 skipped, 2 warnings in 197.53s`, coverage 98.49% |
| Targeted run | legal-code hash, release-date, bumped-fixture tests pass; placeholder gate skipped off-tag (`3 passed, 1 skipped`) |
| ruff check / format | pass on `tests/test_citation.py` |

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | 1 | tests/test_citation.py:157 | A release PR must now bump the version, date its CHANGELOG heading and set `date-released` in one change, or the test goes red; this is the intended coupling, but no release procedure states it. | Optional: one line in the release procedure when order 4 touches it. |

Owner-pending, unchanged: author identity (D3), GitHub "Cite this repository" rendering after push.
