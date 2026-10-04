---
type: spike
status: resolved
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

### Live session on Ollama v0.35.1, 2026-10-04

Run by the execution spike `aidd_docs/backlog/spikes/are-the-three-ollama-spikes-live-captures-obtainable-in-one-ollama-v0-35-1-session.md` (runbook steps 8 and 12, 2026-10-04 00:21 to 00:22, reference laptop). Evidence folder `aidd_docs/tasks/2026_10/2026_10_04_local-spike-runs/ollama-v0.35.1/`, written `E/` below: the cited files copied from the capture folder `D:\ia\ollama-v0.35.1-captures`, under their original names. Sampling on every call: seed 20260821, temperature 0, `top_k` 0, `top_p` 1.0, `num_predict` 32, `think: false` unless stated. Declared format: the runbook used the suite's label set (`account`, `billing`, `other`, `technical`) because order 5 had not landed when it was written; order 5 is now `done`, and its classification format (`src/wave_local_ai_v2/prompt_variants.py`) is "exactly one label of the closed set ..., lowercase, with nothing before or after it" under the `gbnf` grammar `root ::= "account" | "billing" | "other" | "technical"`, the very grammar the GBNF attempt below sent.

| Attempt | Evidence | Result |
| ------- | -------- | ------ |
| GBNF grammar in a `grammar` field on `POST /api/chat` | `E/60-gbnf-field-attempt.body.json`, `E/60-gbnf-field-attempt.json`, `E/http-status.txt` | HTTP 200, no error or warning: the field is accepted. Output `technical`, `eval_count` 2, the same as the unconstrained call on the same item (`E/62-unconstrained-billing-01.json`). The capture cannot separate "dropped" from "applied" on its own, because the unconstrained answer already satisfies the grammar; with no such field in the API (desk row 1), the field is silently dropped. |
| `format: {"type":"string","enum":[the four labels]}` on ten items (four labels, EN, FR, DE) | `E/61-constrained-*.json` and their `.body.json` | All ten HTTP 200; every `message.content` is a JSON string in the label set (`"account"`, `"technical"`, `"other"`), and the constrained `billing-01` generation took 8 tokens against 2 unconstrained. |
| The same ten without `format` | `E/62-unconstrained-*.json` and their `.body.json` | All ten HTTP 200; every output a bare label in the set (`technical` nine times, `other` once). |
| Format check over the twenty | `E/A1-format-check.csv` | Constrained: 10 of 10 `json_string_in_label_set`, 0 of 10 `bare_label`. Unconstrained: 10 of 10 `bare_label`. (The file also lists the GBNF attempt, picked up by its `6*.json` glob.) The constraint changed two answers: `billing-01` `"account"` against `technical`, `account-01` `"account"` against `technical`. |
| `format` with `think: true` and 2048 tokens | `E/63-constrained-think-true-billing-01.json` and its `.body.json` | HTTP 200; the reasoning comes back in `message.thinking` and `message.content` is `"billing"`: the format applies after the thinking block. |

Desk assumptions checked: (1) order 5 now uses a GBNF grammar on bare labels, as assumed; (2) native mode holds (`E/30-serve-roster.log` line 268); (3) the enum constraint held on 11 of 11 constrained generations; the runner's debug log shows no grammar line, so the schema-to-grammar step itself is not observed.

## Outcome

- Result: resolved, the epic's "different mechanism" outcome. Ollama v0.35.1 takes no GBNF grammar per request: a `grammar` field is accepted with HTTP 200 and has no observable effect. Its one mechanism is `format` with a JSON Schema, here `{"type":"string","enum":["account","billing","other","technical"]}`, and it restricted every constrained generation (10 of 10 with `think: false`, 1 of 1 with `think: true`) to a JSON string in the label set. That is not order 5's declared classification format: every constrained Ollama output is quoted (`"billing"`), where order 5 declares a bare label with nothing before or after it. The cell therefore runs under a different mechanism (JSON Schema `format`, against llama.cpp's `gbnf`) and needs the per-family equivalent constraint in that mechanism, with the quoted JSON form declared. Decisive evidence: `aidd_docs/tasks/2026_10/2026_10_04_local-spike-runs/ollama-v0.35.1/A1-format-check.csv`.
- Confidence: high that `format` applies and kept every constrained output in the set; medium that it enforces, because the unconstrained outputs were already in the set, so no capture shows the constraint correcting an out-of-set answer. The changed shape and the two changed labels show it acts on decoding.
- Remaining uncertainty: enforcement against an out-of-set answer is not exercised; the row's mechanism spelling (for example `json_schema`) is order 8's to fix; whether constraining helps or hurts accuracy (two of ten labels changed here) is the campaign's measurement, not this spike's.

## Follow-up

- `aidd_docs/backlog/stories/the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason.md`: no longer blocked by this spike; the outcome is its "Different mechanism" branch. Still blocked through `depends_on` on order 7, which waits on order 6. Its other `depends_on`, order 5, is `done`.
