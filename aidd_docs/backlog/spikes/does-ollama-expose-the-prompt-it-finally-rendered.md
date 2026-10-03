---
type: spike
status: blocked
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parents:
  - aidd_docs/backlog/stories/ollama-quality-rows-pass-a-prompt-parity-gate-or-publish-as-observations.md
---

# Spike: Does Ollama expose the prompt it finally rendered

## Question

Can the harness obtain, from a running Ollama instance, the exact string the model received after Ollama's own chat templating, by a documented or observable path, so that it can be published under Methodology 2 and compared byte for byte with llama.cpp's `/apply-template` output for the same model and item?

## Decision

Whether Ollama's quality rows (order 7) can carry a rendered prompt at all, and with which `prompt_capture` value: `captured` (the engine returns what it received), `reconstructed` (rendered by a separate call on the same template, as llama.cpp's path does today), or an explicit absence. The answer decides whether cross-engine quality cells can be paired comparisons or only observations, under the epic's prompt-parity decision. It also decides how the Ollama thinking switch is verified: by comparing a render with the switch against one without it, or not at all.

## Bounds

- Evidence needed: against a running pinned Ollama instance (the same one spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol` installs), for `qwen3-0.6b-q8` and two classification items, one EN and one FR: every candidate path tried and its captured output (a render or template endpoint if one exists, the template the server reports for the model, a raw or pre-templated request mode, server debug logging), and for each the string obtained; the same items rendered by llama.cpp's `/apply-template` on the same GGUF; the byte-level diff between the two; whether the path still reflects the thinking switch when it is set. A path that requires logging the prompt to a file is recorded with where that file lives, because rows and logs have different retention rules.
- Stop when: one path is shown to return the rendered string with its capture kind named, and the diff against llama.cpp is recorded, or every candidate path is shown to fail, which is recorded as "no rendered prompt available" with the attempts.

## Investigation

Desk research only, on 2026-10-02: no Ollama binary was executed. Source citations are to tag `v0.35.1` (commit `b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce`, latest stable on 2026-10-02) of `github.com/ollama/ollama`, read at `https://github.com/ollama/ollama/blob/v0.35.1/<path>` (read 2026-10-02). How the imported roster GGUF is routed (native mode, rendered by the bundled llama.cpp `b11232` `llama-server` from the GGUF's own jinja template) is recorded in spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`.

| Attempt | Evidence | Result |
| ------- | -------- | ------ |
| Searched the API types for a field returning the rendered prompt | `api/types.go` (lines 119-121, 168-170, 541-553, 947) | `ChatRequest` and `GenerateRequest` accept `_debug_render_only` (bool, documented in source as "a debug option that ... returns the rendered template instead of calling the model"); `ChatResponse` and `GenerateResponse` carry `_debug_info.rendered_template` and `image_count`. No other response field carries a prompt. The field is absent from `docs/api.md` and the other docs at the tag: undocumented, underscore-prefixed, so not a stable contract. |
| Read where `_debug_info` is filled | `server/routes.go` (lines 659-670 generate, 2911-2921 Go-rendered chat, 3100-3120 native chat) | `_debug_info` is set only in the `_debug_render_only` branches, which return before any generation. A real generation never returns the string the model received: no `captured` path exists. |
| Read what the native-mode render call does | `server/routes.go` `handleNativeChat` (lines 3076-3120); `llm/llama_server.go` `ApplyChatTemplate` (lines 1944-1988), `llamaServerChatRequest` (lines 2240-2295) | For a native-mode model, `_debug_render_only` builds the same request body the generation would send (messages, `chat_template_kwargs` from `think`, tools, format) and posts it to the bundled `llama-server`'s own `/apply-template`, returning its `prompt`. The generation itself posts that body to `/v1/chat/completions`, which renders inside llama-server. The render is therefore a separate call on the same template and the same server process: `prompt_capture: reconstructed`, the same kind the llama.cpp rows carry today. |
| Read the `/api/generate` native path | `server/routes.go` `GenerateHandler` (lines 585-670) | On `/api/generate` (non-raw) a native-mode model's prompt is rendered by `ApplyChatTemplate` and the resulting string is what is sent to `/completion`; `_debug_render_only` returns that same string. |
| Read the thinking switch on the render path | `llm/llama_server.go` `llamaServerChatTemplateKwargs` (lines 2296-2310) | `think: false` / `true` becomes `chat_template_kwargs: {"enable_thinking": false/true}` in the body sent to both `/apply-template` and `/v1/chat/completions`; Qwen3's template renders differently under the two values, so the switch can be verified by comparing two renders. |
| Read the raw (pre-templated) mode | `docs/api.md` (lines 57, 331); `llm/llama_server.go` `completionPrompt` (lines 246-257) | `/api/generate` with `raw: true` sends the caller's string without templating, so the harness could send llama.cpp's `/apply-template` output verbatim. Ollama strips one leading BOS text from it when the tokenizer adds BOS itself. This bypasses Ollama's templating: parity by construction, at the cost of not measuring the prompt an Ollama user's chat call would get, and the thinking switch is then whatever the string contains. |
| Read `/api/show` and the debug logging options | `api/types.go` `ShowResponse` (lines 742-761); `envconfig/config.go` (lines 199-220, 315-316); `docs/windows.mdx` (lines 66-69) | `/api/show` returns `template` (the Go TEMPLATE, expected empty for a native-mode import), `renderer`, `parser`, `model_info`. `OLLAMA_DEBUG_LOG_REQUESTS` logs inference request bodies and replay curl commands to a temp directory (request JSON, not the rendered prompt). `OLLAMA_DEBUG=1` raises log level; server logs go to `%LOCALAPPDATA%\Ollama\server.log` for the app or stderr for `ollama serve`. Whether either log holds the rendered prompt is not shown by source. |

Evidence, decisions and assumptions:

- Evidence: the Result column above.
- Decisions already taken: the epic's decision "Prompt parity across engines is a gate, not an assumption" and its current llama.cpp path (`/apply-template`, `prompt_capture: reconstructed`) (`aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md`).
- Assumptions: (1) the imported Qwen3 GGUF runs in native mode (verified live by `/api/show` returning empty `template`, `renderer`, `parser`); (2) llama-server's `/apply-template` and `/v1/chat/completions` render one body identically inside the same process, which is how llama.cpp's own reconstructed path is already treated; (3) the b11232 jinja engine may render differently from b10537 on the same template, which only the byte diff shows.

## Outcome

- Result: blocked on the live render and diff the Bounds require. Desk research shows a candidate path: `_debug_render_only: true` on `POST /api/chat`, returning `_debug_info.rendered_template` from the bundled llama-server's `/apply-template` on the same body, i.e. `prompt_capture: reconstructed`; no `captured` path exists (no generation response carries the prompt). The path reflects the thinking switch through `chat_template_kwargs.enable_thinking`. It is undocumented and underscore-prefixed, so the engine entry must pin the Ollama version it was verified on. Fallback paths: `raw: true` pre-templated mode (parity by construction, not Ollama's own rendering), or "no rendered prompt available".
- Confidence: high that no `captured` path exists and that `_debug_render_only` routes to `/apply-template` (read in pinned source); unknown whether its output is byte-identical to llama.cpp b10537's `/apply-template` for the same items.
- Remaining uncertainty: the captured strings and the byte diff. Commands, with the Ollama session of the runtime spike running on `127.0.0.1:11500` and model `wla-qwen3-0.6b-q8`:

