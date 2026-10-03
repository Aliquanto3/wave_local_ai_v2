---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Streamed chat proxy

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/playground.py    ✏️ chat body (thinking_kwargs), SSE to NDJSON deltas, caps
├── src/wave_local_ai_v2/service.py       ✏️ POST /api/playground/chat as a StreamingResponse
└── tests/test_playground.py              ✏️ stub llama-server: body shape, policy spelling, over-cap refused, no timings forwarded
```

## Test Scope

```mermaid
journey
  section Setup
    stub HTTP chat endpoint streaming SSE chunks => fixture: 5: system
  section Happy path
    POST chat with prompt and policy => NDJSON deltas then a final event naming the policy: 5: api
  section Edge case - over cap
    prompt longer than the cap => POST chat => 422, no request sent: 1: api
  section Edge case - unknown policy
    policy outside the two values => POST chat => 422: 1: api
  section Edge case - no model
    nothing loaded => POST chat => 409: 1: api
```

## Tasks to do

### `1)` Proxy

1. Validate prompt (non-empty string, within the cap) and policy (`row_contract.THINKING_POLICIES`).
2. Body `{"messages": [user content], "stream": true, "max_tokens": cap, **thinking_kwargs}` to the engine's chat endpoint.
3. Parse `data:` lines; yield `{"delta"}` / `{"reasoning"}`; then `{"final": {thinking_policy, finish_reason}}`; a transport error ends with `{"final": {"error"}}`.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | The stub receives the typed text only as message content, the entry's thinking spelling under `disabled` and nothing under `allowed`; no timing value reaches the browser |
