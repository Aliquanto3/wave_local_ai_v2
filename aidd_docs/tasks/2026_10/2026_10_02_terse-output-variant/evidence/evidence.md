# Evidence: the terse-output variant meets baseline in a paired test

Laptop (`laptop-mobile-gpu`, `gpu`), 2026-10-03, pinned build
`llama-b10537-bin-win-cuda-12.4-x64`, roster entry `qwen3-0.6b-q8`, suite
`classification-support-routing@4`, local only (night-run decision D2). Every
results path, the fiche registry, the machine results root and the campaign
directory point into this folder.

```sh
LLAMA_SERVER_PATH=...\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe
SLM_MODELS_DIR=D:\ia\models QUALITY_PROVIDERS=local ROSTER_ENTRY_ID=qwen3-0.6b-q8
MACHINE_ID=laptop-mobile-gpu COMPUTE_MODE=gpu CAMPAIGN_ID=terse-output-laptop
CAMPAIGNS_DIR=<evidence>/campaigns QUALITY_RESULTS_PATH=QUALITY_REFERENCE_PATH=<evidence>/quality.jsonl
RUNTIME_RESULTS_PATH=RUNTIME_REFERENCE_PATH=<evidence>/runtime.jsonl
FICHE_REGISTRY_DIR=<evidence>/fiches MACHINE_RESULTS_ROOT=<evidence>/machines
uv run wave-local-ai-v2-quality --suite classification-support-routing                                       # quality-baseline.log, accuracy=0.45, exit 0
uv run wave-local-ai-v2-quality --suite classification-support-routing --prompt-variant output_compressed  # quality-output-compressed.log, accuracy=0.30, exit 0
uv run wave-local-ai-v2-campaign-completeness --campaign terse-output-laptop --campaigns-dir <evidence>/campaigns --rows <evidence>/quality.jsonl  # 2 cells filled, exit 0
uv run wave-local-ai-v2-compare --reference 9a68cbaf9dd147a9b179edfd7b605b58 --candidate 13ade3c585b64455bd4d2fd4ce9f0337 --dimension prompt_variant [--quantity item_tokens_out] --rows <evidence>/quality.jsonl --records-dir <evidence>/comparisons
FICHE_REGISTRY_DIR=aidd_docs/tasks/2026_10/2026_10_02_named-run-profiles/evidence/fiches uv run wave-local-ai-v2-validate <evidence>/quality.jsonl  # validate.log: checked 40 row(s), exit 0
```

| Record | Kind | Differing fields | Confounds | Result | Verdict |
| --- | --- | --- | --- | --- | --- |
| `comparisons/...prompt_variant.58b1ecc07d7f.json` (score) | test | `prompt_variant_id` | none | McNemar exact, b=3, c=0, p=0.25, `reference_higher` | not distinguishable |
| `comparisons/...prompt_variant.item_tokens_out.e11111ca3af7.json` | test | `prompt_variant_id` | none | Wilcoxon, all 20 differences zero, mean 2.0 vs 2.0 | not distinguishable |

The run wrote one fiche, `73ec536e...`, byte-identical to the one the
named-run-profiles evidence already tracks (same model, machine, mode and
build), so it is not duplicated here and the rows validate against that
registry.

Both arms are at version "1", so `prompt_variant_version` does not differ;
nothing outside the variant fields does. A first comparison, before the
`score_interval` fix, published the pair as an observation with confound
`score_interval`; that record was discarded and regenerated after the fix.
