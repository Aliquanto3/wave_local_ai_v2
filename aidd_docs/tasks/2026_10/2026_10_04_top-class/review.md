# Review: the top class spans two families with dense and MoE (round 1, 2026-10-04)

VERDICT: CHANGES-REQUIRED

Scope: this review covers the committed stage A (`6de6888`: the roster entry, the candidate record, the two candidate declarations, `docs/setup.md` 1.2 and 3.6, the tests, `.secrets.baseline`, `memory/cli.md` and the README composition section) and the uncommitted stage B (41 rows, 1 fiche, the README rows section and the evidence).

Blocking findings:
1. The shared-memory finding rests on a false premise. `aidd_docs/results/README.md:1081` says "The weights alone (6.38 GB) exceed the GPU's 6,144 MiB", and `docs/setup.md:632-633` and `evidence/run-summary.md:33` say the same. But 6,375,734,080 B is 6,080 MiB, which is below 6,144 MiB, so the weights alone do not exceed the GPU's memory. The logs hold no llama-server buffer lines, so no measurement shows where the excess sits. Fix: state the true figures. The weights take 6,080 MiB of 6,144, with the KV cache at a 32,768-token context and the compute buffers on top. Dedicated memory plateaued at 5,959 to 5,973 MiB. The spill into shared memory is inferred, not measured. Drop "necessarily". The conclusion ("not a full-offload speed figure") can stay as an inference. This is a docs-only change and needs no rerun. The `6de6888` commit message repeats the claim; leave it, since the history stays as it is.

Acceptance:
- Shortlist, gate order, pins and the Q129 (a) stop rule: proven.
  - The candidate declarations equal the story's pins: repo, sha, file, bytes, `gemma4`, and `enable_thinking: false` for both.
  - The 12B (the smaller download) was gated first. D: free space fell 70,268,579,840 -> 63,892,844,544 B, within 1,216 B of the file size, so the download was real.
  - The 26B-A4B was correctly not gated, because the 12B passed the gate and both suites. The README and run-summary record the tower dependency as untested.
  - The README records no refusal and no deferral. HF listing re-read: unsloth ships only `IQ4_XS` and `IQ4_NL` at 4-bit for the 12B (no `UD-IQ4_XS`), so "nearest" holds.
- The quant difference "stated in the candidate record": NOT MET as written; met in substance. See the owner note below.
- Entry from the pass record: proven.
  - A scripted field-by-field diff of the record's `entry` against `models.json` finds only `requirements`, which the roster adds.
  - The entry matches the pass record: google, dense, `expert_count` 0, 11,907,350,576 params, `IQ4_XS`, `thinking_control` the verified switch.
  - The sha256 `b0037d0e...6774` equals the spike (l.73), `observed.sha256`, and a fresh `sha256sum` of `D:\ia\models\gemma-4-12b-it\gemma-4-12b-it-IQ4_XS.gguf`.
  - `roster_version` moved 9 -> 10. `setup.md` 3.6 holds `hf download --revision fc034cff...` and `Get-FileHash ... .ToLower()`.
  - Tests: `test_the_top_class_spans_two_families_with_dense_and_moe`, `SHIPPED_SECOND_FAMILY_ENTRIES` and `SHIPPED_FIGURES`.
- Suites, rows and append-only: proven.
  - 20 + 21 rows. All 41 carry `tree_dirty: false`, `commit_sha` `6de6888a...`, `roster_version` 10, `google`, `~8B-and-up`, `disabled`, `profile_overrides` `{}`, and one fiche.
  - Append-only: `git diff -U0` shows one hunk `@@ -244,0 +245,41 @@` per store, with 0 removed lines. The last 41 lines of each store equal `evidence/quality.jsonl`.
  - The fiche's flags equal the declared ones (`-ngl 99 -c 32768 -fa on -t 8 --load-mode auto`, no `--n-cpu-moe`), so the launched value equals the declared value.
- Launch blocks (dense, no offload, no load refusal): proven. The value that launched is recorded. The memory explanation is wrong (blocking 1).
- Declaration states two families, dense and MoE: proven. The flagship is unchanged: the diff only adds the entry and bumps the version.
- Composition check passes and the README is regenerated: proven. The live `composition-check` exits 0, and its output is a substring of the README and byte-equal to `evidence/composition-check.txt`.
- Q126 deferred/refused handling: n/a, because nothing was refused.
- `gemma4` spike closure: proven. The pass record's `observed` holds the build b10537, the template hash and the verified thinking control.
- EN/FR/DE claim versus the rows: proven. No language is claimed.
  - All 21 `subject_output` values are in the target language. Classification is 20/20 (en 10, fr 5, de 5).
  - chrF 0.866; per direction 0.893, 0.785 and 0.920, recomputed from `item_score`. `fr-de-04` 0.453 and `fr-de-05` 0.625 are paraphrases, as the README says.
  - The flagship's local runs `acb6e894` and `68ac4f21` at `@5` each score 20/20, and no flagship row exists at translation `@4`, as stated.

