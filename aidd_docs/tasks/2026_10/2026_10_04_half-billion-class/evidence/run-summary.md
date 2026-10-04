# Half-billion class: gate and suite runs (2026-10-04, laptop-mobile-gpu)

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each step: GPU 0 MiB, no `llama-server`
(logged at the top of each log). After each step: GPU 0 MiB, no `llama-server` left
(each command started and stopped its own server). D: had 75,320,168,448 bytes free
before the one download.

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gate, Granite 4.0 H 350M | `wave-local-ai-v2-candidate-gate --candidate candidates/granite-4.0-h-350m-q8.json` | exit 0, `passed`; 366,195,616 bytes downloaded, sha256 `c7d98736...c942` (the spike's), `granitehybrid`, dense, 340,332,224 params; build `b10537`; template hash `9524df67...83ce`; `none` verified | `gate-granite-4.0-h-350m-q8.log` |
| Classification (published) | `wave-local-ai-v2-quality --suite classification-support-routing` | `cb8cb4ffa7754de4b567e3f901953706`, 20 rows, accuracy 0.50 | `clean-rerun/suite-classification-support-routing.log` |
| Translation (published) | `wave-local-ai-v2-quality --suite translation-business-short-form` | `be0dda5eeaa24862ad4ffbd11d10d61e`, 21 rows, chrF 0.484 | `clean-rerun/suite-translation-business-short-form.log` |
| Promote | `wave-local-ai-v2-promote --run-id cb8cb4ff... --run-id be0dda5e... --machine laptop-mobile-gpu` | 41 quality rows; the fiche already tracked | `clean-rerun/promote.log` |
| Merge | `wave-local-ai-v2-merge-bundle`, then `--check` | 6 runtime, 121 quality, 0 refusals; check exit 0 | `clean-rerun/merge.log` |

The published runs ran from commit `8852bf0252cd90ca08a6e0473d998c282b60dc34` (the
entry committed) with no tracked change (`git status --porcelain` listing untracked paths only, no tracked change, at the top of
each log), so every row carries `tree_dirty: false`. Their live store and fiche
registry are in `clean-rerun/`.

**Superseded, not published: the first pair of runs.** `29295f9be29f4901998e6958de0cfa65`
(classification) and `d8c5b24b38194c34b42f225ad44af0f9` (translation) ran from the
uncommitted entry on `4cf22a17` (`tree_dirty: true`, a commit whose roster lacks the
entry), which Methodology 19 rules out for a published row; their rows were reverted
from the tracked location before commit. Kept here as evidence: `quality.jsonl`,
`fiches/`, `suite-classification.log`, `suite-translation.log`, `promote.log`,
`merge.log` in this folder. The clean re-run reproduced them exactly: every one of the
41 items has the same output and score, the same fiche (`5ce2bf21...`), so the same
suite scores and intervals.

Environment of the suite runs: `MACHINE_ID=laptop-mobile-gpu`, `COMPUTE_MODE=gpu`,
`QUALITY_PROVIDERS=local`, `ROSTER_ENTRY_ID=granite-4.0-h-350m-q8`, live stores
(`quality.jsonl`, `runtime.jsonl`) and fiche registry (`fiches/`) in `clean-rerun/`. No
paid call, no judge, no `.env`.

Not run: Granite 4.0 350M and LFM2.5-350M (declarations in `candidates/`, never
gated): the class stopped at the first candidate that passed and completed both suites
(owner answer Q127 (a)). Nothing else was downloaded.

Spike resolution lines: `granitehybrid` loaded (pass record of
`granite-4.0-h-350m-q8`); `granite` and `lfm2` not reached: class stopped at
`granite-4.0-h-350m-q8`.

Code beyond the story's change list: `scripts/release_parquet.py` gains the unit
`as the metric defines` (string). The bundle's first translation rows bring the
`metric_params_*` columns into `quality_items`, whose unit had no Parquet type, so the
release Parquet build refused the bundle.

Composition check after the change: `composition-check.txt` (no `~0.5B` failure; five
failures in the other three classes).
