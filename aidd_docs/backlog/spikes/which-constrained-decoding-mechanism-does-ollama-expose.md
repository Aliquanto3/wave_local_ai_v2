---
type: spike
status: blocked
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parents:
  - aidd_docs/backlog/stories/the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md
---

# Spike: Which constrained-decoding mechanism does Ollama expose

## Question

Does Ollama accept a GBNF grammar per request, a JSON-schema-shaped output constraint as a substitute, or no output constraint at all, and does the mechanism it does accept actually restrict generated tokens on the `constrained_output` variant's declared output formats?

## Decision

Which of the epic's three pre-handled outcomes applies to the `constrained_output` x Ollama cell (order 8): the same mechanism as llama.cpp (a real comparison), a different mechanism (recorded per row and published as a comparison of two mechanisms), or none (the cell is dropped with its reason recorded).

## Bounds

- Evidence needed: against a running pinned Ollama instance (the one spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol` installs), for `qwen3-0.6b-q8`: the request parameter tried for each candidate mechanism and the captured response; whether a GBNF grammar is accepted, ignored or rejected; whether a schema-shaped constraint is accepted and how it is expressed; for each accepted mechanism, ten generations on the classification suite's output format with the constraint set and ten without, showing whether any constrained output falls outside the declared format. The variant's declared format per task family comes from order 5's registry entry; if order 5 has not landed, the classification label set is used and that substitution is recorded.
- Stop when: one mechanism is shown to restrict output to the declared format on every constrained generation, with its spelling recorded, or every candidate is shown to be absent or not enforcing, which is recorded as "none" with the attempts.

## Investigation

Desk research only, on 2026-10-02: no Ollama binary was executed. Source citations are to tag `v0.35.1` (commit `b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce`, latest stable on 2026-10-02) of `github.com/ollama/ollama`, read at `https://github.com/ollama/ollama/blob/v0.35.1/<path>` (read 2026-10-02). Native-mode routing of the imported roster GGUF is recorded in spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md`.

| Attempt | Evidence | Result |
| ------- | -------- | ------ |
| Searched the public API for a grammar field | `api/types.go`, `docs/api.md`, `docs/capabilities/structured-outputs.mdx`, `server/routes.go` (grep `grammar`, no match) | No request field accepts a GBNF grammar. The only output constraint is `format`: the string `"json"` or a JSON Schema object (`docs/api.md` lines 52, 63-67; structured-outputs doc). Any other value is rejected with `invalid format ... expected "json" or a valid JSON Schema object` (`llm/llama_server.go` lines 2415-2443, 1678-1690). |
| Read how `format` reaches the sampler on the native chat path | `llm/llama_server.go` header (lines 1-15), `llamaServerChatResponseFormat` (lines 2415-2443), `llamaServerChatRequest` (lines 2240-2295) | On a native-mode model, `/api/chat` `format: <schema>` becomes `response_format: {"type":"json_schema","json_schema":{"name":"schema","schema":<schema>}}` and `format: "json"` becomes `{"type":"json_object"}` on the bundled llama.cpp `b11232` `llama-server` `/v1/chat/completions`. llama-server converts the schema to a GBNF grammar and constrains sampling with it: the mechanism is llama.cpp grammar-constrained sampling, entered through a JSON Schema. |
| Read the Go-rendered `/completion` path | `llm/llama_server.go` `grammarJSON` (lines 54-75), completion request (lines 1407-1424, 1678-1705), `schemaGrammar` (lines 1430-1505); `llm/gbnf.go` `thinkingGrammar` | On `/completion` a schema goes in llama-server's `json_schema` field and `"json"` as Ollama's built-in GBNF `grammarJSON`. When thinking is on, Ollama asks llama-server for the schema's GBNF and wraps it so the text before the thinking close is free and the format applies after it. Ollama builds GBNF internally but never takes one from the caller. |
| Read the documented guarantee | `docs/api.md` (line 246); `docs/capabilities/structured-outputs.mdx` | With `"json"` the output "will always be a well-formed JSON object"; a schema makes "the model ... generate a response that matches the schema". Enforcement on the variant's own format is not shown by docs; a JSON-schema constraint can only produce JSON, so a bare-label format cannot be expressed: a label set becomes e.g. `{"type":"string","enum":[...]}` (output `"label"` with quotes) or an object with an enum property. |

Evidence, decisions and assumptions:

- Evidence: the Result column above.
- Decisions already taken: the epic's three pre-handled outcomes for the `constrained_output` x Ollama cell (same mechanism, a different mechanism recorded per row, or none) (`aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md`).
- Assumptions: (1) the `constrained_output` variant on llama.cpp will pass a GBNF grammar (`grammar` field) for the declared output format; order 5 has not landed (`src/wave_local_ai_v2/prompt_variants.py` holds `baseline` only), so the classification label set stands in for the declared format, per the Bounds; (2) the imported Qwen3 GGUF runs in native mode; (3) llama-server b11232's schema-to-grammar conversion enforces an `enum` exactly.

## Outcome

- Result: blocked on the live generations the Bounds require. Desk research settles the candidates: GBNF per request is absent from Ollama's API (no field, so not even "ignored": a caller cannot express it); the only mechanism is `format` with a JSON Schema (or `"json"`), compiled by the bundled llama-server into a grammar. If order 5's llama.cpp variant uses GBNF on bare labels, the Ollama cell is the epic's "different mechanism" outcome: the row should record the mechanism as `json_schema_format` (Ollama `format`, schema compiled to GBNF by llama-server b11232) beside llama.cpp's `gbnf_grammar`, and the declared output format differs (a JSON string or object instead of a bare label), which the scorer must parse. Whether it restricts every constrained generation is the live question.
- Confidence: high on what the API accepts and how it is routed (pinned source); none yet on enforcement.
- Remaining uncertainty: the twenty generations per mechanism and their check. Commands, with the Ollama session of the runtime spike running on `127.0.0.1:11500` and model `wla-qwen3-0.6b-q8`:

```powershell
# GBNF attempt: no such field; record whether the request is rejected or the field silently dropped, and whether the output is constrained
curl.exe -s http://127.0.0.1:11500/api/chat -d '{"model":"wla-qwen3-0.6b-q8","stream":false,"think":false,"grammar":"root ::= \"positive\" | \"negative\"","messages":[{"role":"user","content":"<item prompt>"}]}'
# Schema constraint, ten generations on ten classification items, then the same ten without "format"
curl.exe -s http://127.0.0.1:11500/api/chat -d '{"model":"wla-qwen3-0.6b-q8","stream":false,"think":false,"keep_alive":-1,"format":{"type":"string","enum":[<classification label set>]},"options":{"seed":<suite seed>,"temperature":<suite>,"num_predict":<suite max_output_tokens>},"messages":[{"role":"user","content":"<item prompt>"}]}'
```

Record, per generation, `message.content` and whether it parses as JSON and its value is in the label set; repeat once with `think: true` to see the format apply after the thinking block.

## Follow-up

- `aidd_docs/backlog/stories/the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md`: still blocked by this spike, now on the live generations only (and on order 5 for the declared format). `Blocked:` should read: spike `which-constrained-decoding-mechanism-does-ollama-expose.md` (live: ten constrained and ten unconstrained generations with `format` as a JSON Schema enum on Ollama v0.35.1, checked against the classification label set). Desk answer the story can already use: GBNF is not exposed; the only candidate is `format` (JSON Schema), so the cell is at best the "different mechanism" outcome, with the declared output format expressed as JSON.
