# Review: The Zenodo deposit is a written, optional procedure, proven once

- **Verdict**: approve (night-run brief: `VERDICT: PASS`)
- **Diff**: uncommitted working tree vs `HEAD` (`README.md`, `docs/zenodo-deposit.md`, `tests/test_zenodo_deposit_procedure.py`, this task folder; `run-log.md` excluded)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_04
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — The procedure, its README link and its guard test

- [x] What to upload: the release asset unchanged, with a SHA-256 check against `Record the archive digest` — `docs/zenodo-deposit.md:41-58`, matches `.github/workflows/ci.yml:287-292`
- [x] Metadata and its `CITATION.cff` source per field; labels no doc shows are marked *confirm on the walk* — `docs/zenodo-deposit.md:67-81`; spot-checked over HTTPS (create-new-upload, licenses, developers API, enable-repository, manage-records): every unmarked label and claim matched
- [x] Licence CC-BY 4.0 with resource type Dataset; archive ships no code (`scripts/assemble_release_archive.py:507-535`: exports, bundle JSON/JSONL/NOTICE, LICENSE, LICENSE-DATA, stamped CITATION.cff, README; `src`/`scripts` are clone-only, `:80-89`) — `docs/zenodo-deposit.md:70,75`
- [x] Mixed terms in the description: LICENSE-DATA 1.1 grant, 1.2/1.3 not-granted parts, drawn-item terms, MIT note — `docs/zenodo-deposit.md:98-122`
- [x] DOI recorded back as a CFF `identifiers` entry plus a README line outside the markers — `docs/zenodo-deposit.md:126-180`; `identifiers` with `type`/`value`/`description` is valid CFF 1.2.0 (schema.json read); simulated edit in a scratch copy: `tests/test_citation.py` + guard test => `19 passed, 1 skipped`; `stamp_citation` output parses and `clone_only_references` => `[]`
- [x] Order-2 version check still holds after the edit — same simulation (`test_the_citation_version_is_the_packaged_version`, release-date test pass)
- [x] No CI token, no automated deposit, integration disabled, and why; no release blocked — `docs/zenodo-deposit.md:17-39`; `test_no_workflow_names_zenodo`, `test_a_workflow_naming_a_zenodo_token_is_reported`
- [x] Sandbox DOI never written — `test_the_citation_and_readme_hold_no_sandbox_doi`; simulated `10.5072/` value in CITATION.cff => that test FAILED as intended
- [x] First real deposit may need one correction — `docs/zenodo-deposit.md:208-210`
- [x] Deposit log row (first release not cut, skipped unless a venue asks) — `docs/zenodo-deposit.md:222-227`
- [x] README links the procedure — `README.md:245-248,299-301`; `test_the_readme_points_at_the_procedure`
- [ ] Sandbox walk performed and corrections folded in — pending owner (operator, owner answer Q40 (a)); tagged not-applicable for this round

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | 1 | `docs/zenodo-deposit.md:73` | Creators row maps `family-names`/`given-names` and `name`, not `alias`, though the CITATION.cff header leaves a pseudonym open and `tests/test_citation.py` accepts `alias` | Add the `alias` case (Person with the pseudonym as the name, or Organization) |
| 🟢 minor | rot | 1 | `docs/zenodo-deposit.md:112-114` | "Today: No item is drawn from a public benchmark." is presented as LICENSE-DATA section 2's statement but is not its wording ("The bundle holds no item drawn from a public benchmark today.") | Quote section 2 verbatim |
| 🟢 minor | code | 1 | `docs/zenodo-deposit.md:155-156` | Replacing the README paragraph's first sentence yields "Releases deposited on Zenodo: Once one is deposited, its DOI is recorded..." (reproduced in a scratch copy) | Replace the whole paragraph with the heading line, or reword it |
| 🟢 minor | fit | 1 | `docs/zenodo-deposit.md:75` | Single CC-BY 4.0 licence; Zenodo documents declaring several licences for mixed uploads, and the archive also holds README/NOTICE/LICENSE files LICENSE-DATA 1.1 does not license | Keep, but note the tradeoff and confirm on the walk whether to add a second licence entry |
| 🟢 minor | fit | 1 | `docs/zenodo-deposit.md:78` | `isIdenticalTo` points at the GitHub Release page, which is not the identical object | Use the asset URL `<repository-code>/releases/download/v<version>/wave-local-ai-v2-<version>.zip` |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 92% (11/12) |
| Files checked | README.md, docs/zenodo-deposit.md, tests/test_zenodo_deposit_procedure.py, plan.md, phase-1.md, evidence/sources.md, evidence/checks.txt, CITATION.cff, LICENSE-DATA, scripts/assemble_release_archive.py, .github/workflows/ci.yml, tests/test_citation.py |
| Unchecked     | Sandbox walk and its corrections — not-applicable (owner-pending; story stays `ready`) |
| Unplanned     | Guard test added although the story says "None automated": cheap, no production code, justified in plan.md Decisions; `uv run pytest -q` => `2895 passed, 20 skipped, 2 warnings in 204.86s`, coverage 98.49% |
