# Publication classification suite: source fetch and the two published batches (2026-10-04, laptop-mobile-gpu)

## Stage A: the source and the draw

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Fetch | `uv run --offline --group loaders python scripts/minds14_suite.py fetch --out <scratch>/table.jsonl --record <scratch>/fetch-record.json --cache <scratch>/cache` | `PolyAI/minds14` at `40ce77cb32a384e4d50a568e1ec39ac804019d33`: the tree listing and the `en-US`, `fr-FR`, `de-DE` parquet files, each checked against its LFS SHA-256; no licence file at the revision; 1713 rows; table SHA-256 `9172eba3...1dc06` (the full value is the definition's `source_table.sha256`) | `fetch.log` |
| Draw | `uv run python scripts/minds14_suite.py draw ...` | seed 20261004, 1 attempt; 300 items, 100 per language, 8 per intent for `abroad` and `address`, 7 for the other twelve; smallest source cell `fr`/`app_error`, 31 rows | n/a |
| Replay | `uv run python -m wave_local_ai_v2.subset_replay --suite classification-banking-intents-minds14 --source <scratch>/table.jsonl` | `reproduced: 300 items, same ids, same order` | `replay.log` |

pyarrow 25.0.1 came from the uv cache (`--offline`); `MInDS-14.zip` was not fetched. The
table and the fetch record stay outside the repository; the operator replay re-fetches
them (`scripts/minds14_suite.py verify`).

## Stage B: the two batches, one session, one subject

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each batch: GPU 0 MiB, no `llama-server`,
`git status --porcelain` listing untracked paths only, HEAD `95040a7b0e7fa891e406c63e7e0cee46909d9292`
(logged at the top of each log). After each: GPU 0 MiB, no `llama-server` left (the CLI
started and stopped its own server). Environment: `MACHINE_ID=laptop-mobile-gpu`,
`COMPUTE_MODE=gpu`, `QUALITY_PROVIDERS=local`, `ROSTER_ENTRY_ID=granite-4.0-h-350m-q8`,
live stores `quality.jsonl` and `fiches/` in this folder. No paid call, no judge, no `.env`.

Subject: `granite-4.0-h-350m-q8`. Neither the story nor its epic names one; it is the
cheapest laptop-local roster entry (0.34B parameters), runs on the laptop's default `gpu`
profile, and already has a tracked fiche on this machine.

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Publication batch | `wave-local-ai-v2-quality --suite classification-banking-intents-minds14` | `7b8f2569a2044a9e9f8f62a0b7770098`, 300 rows, accuracy 0.227 [0.180, 0.277], MDE 0.048; 6 `unparseable` | `suite-classification-banking-intents-minds14.log` |
| Development batch | `wave-local-ai-v2-quality --suite classification-support-routing` | `1c5a5471245e458d80dea8393383b59e`, 20 rows, accuracy 0.50 [0.30, 0.70], MDE 0.200; no failure | `suite-classification-support-routing.log` |
| Promote | `wave-local-ai-v2-promote --machine laptop-mobile-gpu --run-id 7b8f2569... --run-id 1c5a5471...` | 320 quality rows added; fiche `5ce2bf21...` already tracked | `promote.log` |
| Merge | `wave-local-ai-v2-merge-bundle`, then `--check` | 6 runtime, 605 quality, 0 refusals; check exit 0 | `merge.log` |
| Validate | `wave-local-ai-v2-validate` (`FICHE_REGISTRY_DIR` unset) on `quality-reference.jsonl`, `runtime-reference.jsonl` and the laptop store | `checked 605 row(s)`, `checked 6 row(s)`, `checked 605 row(s)`, each exit 0 | `validate.log` |
| Export and recompute | `wave-local-ai-v2-export --output-dir <scratch>/export`, then `python scripts/recompute_from_export.py <scratch>/export` | both exit 0; `320 values recomputed (interval), 0 differ`, 40 of them this story's two batches | `export-recompute.log` |

Both batches share `roster_entry_id` `granite-4.0-h-350m-q8`, `fiche_hash`
`5ce2bf219e51...` and `engine_build` `b10537`, and all 320 rows carry `tree_dirty: false`
and commit `95040a7b0e7fa891e406c63e7e0cee46909d9292`. Diff of the tracked stores: one
hunk of 320 added lines per file, no line removed.
