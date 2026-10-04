# Publication translation suite: source fetch, token count and draw (2026-10-04, laptop-mobile-gpu)

## Stage A: the source and the draw

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Fetch | `uv run python scripts/wmt24pp_suite.py fetch --out <scratch>/table.jsonl --record <scratch>/fetch-record.json --cache <scratch>/cache` | `google/wmt24pp` at `fd7405c06494bc66a57b25f55d217a72f96e60dc`, read-only, no login: the tree listing, `en-fr_FR.jsonl` and `en-de_DE.jsonl`, each equal to the git object id the tree lists (`19bdea58...`, `c9364c8e...`); no licence or NOTICE file at the revision; 998 segments per file, aligned on `segment_id`, 38 `is_bad_source` dropped (the canary and 37 social); 960 rows, pools EN->FR 315, FR->DE 322, DE->EN 323; table SHA-256 `db57a8a457dce9ae2f38e0b4595a582bf9bf471475dc545b3b4bc89e2546f4ed` | `fetch.log`, `fetch-record.json` |
| Count | `llama-server` b10537 on `granite-4.0-h-350m-Q8_0.gguf` (`-ngl 0`, CPU, PID 33604, stopped by PID), then `scripts/wmt24pp_suite.py count-tokens --server http://127.0.0.1:8097 --roster-entry granite-4.0-h-350m-q8` | 960 references counted by `/tokenize` without special tokens; longest drawn 304 tokens (`google/wmt24pp:805`) | `draw.log`, `token-counts.json` |
| Draw | `uv run python scripts/wmt24pp_suite.py draw ...` | seed 20261004, 1 attempt; 300 items, 100 per direction; `max_output_tokens` 608 (2 x 304); per domain: literary 61, news 49, social 158, speech 32 | `draw.log` |
| Replay | `uv run python -m wave_local_ai_v2.subset_replay --suite translation-mixed-domain-wmt24pp --source <scratch>/table.jsonl` | `reproduced: 300 items, same ids, same order` | `replay.log` |

The dataset card (`README.md`, git object id `e80b22b7...`, equal to the tree's) was read
for its licence line (`license: apache-2.0`) and its citation. The table stays outside the
repository; the operator replay re-fetches it (`scripts/wmt24pp_suite.py verify`). The
Apache-2.0 text was copied from a locally installed package (`license_expression`'s
`apache-2.0.LICENSE`, plus the leading blank line), whose result is byte-equal to
https://www.apache.org/licenses/LICENSE-2.0.txt (SHA-256 `cfc7749b...`); nothing else was
downloaded.

## Stage B: the two batches, one session, one subject

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each batch: GPU 0 MiB, no `llama-server`,
`git status --porcelain` listing untracked paths only, HEAD
`0f69b60d54304b7e00bd1ce3cc66647fe553ec2f` (logged at the top of each log). After each:
GPU 0 MiB, no `llama-server` left (the CLI started and stopped its own server).
Environment: `MACHINE_ID=laptop-mobile-gpu`, `COMPUTE_MODE=gpu`, `QUALITY_PROVIDERS=local`,
`ROSTER_ENTRY_ID=granite-4.0-h-350m-q8`, live stores `quality.jsonl` and `fiches/` in this
folder. No paid call, no judge, no `.env`.

Subject: `granite-4.0-h-350m-q8`, as the classification twin; neither the story nor its
epic names one, and it is the model the suite's cap was counted for.

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Publication batch | `wave-local-ai-v2-quality --suite translation-mixed-domain-wmt24pp` (09:08-09:10) | `525734d8b1a44d3681a77aed5b3baee2`, 300 rows, chrF 0.367 [0.347, 0.387], MDE 0.020; EN->FR [0.320, 0.397], FR->DE [0.284, 0.344], DE->EN [0.401, 0.461]; `truncated_max_tokens` 0 (longest completion 320 tokens, cap 608), `empty` 1 (`google/wmt24pp:118`) | `suite-translation-mixed-domain-wmt24pp.log` |
| Development batch | `wave-local-ai-v2-quality --suite translation-business-short-form` (09:10) | `da8737246ed54cbf88ddce02e1d1d26b`, 21 rows, chrF 0.484 [0.358, 0.614], MDE 0.128; no failure | `suite-translation-business-short-form.log` |
| Promote | `wave-local-ai-v2-promote --machine laptop-mobile-gpu --run-id 525734d8... --run-id da873724...` | 321 quality rows added; fiche `5ce2bf21...` already tracked | `promote.log` |
| Merge | `wave-local-ai-v2-merge-bundle`, then `--check` | 6 runtime, 926 quality, 0 refusals; check exit 0 | `merge.log` |
| Validate | `wave-local-ai-v2-validate` (`FICHE_REGISTRY_DIR` unset) on `quality-reference.jsonl`, `runtime-reference.jsonl` and the laptop store | `checked 926 row(s)`, `checked 6 row(s)`, `checked 926 row(s)`, each exit 0 | `validate.log` |
| Export and recompute | `wave-local-ai-v2-export --output-dir <scratch>/export`, then `python scripts/recompute_from_export.py <scratch>/export` | both exit 0; `360 values recomputed (interval), 0 differ`, 40 of them this story's two batches | `export-recompute.log` |

Both batches share `roster_entry_id` `granite-4.0-h-350m-q8`, `fiche_hash` `5ce2bf219e51...`,
`engine_build` `b10537` and `commit_sha` `0f69b60`, and all 321 rows carry
`tree_dirty: false`. Diff of the tracked stores: one hunk of 321 added lines per file, no
line removed. The pairing-test edit (`tests/test_reference_bundle.py`) was made during
the publication batch, by 09:08:50 and after that batch captured its provenance at its start
(09:08:16), and was removed from the tree before the development batch started (09:10:22),
then restored after it; no tracked file differed from `0f69b60` when either batch captured
its provenance.
