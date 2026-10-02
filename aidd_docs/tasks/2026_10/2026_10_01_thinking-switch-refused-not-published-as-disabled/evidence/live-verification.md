# Live verification: the shipped thinking control on qwen3-0.6b-q8

One load of the already-downloaded `Qwen3-0.6B-Q8_0.gguf` under the pinned
build, one call to `local_client.verify_thinking_control` with the entry as the
roster now declares it. No generation, no results store written, nothing
downloaded.

## Result

**Pass.** The two renders differ, so the declared control is honoured by the
template and a `thinking_policy: disabled` batch on this entry proceeds.

| Field | Value |
| ----- | ----- |
| Captured at | 2026-10-02T07:37:23+00:00 |
| Roster entry | `qwen3-0.6b-q8` |
| Model file | `Qwen3-0.6B/Qwen3-0.6B-Q8_0.gguf` |
| Model sha256 | `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031` <!-- pragma: allowlist secret --> |
| llama.cpp build (probed) | `b10537` |
| Chat template hash (`/props`) | `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361` <!-- pragma: allowlist secret --> |
| Declared `thinking_control` | `{"chat_template_kwargs": {"enable_thinking": false}}` |
| Probe message | `Reply with the single word: ready.` |
| Byte-identical | `false` |
| Verified | `true` |

## The two rendered strings

`/apply-template` with the control (JSON-escaped):

```json
"<|im_start|>user\nReply with the single word: ready.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
```

`/apply-template` without it:

```json
"<|im_start|>user\nReply with the single word: ready.<|im_end|>\n<|im_start|>assistant\n"
```

The difference is the empty `<think></think>` block Qwen3's template appends
when `enable_thinking` is false, the behaviour `local_client.render_prompt`'s
docstring already recorded for this build.

## How it was produced

A scratch script outside the repo, run from the worktree root:

```sh
LLAMA_SERVER_PATH=C:/Users/Anael/llama_cpp/llama-b10537-bin-win-cuda-12.4-x64/llama-server.exe \
SLM_MODELS_DIR=D:/ia/models \
QUALITY_PROVIDERS=local \
QUALITY_RESULTS_PATH=<this evidence folder>/unused-quality.jsonl \
RUNTIME_RESULTS_PATH=<this evidence folder>/unused-runtime.jsonl \
uv run python -X utf8 live_verify.py <out>
```

It resolves the entry from `aidd_docs/roster/models.json`, builds its flags with
`server.build_flags` (no `--n-cpu-moe`, dense), launches through
`server.running_server`, reads the template with `local_client.chat_template`,
and calls `local_client.verify_thinking_control(base_url, entry,
chat_template=..., timeout=60.0)`. The two results paths were set into this
folder as a guard; nothing wrote to them, and neither file exists.
