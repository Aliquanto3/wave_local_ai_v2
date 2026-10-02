# Local-run evidence: per-item tokens and first-token time

Two real local batches of the classification suite (`classification-support-routing@4`,
20 items, `baseline`) on `qwen3-0.6b-q8` under llama-server `b10537`, written only to this
folder (`quality.jsonl`, `fiches/`). No committed store was touched: `git status
aidd_docs/results` shows only the README edit.

```sh
LLAMA_SERVER_PATH='C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe' \
SLM_MODELS_DIR='D:\ia\models' ROSTER_ENTRY_ID=qwen3-0.6b-q8 QUALITY_PROVIDERS=local \
QUALITY_RESULTS_PATH=<evidence>/quality.jsonl RUNTIME_RESULTS_PATH=<evidence>/runtime.jsonl \
FICHE_REGISTRY_DIR=<evidence>/fiches uv run wave-local-ai-v2-quality   # run twice
```

Both printed `model=Qwen3-0.6B provider=local accuracy=0.45`. Runs `da37d53e...` and
`8d2dbf0f...`; every row is schema `"18"` and passed the writer gate.

## Per-item figures (first rows of run `da37d53e`)

| item_id | item_tokens_in | item_tokens_out | item_ttft_ms | item_prompt_tokens_cached | item_first_in_batch |
| ------- | -------------- | --------------- | ------------ | ------------------------- | ------------------- |
| billing-01 | 61 | 2 | 16.313 | 0 | true |
| billing-02 | 65 | 2 | 9.997 | 37 | false |
| technical-01 | 60 | 2 | 9.911 | 37 | false |
| billing-fr-01 | 73 | 2 | 11.007 | 37 | false |
| account-de-02 | 71 | 2 | 11.213 | 37 | false |

All 40 rows carry `item_ttft_source: server_reported`, `item_measurement_kind:
single_generation`, no null reason. The batch total stays beside them
(`tokens_out_total: 40`, `energy_kwh` 6.83e-05 repeated on every row). Two readings the
fields exist for:

- The cold first item: 16.3 ms and 15.9 ms against about 10 ms for the rest, in both runs.
- The prompt cache: from the second item on, 37 of each prompt's tokens (the suite's shared
  instruction prefix) were reused, so `item_ttft_ms` covers only the remaining 19 to 36.

## Paired records (`comparisons/`, output in `compare-output.txt`)

Both sides are `baseline`, so each member is an observation ("the sides do not differ on
the compared dimension's key field(s)"); the record still carries the test on identical
item ids.

| --quantity | scoring kind | test | paired n | result |
| ---------- | ------------ | ---- | -------- | ------ |
| `item_tokens_out` | `continuous_measurement` | Wilcoxon signed-rank | 20 | p null, `all_differences_zero` (every item answered in 2 tokens on both runs) |
| `item_tokens_in` | `continuous_measurement` | Wilcoxon signed-rank | 20 | p null, `all_differences_zero` |
| `item_ttft_ms`, first item excluded by selector | `continuous_measurement` | Wilcoxon signed-rank | 19 | W = 93, p = 0.953 |
| `energy_kwh` | `batch_measurement` | none | - | observation: per-batch values 6.8328e-05 and 6.8502e-05, difference 1.74e-07 kWh, reason "energy is measured per batch, never per item: per-item energy on items of a few dozen tokens sits below what the tracker can resolve ..." |

Against the committed bundle (`comparisons-committed/`), rows below schema `"18"` are
refused naming `item_tokens_out (absent)` and `item_measurement_kind (absent)`.

## Not produced

The story's evidence names order 4's cell pair (`baseline` against `output_compressed`).
Order 4 is not implemented on this branch (no `output_compressed` variant is registered),
so no such pair exists; these two `baseline` runs prove the fields and the paired record on
real rows instead. The figures stay in this folder rather than `aidd_docs/results/README.md`,
which documents the fields without publishing an evidence-only run.