Owner note (implementer's finding 1): the line is not ACCEPTANCE-WRONG, because the code could have satisfied it.
- `candidate_gate.parse_candidate` (`src/wave_local_ai_v2/candidate_gate.py:248`) checks only for missing keys.
- The record stores the declaration verbatim (`"candidate": candidate.raw`, l.721).
- So a free-text key such as `quant_note` in the declaration would have reached the append-only record. The claim that the record "has no free-text field" is therefore inaccurate.
- I do not count it as blocking, for two reasons. The record does carry `quant: IQ4_XS`, against the flagship's `UD-IQ4_XS`. The story's purpose ("not read as a quant comparison") is met on every reader surface: README l.1059, `setup.md` 3.6 and the evidence.
- Fixing the record now needs a new gate run, which means a model load. The owner chooses: accept the README as the statement, or re-gate with a `quant_note`. Future declarations should carry such a note.

Checks:
- `merge-bundle --check` exits 0 (6 runtime, 285 quality).
- `validate` with `FICHE_REGISTRY_DIR` unset reports 285/285/6 rows, each exit 0.
- `ruff check` and `ruff format --check` pass. detect-secrets over the stage B files exits 0.
- The `.secrets.baseline` hashes equal the SHA-1 of the three public pins.
- Tests: `timeout 900 uv run pytest -q` => `3065 passed, 20 skipped, 2 warnings in 225.22s`, coverage 98.51%.

Non-blocking:
- The bold lead at README l.753, "Today it fails, which is the honest state.", is now contradicted by the paragraph's own last line ("the check now passes"). Retitle it.
- The untracked fiche `aidd_docs/results/fiches/c9db1dea...json` must be committed with the rows (it is byte-equal to the evidence copy).
- No flagship translation row exists at `@4`, so the class's translation side-by-side is missing (the README states this).

Reviewer note: I did not invoke the `aidd-dev:05-review` skill; I reviewed the three axes directly. No file was edited apart from this report.

## Round 2 (2026-10-04)

VERDICT: PASS

Blocking findings: none. Round 1's blocking 1 is resolved.
- `docs/setup.md` 3.6 (l.632-638), README l.1081-1089 and `evidence/run-summary.md` l.31-39 now give the true figures:
  - weights 6,080 MiB (6,375,734,080 B), which would fit under 6,144 MiB on their own;
  - the KV cache at a 32,768-token context and the compute buffers on top;
  - a dedicated-memory plateau of 5,959 MiB (gate) and 5,973 MiB (suites).
- The spill into shared memory is labelled an inference ("the logs hold no llama-server buffer lines"), and "necessarily" is gone.
- README l.753 is reworded to the past tense ("It failed at first, which was the honest state."), so it no longer contradicts the paragraph's own last line.

Nothing else changed since round 1:
- Against HEAD `6de6888`, the tracked diff covers only the round 1 stage B files (README, the two quality stores, run-summary, phase-3, plan) plus `docs/setup.md`. Nothing under `src/`, `tests/` or `aidd_docs/roster/` changed.
- The untracked set is the same, plus this report.
- Each store still has one hunk `@@ -244,0 +245,41 @@`, and its last 41 lines equal `evidence/quality.jsonl`. The promoted fiche is byte-equal to the evidence copy.
- The composition check exits 0, and its output appears verbatim in the README.
- `merge-bundle --check` exits 0 (6 runtime, 285 quality). `validate` with `FICHE_REGISTRY_DIR` unset reports 285/285/6 rows, each exit 0.
- Tests: `timeout 900 uv run pytest -q` => `3065 passed, 20 skipped, 2 warnings in 221.31s`, coverage 98.51%, rc 0.

Acceptance: unchanged from round 1. Every line is proven or n/a, except the quant difference "stated in the candidate record". That line is not met as written and is met in substance; it is left to the owner (see the round 1 owner note), and it is not ACCEPTANCE-WRONG.

Non-blocking:
- README l.1112 still calls the 5,973 MiB peak "the full-GPU state the gate showed". It means "the dedicated memory filled", which is consistent with the inference, but the wording could be read as a full offload.
- The untracked fiche `aidd_docs/results/fiches/c9db1dea...json` must be committed with the rows.
