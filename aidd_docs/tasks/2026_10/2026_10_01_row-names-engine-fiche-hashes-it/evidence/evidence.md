# Evidence: every row names the engine that produced it, and the fiche hashes it

Re-run on 2026-10-02 on the final, rebased code, on the laptop (consumer NVIDIA laptop GPU, ~6 GB VRAM, Windows), pinned
build `llama-b10537-bin-win-cuda-12.4-x64`, roster entry `qwen3-0.6b-q8`, with every results
path and the fiche registry pointed into this folder (never `aidd_docs/results/`).

```sh
LLAMA_SERVER_PATH=C:/Users/Anael/llama_cpp/llama-b10537-bin-win-cuda-12.4-x64/llama-server.exe \
SLM_MODELS_DIR=D:/ia/models ROSTER_ENTRY_ID=qwen3-0.6b-q8 QUALITY_PROVIDERS=local \
RUNTIME_RESULTS_PATH=$E/runtime.jsonl QUALITY_RESULTS_PATH=$E/quality.jsonl \
FICHE_REGISTRY_DIR=$E/fiches uv run wave-local-ai-v2
```

## The runtime row and its fiche

`runtime-run.log`, last line:

```text
gen_tok_per_s=209.2 prompt_tok_per_s=3941.0 ttft_ms=376.8 repetitions_n=5 unreliable=False ...
```

`runtime.jsonl` (one row):

| Field | Value |
| ----- | ----- |
| `schema_version` | `22` |
| `engine_id` | `llama.cpp` |
| `engine_build` | `b10537` (live `--version` probe through the registry entry) |
| `fiche_hash` | `3b11dad518aa1a2aeaa0ec655d99968a03ca2e334acb5301d8574ccfbefef17b` |
| `verdict` | `not_comparable`, "no reference row shares this candidate's roster_entry_id" |

`fiches/3b11dad5....json`: `engine_id` `llama.cpp`, `engine_build` `b10537`,
`engine_config_hash` `fd916198e0d0991fc7492e609d056d7534e16804f644297c75eef819c32bea36`
(the same identity the earlier, pre-rebase run of this story wrote: same machine, build,
entry and normalised configuration hash to the same fiche).
Recomputed from the stored `flags`: the configuration hash and the fiche hash both match. The
normalised list the configuration hash is taken over has no path and no host or port:

```text
['-m', 'roster:qwen3-0.6b-q8', '-ngl', '99', '-c', '32768', '-fa', 'on', '-t', '8', '--jinja',
 '-np', '1', '--load-mode', 'auto', '--temp', '0.6', '--top-p', '0.95', '--top-k', '20',
 '--min-p', '0', '--presence-penalty', '1.5']
```

while the raw `flags` kept as evidence carry `D:\ia\models\Qwen3-0.6B\Qwen3-0.6B-Q8_0.gguf`
and `--host 127.0.0.1 --port 8080`.

## The gate refuses an unregistered engine

`gate-refusal.log`: the row above with `engine_id` set to `ollama`, through `append_row`:

```text
refused: row of kind 'runtime' names engine_id 'ollama', which is not a registered engine (registered: llama.cpp)
written: False
```

## The thinking switch, verified and recorded

`quality-run.log` (local-only classification batch, `thinking_policy: disabled`):

```text
thinking switch verified: engine=llama.cpp field=chat_template_kwargs renders_differ=True with=912d49fc... without=7386842a...
model=Qwen3-0.6B provider=local accuracy=0.45
```

All 20 quality rows carry `schema_version` `22`, `engine_id` `llama.cpp`, `engine_build`
`b10537`, `thinking_policy` `disabled` and the same `fiche_hash` as the runtime row (same
launch, same identity).

The two refusals the amended acceptance asks for are code paths llama.cpp does not take
(its switch renders a difference, and it declares one), so they are proven by tests rather
than this run: a declared switch whose two renders are byte-identical refuses the batch
before any generation (`tests/test_local_client.py`, `tests/test_quality_cli.py`, the done
thinking-switch story's tests, unchanged), and an engine declaring `none` refuses a
`disabled` batch whose entry declares an object control
(`test_an_engine_with_no_switch_refuses_an_object_control_under_disabled`) and is checked by
the candidate gate
(`test_an_object_control_on_an_engine_declaring_no_switch_is_refused`).

## Both stores verify

`validate.log`, `FICHE_REGISTRY_DIR=$E/fiches uv run wave-local-ai-v2-validate $E/runtime.jsonl $E/quality.jsonl`:

```text
checked 21 row(s)
```

exit `0`. The committed bundle (rows below schema `22`, projection `"1"` fiches) still
verifies: `tests/test_reference_bundle.py` passes with no bundle file edited.
