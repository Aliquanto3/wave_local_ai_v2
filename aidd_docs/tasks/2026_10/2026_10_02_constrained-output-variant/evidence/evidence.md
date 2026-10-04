# Evidence: the constrained-output variant runs under a llama.cpp grammar

Laptop (`laptop-mobile-gpu`, `gpu`), 2026-10-03, pinned build
`llama-b10537-bin-win-cuda-12.4-x64`, roster entry `qwen3-0.6b-q8`, suite
`classification-support-routing@4`, local only (night-run decision D2). Every
results path, the fiche registry, the machine results root and the campaign
directory point into this folder.

```sh
# grammar-probe.json: a probe llama-server on port 8091, three
# /v1/chat/completions requests on a "technical" message: no grammar ->
# technical; the four-label grammar -> technical; root ::= "billing" -> billing.
"$LLAMA_SERVER_PATH" -m D:/ia/models/Qwen3-0.6B/Qwen3-0.6B-Q8_0.gguf --host 127.0.0.1 --port 8091 -ngl 99 &   # stopped afterwards by its PID
uv run python <evidence>/grammar_probe.py > <evidence>/grammar-probe.json
LLAMA_SERVER_PATH=...\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe
SLM_MODELS_DIR=D:\ia\models QUALITY_PROVIDERS=local ROSTER_ENTRY_ID=qwen3-0.6b-q8
MACHINE_ID=laptop-mobile-gpu COMPUTE_MODE=gpu CAMPAIGN_ID=constrained-output-laptop
CAMPAIGNS_DIR=<evidence>/campaigns QUALITY_RESULTS_PATH=QUALITY_REFERENCE_PATH=<evidence>/quality.jsonl
RUNTIME_RESULTS_PATH=RUNTIME_REFERENCE_PATH=<evidence>/runtime.jsonl
FICHE_REGISTRY_DIR=<evidence>/fiches MACHINE_RESULTS_ROOT=<evidence>/machines
uv run wave-local-ai-v2-quality --suite classification-support-routing                                        # quality-baseline.log, accuracy=0.45, exit 0
uv run wave-local-ai-v2-quality --suite classification-support-routing --prompt-variant constrained_output   # quality-constrained-output.log, accuracy=0.45, exit 0
uv run python <evidence>/baseline_format_replay.py > <evidence>/baseline-format-replay.json   # same env plus E=<evidence>; spawns and terminates its own server on 8091
uv run wave-local-ai-v2-campaign-completeness --campaign constrained-output-laptop --campaigns-dir <evidence>/campaigns --rows <evidence>/quality.jsonl  # 2 cells filled, exit 0
uv run wave-local-ai-v2-compare --reference 962f939a9d674078844d582dba9e945c --candidate 6d16257704594d79b427826bcb696455 --dimension prompt_variant --rows <evidence>/quality.jsonl --records-dir <evidence>/comparisons
FICHE_REGISTRY_DIR=aidd_docs/tasks/2026_10/2026_10_02_named-run-profiles/evidence/fiches uv run wave-local-ai-v2-validate <evidence>/quality.jsonl  # validate.log: checked 40 row(s), exit 0
```

| Record | Kind | Differing fields | Confounds | Result | Verdict |
| --- | --- | --- | --- | --- | --- |
| `comparisons/classification-support-routing@4.prompt_variant.44b9986b4ebf.json` | test | `constraint_grammar_hash`, `constraint_mechanism`, `prompt_variant_id` | none | McNemar exact, 9 both right, 11 both wrong, 0 discordant | not distinguishable |

Rows: `baseline` all `constraint_mechanism: none`, `constraint_grammar_hash:
null`; `constrained_output` all `gbnf` and
`302f90ebf245a4218f5a2bc510df860667e754d8cbe7dde5a8fb435ca5782e97`, the
SHA-256 of the registered grammar.

Share of baseline outputs outside the declared format: 0/20
(`baseline-format-replay.json`, produced by `baseline_format_replay.py`). A classification row does not carry the raw
answer, so the baseline requests were replayed through `local_client.complete_chat`
on the same build, model, launch flags (port moved to 8091), sampling and
thinking control; every raw answer equals its row's `predicted_label`.

The run wrote one fiche, `73ec536e...`, byte-identical to the one the
named-run-profiles evidence already tracks, so it is not duplicated here and
the rows validate against that registry.
