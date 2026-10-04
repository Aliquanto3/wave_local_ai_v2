# Review: the ~2B class spans two families (round 1, 2026-10-04)

VERDICT: PASS

Scope: committed stage A (`5fc6901`: roster entries, candidate records, ~2B declaration, `docs/setup.md` 3.4, tests, `.secrets.baseline`) and uncommitted stage B (82 rows, 2 fiches, README rows section, evidence).

Blocking findings: none.

Acceptance:
- Shortlist, gate order, Q8_0, stop rule: proven. Candidate declarations (`evidence/candidates/*.json`) match the story's four pins. Gate order is smallest download first: LFM2.5 (1,246,253,888 B), then the Granite MoE (1,422,239,776 B). Both pass records are in `aidd_docs/roster/candidate-records.jsonl`, and both gate logs exit 0. D: free space fell by exactly each file's size, so both were real downloads. Trying the MoE after LFM2.5 passed is required by the story, not optional: the stop rule needs the MoE question answered, and the MoE acceptance line says a MoE the spike found "is taken through the gate like any candidate". Granite 4.0 H 1B and Granite 4.0 1B are dense, so skipping them is correct under Q127 (a).
- Entry from the pass record: proven. A scripted comparison found every `entry` field equal to the roster entry; the roster adds only `requirements` and `entry_id`. The local GGUF headers show `granitemoe`, `expert_count` 32, `expert_used_count` 8 and 1,334,628,352 params; `lfm2` with 1,170,340,608 params. `roster_version` moved 7 -> 8. `docs/setup.md` 3.4 has `hf download ... --revision <sha>` plus `Get-FileHash ... .ToLower()`, and its shas, sizes and "8 active" are correct. On the hub, bartowski's card shows `apache-2.0` and `b4381`. Test: `test_each_second_family_entry_matches_docs_setup_and_its_gguf_kind`.
- LFM `client_commercial_use: false` with its basis: proven (roster entry; README "Licences" paragraph).
- Suites to completion, required row fields, append-only: proven.
  - Rows: 4 runs, 20/21/20/21 rows, `failure_counts` all 0. Every row has `tree_dirty: false`, `commit_sha` `5fc6901d...`, `roster_version` 8, family `liquid`/`ibm`, `~2B`, `disabled`.
  - Launch: fiche flags equal the declared flags (`-ngl 99 -t 8`, no `--n-cpu-moe`).
  - Append-only: `git diff -U0` shows one hunk `@@ -121,0 +122,82 @@` per store and 0 removed lines. The bundle rows equal `evidence/quality.jsonl`.
  - Checks: `merge-bundle --check` exits 0 (6 runtime, 203 quality). `validate` with `FICHE_REGISTRY_DIR` unset reports `checked 203 row(s)` on the reference and laptop stores and 6 on runtime, each exit 0.
- MoE question answered: proven. The declaration has `moe_sought: true` and `moe_entry: granite-3.1-1b-a400m-instruct-q8`. Test: `test_the_two_billion_class_spans_three_families_and_holds_its_moe`.
- Declaration states two families: proven (ibm, liquid, qwen).
- Composition check passes for ~2B and the README block is regenerated: proven. The live output equals both the README block and `evidence/composition-check.txt`. The command exits 1 only for `~4B` and `~8B-and-up`, as expected.
- Q126 deferred/refused handling: n/a, because no candidate was refused or deferred.
- Spike resolution lines: proven in the README. `granitemoe` and `lfm2` loaded (pass records); `granitehybrid` closed at ~0.5B; `granite` "not reached: class stopped at ...".
- EN/FR/DE claim versus rows: proven. I checked a sample against `subject_output`. All 42 translations are in the target language, and Granite `fr-de-07` contains "signed-document". The misroutes match the README (LFM2.5 3; Granite 8, of which 4 went to `account`). Scores and per-language figures match the rows.

Other checks:
- `.secrets.baseline` additions: SHA-1 of the six public revision and GGUF shas only (verified by recomputing them).
- detect-secrets over the stage B files: exit 0.
- Tests: `timeout 900 uv run pytest -q` => `3059 passed, 20 skipped, 2 warnings in 215.45s`, coverage 98.51%.

Non-blocking:
- The untracked fiches `aidd_docs/results/fiches/53fa3307...json` and `add6a317...json` must be committed together with the rows, or the validator fails on a clean clone.
- Both entries copy Qwen's sampler (0.6/20/1.5) rather than the publishers' recommended settings. The suites are unaffected, but the playground path would use it. This is the same precedent as ~0.5B.
- `requirements.*.ram_gb` (1.25, 1.42) is the weights only. It is labelled a lower bound, which is honest, but a fit check on it is optimistic.
- No `Qwen3-1.7B` rows exist at these suite versions, so the side-by-side rests on superseded tables. The README states this; re-running `qwen3-1.7b-q8` would close the story's "So that".

Reviewer note: I did not invoke the `aidd-dev:05-review` skill; I reviewed the three axes directly. No file was edited apart from this report.