```powershell
# Ollama render, per item (EN item, FR item) and per think value (false, true)
curl.exe -s http://127.0.0.1:11500/api/chat -d '{"model":"wla-qwen3-0.6b-q8","_debug_render_only":true,"think":false,"messages":[{"role":"user","content":"<item prompt>"}]}' -o ollama-<item>-think-false.json
# llama.cpp b10537 render of the same GGUF and body (after the Ollama session is stopped)
C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe -m D:\ia\models\Qwen3-0.6B\Qwen3-0.6B-Q8_0.gguf --jinja -c 32768 --port 8080
curl.exe -s http://127.0.0.1:8080/apply-template -d '{"messages":[{"role":"user","content":"<item prompt>"}],"chat_template_kwargs":{"enable_thinking":false}}' -o llamacpp-<item>-think-false.json
```

Compare `_debug_info.rendered_template` with `prompt` byte for byte (UTF-8, first differing offset), for the two items and both think values; also confirm that the `false` and `true` renders differ on each engine; record `/api/show` `template`/`renderer`/`parser`. Items: the first EN and the first FR item of the classification suite.

## Follow-up

- `aidd_docs/backlog/stories/ollama-quality-rows-pass-a-prompt-parity-gate-or-publish-as-observations.md`: still blocked by this spike, now on the live render and diff only. `Blocked:` should read: spike `does-ollama-expose-the-prompt-it-finally-rendered.md` (live `_debug_render_only` renders on Ollama v0.35.1 for one EN and one FR item, think on and off, byte diff against llama.cpp b10537 `/apply-template`). Desk answer the story can already use: Ollama rows can carry `prompt_capture: reconstructed` at most, never `captured`; the thinking switch is verifiable by render comparison if the path works. If the diff shows divergence, the story's acceptance already handles it (cells published as observations).
- Execution vehicle: spike `aidd_docs/backlog/spikes/are-the-three-ollama-spikes-live-captures-obtainable-in-one-ollama-v0-35-1-session.md` runs this spike's live session (runbook with every command and request value, prerequisites, capture map); record its captures here.
