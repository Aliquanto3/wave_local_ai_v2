# Two-billion class: gate and suite runs (2026-10-04, laptop-mobile-gpu)

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each step: GPU 0 MiB, no `llama-server`,
nothing listening on 8080, D: free space read and the run stopped if the download
would leave under 20 GB (logged at the top of each log). After each step: GPU 0 MiB,
no `llama-server` left (each command started and stopped its own server).

## Stage A: the gate

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gate, LFM2.5-1.2B-Instruct | `wave-local-ai-v2-candidate-gate --candidate candidates/lfm2.5-1.2b-instruct-q8.json` | exit 0, `passed`; 1,246,253,888 bytes downloaded, sha256 `f6b981dc...d26a` (the spike's), `lfm2`, dense, 1,170,340,608 params; build `b10537`; template hash `f05bf4b9...8176`; `none` verified | `gate-lfm2.5-1.2b-instruct-q8.log` |
| Gate, Granite 3.1 1B-A400M (MoE) | `wave-local-ai-v2-candidate-gate --candidate candidates/granite-3.1-1b-a400m-instruct-q8.json` | exit 0, `passed`; 1,422,239,776 bytes downloaded, sha256 `72430235...7650` (the spike's), `granitemoe`, 32 experts, 1,334,628,352 params; build `b10537`; template hash `22da3019...d800`; `none` verified | `gate-granite-3.1-1b-a400m-instruct-q8.log` |

D: had 74,953,969,664 bytes free before the first download and 73,707,712,512 before
the second; 2,668,493,664 bytes downloaded in all.

Not gated: Granite 4.0 H 1B and Granite 4.0 1B (declarations in `candidates/`): once
LFM2.5-1.2B-Instruct, a non-Qwen family, passed, further dense candidates are skipped
and only the MoE candidate is still tried (owner answer Q127 (a)).

Spike resolution lines: `granitemoe` loaded (pass record of
`granite-3.1-1b-a400m-instruct-q8`); `lfm2` loaded (pass record of
`lfm2.5-1.2b-instruct-q8`); `granitehybrid` closed at `~0.5B`; `granite` not reached:
class stopped at `granite-3.1-1b-a400m-instruct-q8`.

Composition check after the entries: `composition-check.txt` (no `~2B` failure; three
failures in `~4B` and `~8B-and-up`).

No `src/` change.

## Stage B: the suites

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| LFM2.5 classification | `wave-local-ai-v2-quality --suite classification-support-routing` | `02d855b6b1b24edab26b6e32e59a9e26`, 20 rows, accuracy 0.85 [0.70, 1.00] | `suite-lfm2.5-1.2b-instruct-q8-classification-support-routing.log` |
| LFM2.5 translation | `wave-local-ai-v2-quality --suite translation-business-short-form` | `e6acc5a1051745ae80c325b3ce61fb32`, 21 rows, chrF 0.723 [0.647, 0.799] | `suite-lfm2.5-1.2b-instruct-q8-translation-business-short-form.log` |
| Granite MoE classification | as above | `7122bd3e67624735aad92dbcdb82f5be`, 20 rows, accuracy 0.60 [0.40, 0.80] | `suite-granite-3.1-1b-a400m-instruct-q8-classification-support-routing.log` |
| Granite MoE translation | as above | `4db0b4be4cb54e43a16e2ecffa927387`, 21 rows, chrF 0.561 [0.497, 0.631] | `suite-granite-3.1-1b-a400m-instruct-q8-translation-business-short-form.log` |
| Promote | `wave-local-ai-v2-promote --run-id <the four> --machine laptop-mobile-gpu` | 82 quality rows added; 2 fiches copied (`53fa3307...`, `add6a317...`) | `promote.log` |
| Merge | `wave-local-ai-v2-merge-bundle`, then `--check` | 6 runtime, 203 quality, 0 refusals; check exit 0 | `merge.log` |

Every run started from commit `5fc6901d573ad10848e03309ad1d6c44e1179f4b` (the entries
committed) with no tracked change (`git status --porcelain` at the top of each log lists
untracked paths only), so all 82 rows carry `tree_dirty: false` and that sha. No item
failed (`failure_counts` all 0). Environment: `MACHINE_ID=laptop-mobile-gpu`,
`COMPUTE_MODE=gpu`, `QUALITY_PROVIDERS=local`, `ROSTER_ENTRY_ID=<entry>`, live store
`quality.jsonl` and fiche registry `fiches/` in this folder. No paid call, no judge, no
`.env`.

Diff of the tracked stores: one hunk `@@ -121,0 +122,82 @@` per file, no line removed.
`wave-local-ai-v2-validate` with `FICHE_REGISTRY_DIR` unset: `checked 203 row(s)` on
`quality-reference.jsonl` and the laptop store, `checked 6 row(s)` on
`runtime-reference.jsonl`, each exit 0.
