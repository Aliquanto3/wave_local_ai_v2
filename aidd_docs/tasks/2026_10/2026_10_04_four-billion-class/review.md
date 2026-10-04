# Review: the ~4B class spans two families (round 1, 2026-10-04)

VERDICT: PASS

Scope: this review covers the committed stage A (`3008ef9`: the roster entry, the candidate record, the ~4B declaration, `docs/setup.md` 3.5, the tests, `.secrets.baseline` and `memory/cli.md`) and the uncommitted stage B (41 rows, 1 fiche, the README rows section and the evidence).

Blocking findings: none.

Acceptance:
- Shortlist, gate order, quant and stop rule: proven.
  - The four candidate declarations match the story's pins: repo, sha, file, `Q4_K_M` (Phi-tiny-MoE `Q8_0` with `context_size` 4096) and `load_profile`.
  - Granite 3.1 3B-A800M is the smallest download (2,016,888,384 B < 2,147,023,008 < 2,491,874,272 < 3,999,171,104), so it was gated first.
  - Its gate log exits 0. D: free space fell by exactly 2,016,888,384 B (72,285,470,720 -> 70,268,582,336), so this was a real download.
  - Stopping after it is what the story requires, not a shortcut. Q128 (a) reads: "Granite 3.1 3B-A800M is non-Qwen and MoE at once, so its pass (gate and both suites) ends the search, and `mistral3`, `phi3` and `phimoe` are then not reached." The story does not require the dense non-Qwen candidates. No refusal or deferral happened, so the candidate record holds the single pass.
- Entry from the pass record: proven.
  - A scripted field-by-field comparison of `entry` against `models.json` found one difference only: `requirements`, which the roster adds. The remaining fields match: `kind` moe, `expert_count` 40, `total_params` 3,298,793,472, `Q4_K_M` and the sha256 `48e0edcd...a82b3`.
  - The sha256 matches the spike's sha (spike l.73) and the hash of the file on disk (`sha256sum`).
  - The local GGUF header shows `granitemoe`, `expert_count` 40, `expert_used_count` 8, `file_type` 15 (Q4_K_M).
  - `roster_version` moved 8 -> 9. The ~4B declaration reads `moe_sought: true`, `moe_entry: granite-3.1-3b-a800m-instruct-q4km`, `single_family_ladder: false`.
  - `docs/setup.md` 3.5 holds `hf download ... --revision be9a36f0...` and `Get-FileHash ... .ToLower()`, and its sha and size are correct.
  - Tests: `test_the_four_billion_class_spans_two_families_and_holds_its_moe`, `SHIPPED_SECOND_FAMILY_ENTRIES` and `SHIPPED_FIGURES`.
- Suites to completion, row fields, append-only: proven.
  - Rows: 2 runs, 20 + 21 rows, `failure_counts` all 0. All 41 rows carry `tree_dirty: false`, `commit_sha` `3008ef92...`, `roster_version` 9, `family` ibm, `~4B`, `disabled`, and the same fiche.
  - Launch: the fiche flags are the declared ones (`-ngl 99 -c 32768 -t 8`, no `--n-cpu-moe`) and `profile_overrides` is `{}`, so no fallback was needed.
  - Append-only: `git diff -U0` shows one hunk `@@ -203,0 +204,41 @@` per store and 0 removed lines. The last 41 lines of each store equal `evidence/quality.jsonl`.
  - Checks: `merge-bundle --check` exits 0 (6 runtime, 244 quality). `validate` with `FICHE_REGISTRY_DIR` unset reports 244/244/6 rows, each exit 0.
- MoE question answered, and the declaration states two families: proven (ibm, qwen; dense and MoE).
- Composition check passes for ~4B, and the README block is regenerated: proven. The live output is byte-equal to both the README block (l.768) and `evidence/composition-check.txt`. The command exits 1 only for `~8B-and-up`, as expected.
- Q126 deferred/refused handling: n/a, because nothing was refused or deferred.
- Spike resolution lines: proven in the README. `granitemoe` was closed at ~2B and loaded again here, with build, template hash and thinking. `mistral3`, `phi3` and `phimoe` show "not reached: class stopped at ...".
- EN/FR/DE claim versus rows: proven. All 21 `subject_output` values are in the target language. `fr-de-06` "Un technische" and `en-fr-05` "L'bureau" are confirmed. Accuracy is 0.75 (en 0.70, fr/de 0.80). The five misroutes match the README exactly. chrF is 0.710, with per-direction figures 0.659/0.566/0.904 recomputed from `item_score`.

Other checks:
- `.secrets.baseline` additions: the SHA-1 of the five public pins (the entry's revision and sha256, plus the three other candidates' revisions), verified by recomputing them.
- detect-secrets over the stage B files, with the hook's own fiche exclusion: exit 0.
- Tests: `timeout 900 uv run pytest -q` => `3062 passed, 20 skipped, 2 warnings in 221.82s`, coverage 98.51%.

Non-blocking:
- The untracked fiche `aidd_docs/results/fiches/6159f6b5...json` must be committed together with the rows, or the validator fails on a clean clone.
- No `Qwen3-4B` rows exist at `classification@5` and `translation@4`, so the side-by-side rests on superseded tables (the README states this). Re-running `qwen3-4b-q4km` would close the story's "So that".
- The entry copies Qwen's sampler (0.6/20/1.5), as the ~0.5B and ~2B precedents did. Suites send their own sampling, so the rows are unaffected.
- `requirements.*.ram_gb` 2.02 is the weights only and is labelled a lower bound.
- `en-fr-02` renders "invoice" as "L'affrètement", a lexical error in the right language. The README's two named errors are a sample, not the full list.

Reviewer note: I did not invoke the `aidd-dev:05-review` skill; I reviewed the three axes directly. No file was edited apart from this report.
