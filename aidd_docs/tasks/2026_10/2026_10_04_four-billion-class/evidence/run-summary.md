# Four-billion class: gate and suite runs (2026-10-04, laptop-mobile-gpu)

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each step: GPU 0 MiB, no `llama-server`,
nothing listening on 8080, D: free space read and the run stopped if the download
would leave under 20 GB (logged at the top of each log). After each step: GPU 0 MiB,
no `llama-server` left (each command started and stopped its own server).

## Stage A: the gate

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gate, Granite 3.1 3B-A800M (MoE) | `wave-local-ai-v2-candidate-gate --candidate candidates/granite-3.1-3b-a800m-instruct-q4km.json` | exit 0, `passed`; 2,016,888,384 bytes downloaded, sha256 `48e0edcd...82b3` (the spike's), `granitemoe`, 40 experts (8 used), 3,298,793,472 params; build `b10537`; template hash `22da3019...d800`; `none` verified | `gate-granite-3.1-3b-a800m-instruct-q4km.log` |

D: had 72,285,470,720 bytes free before the download and 70,268,579,840 after;
2,016,888,384 bytes downloaded in all.

Not gated: Ministral 3 3B Instruct 2512, Phi-4-mini-instruct and Phi-tiny-MoE-instruct
(declarations in `candidates/`): Granite 3.1 3B-A800M is non-Qwen and MoE at once, so
its pass ends the search (owner answers Q127 (a), Q128 (a)), subject to both suites
completing in stage B.

Spike resolution lines: `granitemoe` already closed at `~2B`, loaded again here (pass
record of `granite-3.1-3b-a800m-instruct-q4km`); `mistral3`, `phi3`, `phimoe` not
reached: class stopped at `granite-3.1-3b-a800m-instruct-q4km`.

Launch: the gate's one load ran the declared block (`-ngl 99`, `-c 32768`, no
`--n-cpu-moe`, `-t 8`) and the server came up, so the declared offload fits.

Composition check after the entry: `composition-check.txt` (no `~4B` failure; one
failure left, in `~8B-and-up`).

No `src/` change.

## Stage B: the suites

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Granite 3.1 3B-A800M classification | `wave-local-ai-v2-quality --suite classification-support-routing` | `6630e70b3bf842d2820b8dfa5acab5dd`, 20 rows, accuracy 0.75 [0.55, 0.90] | `suite-granite-3.1-3b-a800m-instruct-q4km-classification-support-routing.log` |
| Granite 3.1 3B-A800M translation | `wave-local-ai-v2-quality --suite translation-business-short-form` | `316508c8f6ad4ff3a899b4341f481a9a`, 21 rows, chrF 0.710 [0.627, 0.792] | `suite-granite-3.1-3b-a800m-instruct-q4km-translation-business-short-form.log` |
| Promote | `wave-local-ai-v2-promote --run-id <the two> --machine laptop-mobile-gpu` | 41 quality rows added; 1 fiche copied (`6159f6b5...`) | `promote.log` |
| Merge | `wave-local-ai-v2-merge-bundle`, then `--check` | 6 runtime, 244 quality, 0 refusals; check exit 0 | `merge.log` |

Both runs started from commit `3008ef92fa86b203d633815f154f2d329b8f1d66` (the entry
committed) with no tracked change (`git status --porcelain` at the top of each log
lists untracked paths only), so all 41 rows carry `tree_dirty: false` and that sha,
`roster_version` 9, family `ibm`, `~4B`, `thinking_policy` `disabled`. No item failed
(`failure_counts` all 0). The fiche's flags are the declared ones (`-ngl 99 -c 32768
-t 8`, no `--n-cpu-moe`): the declared offload fit, no fallback value was needed.
Environment: `MACHINE_ID=laptop-mobile-gpu`, `COMPUTE_MODE=gpu`,
`QUALITY_PROVIDERS=local`, `ROSTER_ENTRY_ID=granite-3.1-3b-a800m-instruct-q4km`, live
store `quality.jsonl` and fiche registry `fiches/` in this folder. No paid call, no
judge, no `.env`.

Diff of the tracked stores: one hunk `@@ -203,0 +204,41 @@` per file, no line removed;
the bundle's last 41 lines equal `quality.jsonl` here. `wave-local-ai-v2-validate` with
`FICHE_REGISTRY_DIR` unset: `checked 244 row(s)` on `quality-reference.jsonl` and the
laptop store, `checked 6 row(s)` on `runtime-reference.jsonl`, each exit 0.
