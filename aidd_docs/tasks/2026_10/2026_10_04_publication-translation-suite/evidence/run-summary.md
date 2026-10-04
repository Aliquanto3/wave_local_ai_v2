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
