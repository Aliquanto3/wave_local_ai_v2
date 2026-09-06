---
type: defect
status: ready
source: aidd_docs/results/README.md
related_to:
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
  - aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
  - aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
order: 1
---

# Defect: The local quality path sends an untemplated prompt, so a chat-tuned model is scored on continuation

## Context

The quality benchmark's local subject path, `quality_cli._run_local_suite`, on both shipped
suites (`classification-support-routing`, `translation-business-short-form`), against
llama-server build `b10537`. Every cloud subject in the same comparison reaches its model
through a chat API — `POST /v1/chat/completions` for Mistral, `generateContent` for Google —
which applies that provider's chat structure around the item text. Observed on 2026-09-06
across the six quality batches of the dense-versus-MoE side-by-side.

## Expected

PRD Benchmark Methodology criterion 2 requires every row to store "the final prompt string as
rendered for that provider (after llama.cpp jinja templating or the cloud provider's chat
templating)". For a local subject that means the model receives the item text rendered through
its own chat template, the row stores that rendered string, and `prompt_template_id` names the
template that produced it instead of `none`. Rows measured under the untemplated path are
superseded by a re-run under a bumped suite and template version rather than edited in place,
so every published number stays the number the code that wrote it produced.

## Actual

`_run_local_suite` posts the item text verbatim — `json={"prompt": item["prompt"], ...}` to
`/completion` (`src/wave_local_ai_v2/quality_cli.py:717-725`) — and stamps the row
`prompt_template_id: "none"`, `prompt_template_hash: null` (`quality_cli.py:663-664`). No chat
template is applied, although all four roster entries launch the server with `--jinja`
(`aidd_docs/roster/models.json`), so the template is loaded and available on the running server.

Chat-tuned models therefore receive the item as text to continue, and the three dense Qwen3
entries continue it. On classification each of the three spends the full 32-token cap on every
one of the 20 items (`tokens_out_total` 640 on all three rows) and lands at 0.45 (`Qwen3-4B`),
0.45 (`Qwen3-0.6B`) and 0.25 (`Qwen3-1.7B`) accuracy. On translation they score 0.2005, 0.1867
and 0.1742 chrF while demonstrably producing a correct target-language sentence mid-completion,
after first continuing the source text and then reviewing their own work in English. The MoE
flagship survives the same path — it opens a `<think>` envelope and then obeys — at the
~15-character chrF cost already recorded separately.

The rows are internally truthful: `prompt_provenance.RAW_ENDPOINTS` makes `template_id: "none"`
legitimate for `/completion`, and the writer gate accepts the pair. The mismatch is not in a
row's self-description. It is that the local and cloud subjects of one published comparison
were not sent the same kind of input.

## Reproduction

1. `uv run wave-local-ai-v2-quality` with a chat-tuned local roster entry selected
   (`qwen3-4b-q4km`, `qwen3-1.7b-q8` or `qwen3-0.6b-q8`), on either shipped suite.
2. Read the resulting row: `endpoint` is `/completion`, `prompt_template_id` is `none`,
   `prompt_template_hash` is null, and `prompt` is the item text with no chat structure
   around it.
3. Read the same batch's `tokens_out_total`: it equals the item count times the suite's output
   cap, so the model never stopped on its own on any item.
4. Replay one item directly against `/completion` at the same cap to read the continuation in
   full; the README section under Evidence quotes one such reply for `Qwen3-0.6B`, item
   `billing-02`.

## Impact

The consultant reading the dense-versus-MoE side-by-side, and any client engineer auditing a
local quality row against a cloud one. Every local quality number this project has published
measures instruction-following on a raw completion endpoint rather than the capability its
suite names, while the cloud numbers printed beside it do not — so both the local-versus-cloud
gap and the dense-versus-MoE gap are unbounded by the rows that state them. The dense rows are
where it is decisive: 0.25-0.45 accuracy and ~0.19 chrF read as "these models cannot classify
or translate", which their own completions refute. The flagship's rows are affected in the same
direction and far less, so the per-use-case model recommendation the suite epic exists to
produce currently rests on a comparison the harness biases against its own local subjects.

Bounded to local quality rows. Runtime rows are unaffected: they measure throughput on a fixed
prompt, not an answer. No published score is wrong about what it measured; each is wrong about
what a reader takes it to measure.

Resolving this changes what every existing local quality row means, `PROMPT_SET_HASH` included,
so which templated call path is used is a suite-level decision and is not settled here. The
same migration sits inside `no-use-case-is-silently-absent`'s Boundaries, for tool-call
transcript capture; the two need sequencing against each other.

Publishing both readings side by side — one suite version with thinking allowed and one with it
disabled, so the cost of the policy is itself a published number — is rejected for now on run
cost (it doubles every local batch) and stays available as a later increment if a model
recommendation turns on it.

## Evidence

- `aidd_docs/results/README.md`, "What the dense rows are actually measuring" — the verbatim
  `Qwen3-4B` completion for item `fr-de-03`, the `Qwen3-0.6B` probe reply for `billing-02`, and
  the `tokens_out_total` 640 figure for all three dense classification batches.
- `aidd_docs/results/README.md`, "Dense versus MoE, side by side (2026-09-06)" — the two scored
  tables. Classification `run_id`s `d7f08b1a`, `c836bacc`, `9dd45420`; translation `350cac2f`,
  `c370c862`, `80eec0cd`.
- `src/wave_local_ai_v2/quality_cli.py:717-725` — the raw prompt POST; `:663-664` — the
  `none` / `null` stamp.
- `src/wave_local_ai_v2/prompt_provenance.py:32-34` — `/completion` is the one endpoint for
  which `none` is a legitimate template id.
- `aidd_docs/backlog/tech-debt.md`, the 2026-09-06 `tiny-dense-models-alongside-moe` row on
  `_run_local_suite` — the same observation, recorded before this Defect existed.
- `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md:37` — criterion 2.

## Verification

A local quality row carries a `prompt_template_id` other than `none`, a non-null
`prompt_template_hash`, and a `prompt` holding the chat-rendered string rather than the bare
item text. That row's suite and template version are above the version carried by the rows
listed under Evidence, and those rows still read at their own version — superseded, not edited.
On the re-run, a dense entry's `tokens_out_total` falls below item count times cap, showing the
model stopped on its own.

## Cancellation

n/a — not cancelled.
