# Phase 1 evidence: the chat call path, probed live

Two probes against the installed llama-server, launched through the project's own
`server.running_server` with `qwen3-0.6b-q8`'s validated flags. The entry was chosen
for launch speed; nothing about it is special to the findings except where stated.

| Fact | Value |
| ---- | ----- |
| `build_info` (`/props`) | `b10537-bf0040e15` |
| Roster entry | `qwen3-0.6b-q8`, launched by `server.build_flags` unchanged |
| Model | `D:\ia\models\Qwen3-0.6B\Qwen3-0.6B-Q8_0.gguf`, `-ngl 99 -c 32768`, `--jinja` on |
| Suite item replayed | `billing-01`, expected label `billing`, 32-token cap |
| Sampling | `quality_cli.LOCAL_SAMPLING` verbatim (`seed` 20260821, `temperature` 0, `top_k` 0, `top_p` 1.0, `presence_penalty` 0) |
| `chat_template` length / sha256 | 4100 chars / `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361` |

## 1. The plan's Resources row holds, with one correction

Everything the plan asserted from the b10537 README is confirmed against the binary:

- `GET /props` returns `chat_template` (the model's Jinja source), `model_path`, `build_info`,
  and `chat_template_caps`. Full key set: `bos_token`, `build_info`, `chat_template`,
  `chat_template_caps`, `cors_proxy_enabled`, `default_generation_settings`, `endpoint_metrics`,
  `endpoint_props`, `endpoint_slots`, `eos_token`, `is_sleeping`, `media_marker`, `modalities`,
  `model_alias`, `model_ftype`, `model_path`, `total_slots`, `ui`, `ui_settings`.
- `POST /apply-template` takes `messages` and returns the rendered string under `prompt`,
  as the only key in the response.
- `POST /v1/chat/completions` returns `choices[0].message.content`, `choices[0].finish_reason`,
  and `usage.{prompt_tokens,completion_tokens,total_tokens}` (plus `prompt_tokens_details`).
  It echoes the rendered prompt nowhere, so `/apply-template` is required, as planned.
- Two identically-sampled requests returned byte-identical content. `top_k: 0` carries the
  same "disabled" meaning here that it does on `/completion`; the plan's risk on that is closed.
- The rendered prompt for `billing-01`:

  ```
  <|im_start|>user\nClassify the following support message into exactly one of these
  categories: account, billing, other, technical. Reply with only the single category
  word, nothing else.\n\nMessage: I was charged twice for my subscription this month,
  can you refund one?<|im_end|>\n<|im_start|>assistant\n
  ```

**Correction to the plan's Resources row.** The README states `/apply-template`'s only option is
`messages`. It is not true of the binary: `/apply-template` also honours `chat_template_kwargs`,
which matters below.

## 2. The finding that stops the phase

The endpoint switch alone does not make the model answer. It makes it think instead.

`Qwen3-0.6B`, `billing-01`, 32-token cap, chat endpoint, no other parameters:

```json
"message": {
  "role": "assistant",
  "content": "",
  "reasoning_content": "Okay, let's see. The user provided a message: \"I was charged twice for my subscription this month, can you refund one?\" And I"
},
"finish_reason": "length",
"usage": {"completion_tokens": 32, "prompt_tokens": 57, "total_tokens": 89}
```

`content` is the empty string. The whole 32-token cap went to `reasoning_content`, and the
answer never started. Scored by `score_item`, that is `failure_reason: "empty"` on every
item it happens to — a suite score of **0.00**, against the 0.45 the same model published on
the untemplated path.

The same item on `/completion` in the same server session, for comparison:

```
" I need to get a refund.\n\nResponse: other\n\nThe message is a request for a refund,
which is a form of payment. The message is not related"
```

`stop_type: "limit"`, `tokens_predicted: 32`, and `stopped_limit` absent from the body —
independently reconfirming the separate open truncation defect on this build.

So the defect's diagnosis is right about the cause (the raw endpoint asks for continuation)
and incomplete about the remedy: on a thinking-by-default model, the chat endpoint asks for
reasoning, and a 32-token cap is spent before the answer begins. Neither run measures
classification.

## 3. Four request-level controls, probed

All four are documented for b10537. Same item, same cap, same sampling, one variant per row.

| Variant | `finish_reason` | `completion_tokens` | `content` |
| ------- | --------------- | ------------------- | --------- |
| baseline (none of the four) | `length` | 32 | `""` |
| `chat_template_kwargs: {"enable_thinking": false}` | `stop` | **2** | `"technical"` |
| `reasoning_effort: "none"` | `stop` | **2** | `"technical"` |
| `reasoning_budget: 0` | `length` | 32 | `""` |
| `reasoning_format: "none"` | `length` | 32 | `"<think>\nOkay, let's see. The user provided a message: ..."` |

Read carefully:

- **`chat_template_kwargs` and `reasoning_effort` both work**, and produce the same two-token
  answer. The model answers `technical` where the expected label is `billing` — wrong, but a
  *scorable wrong answer*, which is what the whole comparison needs. Note `chat_template_caps`
  reports `"supports_reasoning_effort": false` for this template, yet `reasoning_effort: "none"`
  still suppressed thinking; the two switches are not independent evidence of each other.
- **`reasoning_budget: 0` did nothing** as a request parameter, despite the CLI documentation's
  "0 for immediate end". Do not rely on it.
- **`reasoning_format: "none"` is not a suppressor.** It only stops the server parsing the
  envelope out, moving `<think>` back into `content` — the exact string the translation suite
  already pays chrF precision for.

## 4. `/apply-template` honours the switch, so prompt parity is reachable

Passing the same `chat_template_kwargs` to `/apply-template` changes the rendered string:

```
plain      ... can you refund one?<|im_end|>\n<|im_start|>assistant\n
with kwargs ... can you refund one?<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n
```

The template prefills an empty reasoning block when thinking is disabled. This is the fact that
makes a templated row honest: whichever switch is chosen, the same argument can be sent to both
calls, so the row's stored `prompt` is the string the chat call actually rendered and not an
approximation of it. Had `/apply-template` ignored the kwargs, `prompt_capture: reconstructed`
would have been a claim about a string that was never sent.

## 5. The flagship, under the switch

`Qwen3.6-35B-A3B`, `billing-01`, 32-token cap, same build. It is a different model generation
with a different template, so its behaviour is not inferable from the 0.6B's.

| Variant | `finish_reason` | `completion_tokens` | `content` |
| ------- | --------------- | ------------------- | --------- |
| thinking allowed | `length` | 32 | `""` |
| `chat_template_kwargs: {"enable_thinking": false}` | `stop` | **2** | `"billing"` |

Its reasoning under the first variant opens `"Thinking Process:\n1.  **Analyze User Input:**\n   - Task: Classify a support message into exactly one category..."` and never reaches an answer.

Two things this settles:

- **The flagship needs the switch too.** Its raw-path obedience does not carry over: on the chat
  endpoint it thinks by default like the dense entries, and spends the whole cap doing it. The
  policy is not a dense-model workaround; it is what the endpoint requires from this whole family.
- **`billing` is the expected label.** The flagship answers `billing-01` correctly under the
  switch, where the 0.6B answers `technical`. That is the first evidence in this increment that
  the templated path measures classification rather than instruction-following.

`chat_template_caps` reports `"supports_reasoning_effort": false` on the flagship as it does on
the 0.6B, while `chat_template_kwargs` works on both. This is why `chat_template_kwargs` is the
chosen switch and `reasoning_effort` is not: the capability flag says the latter is unsupported,
and its apparent success on the 0.6B is not something to build a benchmark on.

## 6. The translation suite at its own cap

`Qwen3-0.6B`, item `en-fr-01`, 128-token cap — four times classification's, the case where a
thinking model might have finished on its own.

| Variant | `finish_reason` | `completion_tokens` | `content` |
| ------- | --------------- | ------------------- | --------- |
| thinking allowed | `length` | 128 | `""` |
| `enable_thinking: false` | `stop` | **30** | `"Réponse : Voulez-vous confirmer la date de livraison pour l'ordre que vous avez commandé la semaine dernière ?"` |

Reference on file: `"Pourriez-vous confirmer la date de livraison de la commande que nous avons passée la semaine dernière ?"`

The larger cap does not rescue it: the model spends all 128 tokens reasoning and still returns
nothing. So `thinking_policy: disabled` applies to the translation suite on its own evidence, not
by symmetry with classification.

One finding to carry into the record rather than fix here: the answer is prefixed `"Réponse : "`,
which is not in the reference and will cost chrF precision on this model. It is a different
artifact from the `<think>` envelope — a model habit, not a server or template effect — and
editing the prompt to suppress it is forbidden for the usual reason.

## 7. Where the empty envelope ends up

Under `enable_thinking: false` the rendered prompt ends `...<|im_start|>assistant\n<think>\n\n</think>\n\n`
on both the flagship and the 0.6B, and `content` comes back clean. The empty envelope moves into
the **prompt**, where it belongs and where it costs no score, instead of into the completion where
it currently costs the translation suite ~15 characters of chrF precision per item. That existing
tech-debt row is therefore improved by this increment on the local chat path, but it is not closed
by it: the raw `/completion` path still emits the envelope into the completion.

## 8. Not probed

- **The 1.7B and 4B entries.** Same vendor, same generation, same template family as the 0.6B,
  which was probed. They are covered by the phase 4 runs themselves.
