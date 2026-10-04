# Top class: gate and suite runs (2026-10-04, laptop-mobile-gpu)

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each step: GPU 0 MiB, no `llama-server`,
nothing listening on 8080, D: free space read and the run stopped if the download
would leave under 20 GB (logged at the top of each log). After each step: GPU 0 MiB,
no `llama-server` left (each command started and stopped its own server).

## Stage A: the gate

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gate, Gemma 4 12B it (dense) | `wave-local-ai-v2-candidate-gate --candidate candidates/gemma-4-12b-it-iq4xs.json` | exit 0, `passed`; 6,375,734,080 bytes downloaded, sha256 `b0037d0e...6774` (the spike's), `gemma4`, no expert count (dense), 11,907,350,576 params; build `b10537`; template hash `aa3185df...d61b`; the thinking switch verified (two different renders) | `gate-gemma-4-12b-it-iq4xs.log` |

D: had 70,268,579,840 bytes free before the download and 63,892,844,544 after;
6,375,735,296 bytes fewer, within 1,216 bytes of the file's 6,375,734,080.

Not gated: Gemma 4 26B-A4B it (declaration in `candidates/`, `n_cpu_moe` 28 of its 30
layers, the flagship's ratio). Gemma 4 12B is non-Qwen and dense and the flagship is
the class's MoE, so its pass ends the search (owner answers Q127 (a), Q129 (a)),
subject to both suites completing in stage B. The epic's dependency "whether the tower
holds a Gemma-4-class 26B-A4B MoE at a usable quant" stays untested.

Spike resolution line: `gemma4` loaded, closed by the pass record of
`gemma-4-12b-it-iq4xs` (build, template hash and verified thinking control in its
`observed` block).

Launch, declared against launched: the gate's one load ran the declared block
(`-ngl 99`, `-c 32768`, `-fa on`, `-t 8`, no `--n-cpu-moe`, `--load-mode auto`) and
the server came up and answered, so no load refusal occurred and no stepped-down
`-ngl` was re-declared: the launched value equals the declared one. Dedicated GPU
memory, sampled every 2 s (`gate-gemma-4-12b-it-iq4xs.vram.csv`), went 0 -> 5,931 ->
5,959 MiB of 6,144 while the server was up, and plateaued there. The weights are
6,080 MiB (6,375,734,080 B), which alone would fit, but a full offload adds the KV cache
for the 32,768-token context and the compute buffers. So part of the model most likely
sat outside dedicated VRAM, in the shared system memory the Windows driver falls back
to. This is inferred: nvidia-smi reports dedicated memory only, and the logs hold no
llama-server buffer lines. The conclusion that the laptop's speed for this model is not
a full-offload figure is an inference on the same grounds.
`--fit` (on by default in b10537) adjusts only unset arguments, and `-ngl` and `-c` are
set, so it did not change them.

Composition check after the entry: `composition-check.txt` (exit 0, `PASS`; no
failure left).

No `src/` change.

## Stage B: the suites

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gemma 4 12B classification | `wave-local-ai-v2-quality --suite classification-support-routing` | `51bcde3e05814d2097a6be81a83d1e54`, 20 rows, accuracy 1.00 (interval `zero_width`) | `suite-gemma-4-12b-it-iq4xs-classification-support-routing.log` |
| Gemma 4 12B translation | `wave-local-ai-v2-quality --suite translation-business-short-form` | `ff30926f02184ff387c08e5dfafa0ac9`, 21 rows, chrF 0.866 [0.803, 0.921] | `suite-gemma-4-12b-it-iq4xs-translation-business-short-form.log` |
| Promote | `wave-local-ai-v2-promote --run-id <the two> --machine laptop-mobile-gpu` | 41 quality rows added; 1 fiche copied (`c9db1dea...`) | `promote.log` |
| Merge | `wave-local-ai-v2-merge-bundle`, then `--check` | 6 runtime, 285 quality, 0 refusals; check exit 0 | `merge.log` |

Both runs started from commit `6de6888a08be48a40da297e287b7bcd8e9ded324` (the entry
committed) with no tracked change (`git status --porcelain` at the top of each log
lists untracked paths only), so all 41 rows carry `tree_dirty: false` and that sha,
`roster_version` 10, family `google`, `~8B-and-up`, `thinking_policy` `disabled`,
`profile_overrides` `{}`. Each run verified the thinking switch before its first item
(`renders_differ=True`). No item failed (`failure_counts` all 0). The fiche's flags are
the declared ones (`-ngl 99 -c 32768 -fa on -t 8 --jinja -np 1 --load-mode auto`, no
`--n-cpu-moe`): the declared value launched, no fallback value was needed. Dedicated
GPU memory peaked at 5,973 of 6,144 MiB (`suite-*.vram.csv`, sampled every 5 s).
Classification took 33 s, translation 55 s, wall clock per log.
Environment: `MACHINE_ID=laptop-mobile-gpu`, `COMPUTE_MODE=gpu`,
`QUALITY_PROVIDERS=local`, `ROSTER_ENTRY_ID=gemma-4-12b-it-iq4xs`, live store
`quality.jsonl` and fiche registry `fiches/` in this folder. No paid call, no judge, no
`.env`.

Diff of the tracked stores: one hunk `@@ -244,0 +245,41 @@` per file, no line removed;
the last 41 lines of each equal `quality.jsonl` here. `wave-local-ai-v2-validate` with
`FICHE_REGISTRY_DIR` unset: `checked 285 row(s)` on `quality-reference.jsonl` and the
laptop store, `checked 6 row(s)` on `runtime-reference.jsonl`, each exit 0.

The 26B-A4B was not gated: the 12B passed the gate and completed both suites (owner
answer Q129 (a)).
