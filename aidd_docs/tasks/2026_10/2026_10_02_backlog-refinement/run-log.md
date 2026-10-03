# Run log: backlog refinement run (2026-10-02)

Branch `docs/refine-proposed-items-2026-10-02` (worktree `wave_local_ai_v2-refine`), cut from `main` at `c68b23e`. Unattended; runs beside the implementation session on `feat/night-run-2026-10-02`. Desk research only: no model run, no install, no download, no account, no provider call.

## Final report

Written 2026-10-03 at the end of the run. Branch `docs/refine-proposed-items-2026-10-02`, cut from `main` at `c68b23e`; 23 commits before this report, nothing pushed, no merge, no PR, no branch deleted. Nothing was run, installed or downloaded, no account was created and no provider was called; every spike is desk research with dated URLs. No permission-classifier refusal occurred. Agents stalled six times on the stream watchdog and were resumed with smaller reads; one hook run hung once (a stray interactive `python` started by a shell heredoc, stopped, its output file deleted). Before every commit: `uv run pre-commit run --files ...` (or the commit hook) and the UTF-8 secrets hook on the staged files; two spike files first failed the secrets hook (an example `revision` sha and placeholder API-key literals) and were reworded, never baselined.

### Spikes (13)

| Spike | Status | What remains |
| --- | --- | --- |
| is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms | blocked | 10 live calls with a paid DeepSeek key (listed in the spike); Q102 (no dated id), Q103 (training opt-out) |
| is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms | blocked | 8 live calls with a paid Z.ai key; Q102 (release ids only, no documented model list) |
| which-public-classification-benchmark-seeds-the-publication-suite-and-on-what-terms | blocked | Q105 only (rung settled: permissive; MInDS-14 or MASSIVE 1.1) |
| which-public-translation-benchmark-seeds-the-publication-suite-and-on-what-terms | blocked | Q106 only (WMT24++ found; accepting Google's Apache-2.0 label over WMT24 research-only sources is the owner's risk) |
| which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them | blocked | 8 live gate loads under b10537 (`uv run wave-local-ai-v2-candidate-gate --candidate <entry>.json`, one per architecture); Q107, Q108 |
| does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it | blocked | live probes P1-P5 per roster entry with `-lv 5`, attribution runs, one framework driver run on a throwaway branch; Q109, Q110 |
| which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms | blocked | 9 live calls with a paid OpenAI key; Q102, Q104 |
| may-the-model-outputs-in-the-published-rows-be-redistributed-and-on-what-terms | resolved | nothing (permitted everywhere, with an AI-generated marking); follow-up task created and `ready`; Q111 asks the owner to update the bundle epic's assumption row |
| which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream | blocked | live SearXNG and Mojeek captures (install and provider call); Mojeek account (owner act); Q112, Q113, Q114 |
| can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol | blocked | one live session on Ollama v0.35.1 (commands in the spike) |
| does-ollama-expose-the-prompt-it-finally-rendered | blocked | live `_debug_render_only` renders, byte-diffed against b10537 `/apply-template` (same session) |
| which-constrained-decoding-mechanism-does-ollama-expose | blocked | ten constrained and ten unconstrained live generations (same session) |
| which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement | blocked | one live CPU measurement in an isolated environment (install and download); Q115 |

### Proposed stories (29): none moved to `ready`

Every one still waits on a `blocked` spike, an unanswered owner question of this run or a `depends_on` chain that does; each `Blocked:` line now names exactly that, and each "Current state" was re-verified against `main`. Contrary to the run brief, `the-campaign-answers-whether-each-variant-helps-or-hurts-a-small-model` and `the-threshold-review-is-written-from-the-first-publication-run` always had a `Blocked:` line; both block through their `depends_on` (the threshold review now also on Q120).

| Story | Still blocked by |
| --- | --- |
| a-glm-judge-answers-through-z-ai-under-the-pinning-discipline | GLM spike live calls, Q102 |
| a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline | DeepSeek spike live calls, Q102, Q103 |
| glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again | orders 8 and 9 |
| a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score | Luna spike live calls, Q102, Q116, order 10 |
| the-judged-probe-runs-both-paths-in-three-languages | order 10 |
| judge-scoring-with-inter-judge-agreement-proves-judged-machinery | judge order 10 and the judged probe |
| the-rewriting-suite-scores-dense-and-moe-side-by-side-under-the-judge-pair | order 2 |
| a-judged-re-run-receives-a-reproduction-verdict-that-separates-the-subject-from-its-judges | Q102, order 2, the `ready` cloud-subject re-run story |
| a-publication-level-classification-suite-stands-beside-the-hand-written-one | Q105 only |
| a-publication-level-translation-suite-stands-beside-the-hand-written-one | Q106, Q118, Q119 |
| the-threshold-review-is-written-from-the-first-publication-run | orders 7 and 8, Q120 |
| a-drawn-item-reaches-the-download-under-its-own-terms-or-as-a-visible-hole | Q106, the two publication suites, the `ready` archive story |
| document-comparison-is-scored-against-a-reference-and-two-judges | the judge chain |
| a-rag-answer-is-scored-over-a-local-corpus-under-a-named-harness | Q109, Q110, the judge chain |
| a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge | tool-call spike live probes |
| the-same-tool-calling-items-run-under-each-compared-harness | tool-call spike framework run, Q109, Q110, order 6 |
| an-agentic-plan-is-scored-against-its-authored-step-set | tool-call spike runs, orders 6 and 7 |
| a-web-research-score-recomputes-offline-from-its-archived-search-responses | SearXNG live capture, Q113, Q114, the judge chain |
| two-search-tools-answer-the-same-queries-and-each-row-names-its-tool | Q112, Q113, Mojeek live capture, order 9 |
| ollama-runtime-rows-stand-beside-llama-cpp-rows-on-the-same-artifact | Ollama runtime spike live session |
| ollama-quality-rows-pass-a-prompt-parity-gate-or-publish-as-observations | rendered-prompt spike live session, Q117, order 6 |
| the-constrained-variant-on-the-comparator-names-its-mechanism-or-is-dropped-with-its-reason | constrained-decoding spike live run, order 7 |
| the-input-compression-variant-records-its-compressor-as-a-step-of-its-own | compressor spike live measurement, Q115 |
| what-a-default-ollama-install-costs-is-published-as-its-own-figure | Ollama runtime spike live session, order 6 |
| the-campaign-answers-whether-each-variant-helps-or-hurts-a-small-model | orders 8 and 9 |
| the-half-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder | GGUF spike live loads, Q107, Q108 |
| the-two-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder | GGUF spike live loads, Q107, Q108 |
| the-four-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder | GGUF spike live loads, Q108 |
| the-top-class-spans-two-families-with-dense-and-moe-or-says-why-not | GGUF spike live loads, Q108 |

Cheapest unlocks: Q105 alone readies the classification publication suite; Q108 (a) alone readies the four-billion and top-class stories (their first gate runs are the spike's remaining loads); Q107 plus Q108 ready the two smaller classes.

### Credible-sessions epic: stories created

- `each-client-showing-is-logged-as-a-record-someone-who-was-not-there-can-read-back` (order 1, `ready`)
- `a-challenge-no-named-evidence-resolved-is-sustained-and-points-at-its-follow-up-item` (order 2, `ready`)
- `each-release-reads-its-credibility-verdict-from-its-records-in-its-changelog-entry` (order 3, `proposed`: Q100)
- `the-first-real-client-session-is-logged-the-same-day-and-read-back-by-someone-who-was-not-there` (order 4, `proposed`: through order 3; operator)

The epic stays `proposed` (Q101).

### Owner questions

23, Q100 to Q122, in `owner-questions.md`. Q102 (how Methodology 12 pins a judge provider with no dated id) is the widest: it gates every judged story.

### Newly ready, in dependency order

1. `aidd_docs/backlog/tasks/the-model-output-fields-cite-the-terms-they-were-checked-against-and-carry-the-ai-generated-notice.md`: code-only (licence text, README, one test).
2. `aidd_docs/backlog/stories/each-client-showing-is-logged-as-a-record-someone-who-was-not-there-can-read-back.md`: code-only (its evidence walk needs a second reader; a separate agent session counts). Note: its epic is still `proposed` (Q101).
3. `aidd_docs/backlog/stories/a-challenge-no-named-evidence-resolved-is-sustained-and-points-at-its-follow-up-item.md`: code-only, after 2.

No newly ready item needs a local run, a paid key or an operator.


## Setup

- `git worktree add ../wave_local_ai_v2-refine -b docs/refine-proposed-items-2026-10-02 main` (main at `c68b23e`, equal to `origin/main`). `uv sync` done. `pre-commit install` not run (shared hooks).
- Read: `aidd_docs/memory/*` (not `external/`), the PRD, the 2026-10-01 slicing run log and owner questions (Q1-Q76, all answered), the 2026-10-01 implementation run log's "Code against the backlog".
- Spike status convention: a spike concluded from evidence is `resolved`; one that still needs a live run or an owner choice keeps its findings and moves to `blocked` (the spike lifecycle's non-terminal state for a named dependency), with what remains written in its Outcome. Either way a `blocked` spike still blocks its parents.

## Step 1: spikes

| Spike | Status | What remains | Commit |
| --- | --- | --- | --- |
| is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms | blocked | Live calls with a paid key (10 listed in the spike); Q102 (no dated id: names repointed in place), Q103 (training opt-out). Terms are compatible with the egress non-goal (training on inputs unless opted out, PRC storage, no fixed retention). | d842df4 |
| is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms | blocked | Live calls with a paid Z.ai key (8 listed in the spike); Q102 (release ids only, e.g. `glm-5.2`, and no documented model-list endpoint). `glm-5.3` excluded (forced thinking). Terms are compatible with the egress non-goal (no training on API content without consent, processed in Singapore, not stored). | 81b6634 |
| which-public-classification-benchmark-seeds-the-publication-suite-and-on-what-terms | blocked | Rung settled: permissive (both qualifying sources are CC BY 4.0). Remains Q105: MInDS-14 (support-routing intents, recommended) or MASSIVE 1.1 (the epic's lead, voice-assistant scenarios). SIB-200 and MTOP are share-alike; Amazon Reviews Multi is no-republish. | 56ad9da |
| which-public-translation-benchmark-seeds-the-publication-suite-and-on-what-terms | blocked | Source found: WMT24++ (`google/wmt24pp`, Apache-2.0, EN->FR, FR->DE, DE->EN by joining two pairs on `segment_id`). The agent marked it `resolved`; set to `blocked` here because the permissive rung rests on Google's label over WMT24 source text released "for research purposes" only, a risk for the owner: Q106. FLORES+ is share-alike and gated against re-hosting. Noted, not asked: the PRD open question's "republishes ... under CC-BY 4.0" wording does not fit an Apache-2.0 item, which keeps its own licence per Methodology 5. | 570bb17 |
| which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them | blocked | Every shortlisted family has a GGUF pinned by commit sha per class; all eight architectures are in b10537's `src/llama-arch.cpp`. MoE found below the top class (Granite 3.1 1B-A400M, 3B-A800M, Phi-tiny-MoE). Remains: one live gate load per architecture (`uv run wave-local-ai-v2-candidate-gate --candidate <entry>.json`, 8 runs), Q107 (which LFM2 models), Q108 (fold those loads into the class stories). | 939b311 |
| does-each-roster-model-emit-parseable-tool-calls-through-llama-server-and-can-each-candidate-harness-drive-it | blocked | Dense Qwen3 uses Hermes-style `<tool_call>` JSON (b10537's autoparser, no unit test for that exact template); the MoE's Unsloth template uses Qwen3-Coder XML (dedicated, tested handler). Open engine bugs #27767, #24807, #28522 hit the probe set. All four frameworks can drive llama-server natively; Q33 overhead is readable through a recording proxy. Remains: live probes P1-P5 per roster entry, attribution with `parse_tool_calls: false`, a framework driver run on a throwaway branch; Q109, Q110. | 5782f6a |
| which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms | blocked | `gpt-5.6-luna` exists on OpenAI's direct API (Q7), undated snapshot id; reasoning off with effort `none`; seed only on Chat Completions; $0.20 / $0.02 / $1.20 per 1M input / cached / output; calibration projected well under the ten-dollar estimate; API data not used for training by default, 30-day abuse logs. Remains: 9 live calls with a paid key; Q102 (undated id), Q104 (GPT-6 Luna exists). The Services Agreement page returned 403 and was not read at a revision. | 51aa169 |
| may-the-model-outputs-in-the-published-rows-be-redistributed-and-on-what-terms | resolved | Nothing. Every model licence and provider term read (Qwen3, Gemma 4 now plain Apache 2.0, Granite, Ministral, Phi, LFM, Mistral, Google, DeepSeek, Z.ai, OpenAI) permits redistributing output; the condition the providers impose is an AI-generated marking naming model and provider. New task (proposed): `the-model-output-fields-cite-the-terms-they-were-checked-against-and-carry-the-ai-generated-notice`. Q111 asks the owner to update the bundle epic's assumption row. | 86e26be |
| which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream | blocked | Two tools pass on desk evidence: SearXNG self-hosted and the Mojeek API, so order 10's out-of-scope trigger does not fire. Remains: a pinned SearXNG instance and Mojeek queries captured live (install and provider call, out of this run's bounds), the Mojeek account (owner act), Q112, Q113, Q114. | 2270c34 |
| can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol | blocked | Pin Ollama v0.35.1 (it bundles its own llama-server, llama.cpp b11232 plus patches, not the reference b10537). `FROM <gguf>` keeps the bytes, so the layer digest equals the roster sha256; `/api/ps` reports loaded models and effective context; keep-alive pinnable per request; no endpoint shows a second client; TTFT comes from the bundled server's `timings.prompt_ms`. Default install: `qwen3:0.6b` resolves to Q4_K_M, not the roster Q8_0 (input to Q21). Remains: one live session on v0.35.1 (commands in the spike). | 69c2ce3 |
| does-ollama-expose-the-prompt-it-finally-rendered | blocked | No generation response returns the rendered prompt, so `captured` is impossible; `_debug_render_only: true` on `/api/chat` returns the render from the bundled server's `/apply-template` (`prompt_capture: reconstructed`, undocumented, so the engine entry pins the version). Thinking switch verifiable by comparing renders. Remains: live renders for one EN and one FR item, think on and off, byte-diffed against b10537 `/apply-template`. The agent drafted a native-versus-raw question; not filed, because the parity-gate story already chooses native rendering behind a gate. | 0c5f981 |
| which-constrained-decoding-mechanism-does-ollama-expose | blocked | No GBNF field in the public API; the only constraint is `format` (`"json"` or a JSON Schema), compiled to a grammar by the bundled llama-server. Against a GBNF variant on llama.cpp this is the epic's "different mechanism" outcome (`json_schema_format` beside `gbnf_grammar`), and the output is JSON, not a bare label. Remains: ten constrained and ten unconstrained live generations on v0.35.1. | 1631f14 |
| which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement | blocked | Compressor pinned by revision and sha256 (`llmlingua-2-xlm-roberta-large-meetingbank`, MIT; the multilingual BERT-base variant as alternative); co-residence excluded by measured VRAM; token counts must use the subject's tokenizer, not LLMLingua's tiktoken counts; the compression step's time and energy are measurable as their own window. Remains: one live CPU measurement in an isolated environment (install and download, out of this run's bounds), and Q115 (placement). Ruff 0.16 formats the Python block embedded in the spike, so the file was run through `ruff format`. | 51c90c7 |

## Step 2: proposed items

No proposed story reached `ready` in this step: each sits behind a `blocked` spike, an unanswered owner question of this run (Q100-Q115) or a `depends_on` chain that does. Each story's `Blocked:` line now names exactly that, and its "Current state" was re-verified against `main` at `c68b23e`.

The run brief said `the-campaign-answers-whether-each-variant-helps-or-hurts-a-small-model` and `the-threshold-review-is-written-from-the-first-publication-run` have no `Blocked:` line. They do: both lines date from their creation (`baa9184` and `48732f0`, 2026-10-01), and both block only through their `depends_on` chains. Their lines are made precise below.

| Epic | Story | Ready? | What blocks it | Commit |
| --- | --- | --- | --- | --- |
| every-size-class-spans-two-families-or-says-it-does-not | the-half-billion-class (5) | no | GGUF spike's live gate loads (`granitehybrid`, `granite`, `lfm2`), Q107, Q108 | 8ce087f |
| every-size-class-spans-two-families-or-says-it-does-not | the-two-billion-class (6) | no | GGUF spike's live gate loads (`lfm2`, `granitemoe`, `granitehybrid`, `granite`), Q107, Q108 | 8ce087f |
| every-size-class-spans-two-families-or-says-it-does-not | the-four-billion-class (7) | no | GGUF spike's live gate loads (`granitemoe`, `mistral3`, `phi3`, `phimoe`), Q108; ready once Q108 (a) is answered | 8ce087f |
| every-size-class-spans-two-families-or-says-it-does-not | the-top-class (8) | no | GGUF spike's live gate loads (`gemma4` twice), Q108; ready once Q108 (a) is answered | 8ce087f |

Size-class notes: "Current state" added to all four (class entry, bytes, declaration, gate record fields; `candidate-records.jsonl` does not exist yet); the composition check's shipped-file tests are in `tests/test_composition_check.py`, not `tests/test_roster.py` (fixed in all four); download sizes corrected from the spike (order 7: Phi-tiny-MoE is 4.0 GB at `Q8_0`; order 8: 6.4 GB and 13.6 GB, not 7 and 16). Noted, not changed: the epic's own Current state says `KNOWN_FAMILIES` holds three families (it holds six; the epic is `ready`, owner edit); `SizeClassDeclaration` has no field for a missing dense model's reason, so order 8's "missing with the reason recorded" lands in the candidate record and README unless its delivery adds one; `validate_host_fit`'s ceiling for the 26B-A4B is its 128 experts, which never limits `n_cpu_moe`.
| any-open-ended-output-carries-two-judges-or-an-honest-flag | a-glm-judge (8) | no | GLM spike's 8 live calls (paid Z.ai key), Q102 | b84199e |
| any-open-ended-output-carries-two-judges-or-an-honest-flag | a-deepseek-judge (9) | no | DeepSeek spike's live calls (paid key), Q102, Q103 | b84199e |
| any-open-ended-output-carries-two-judges-or-an-honest-flag | glm-and-deepseek-are-the-only-judges (10) | no | only through orders 8 and 9 | b84199e |
| any-open-ended-output-carries-two-judges-or-an-honest-flag | a-calibration-judge (11) | no | Luna spike's live calls (paid OpenAI key), Q102, Q116 (new: agreement against what), order 10; Q104 open but not blocking | b84199e |
| any-open-ended-output-carries-two-judges-or-an-honest-flag | the-judged-probe (6) | no | only through order 10 | b84199e |

Judge epic notes: Current state added or rewritten on all five (no Z.ai, DeepSeek or OpenAI client or family; `KNOWN_FAMILIES` holds six; `REASONING_TOKEN_BILLING` covers only `mistral` and `google`; `JudgeCallRecord` has no API-version field; `judge_backends.py` still binds the retired judges). Orders 8 and 9: egress bullets now cite the terms the spikes recorded; "Code it changes" gains the judge record's API-version field and the providers' `REASONING_TOKEN_BILLING` basis, without which `cost.judge_cost_fields` raises. Order 8's client calls `api.z.ai`, never `open.bigmodel.cn` (different data terms). If Q102 is answered (a), the first acceptance bullet of orders 8 and 9 ("dated id") is reworded to the release-id-plus-marker reading. Noted, not changed: `README.md` still calls `GOOGLE_API_KEY` "reserved for the planned second LLM-as-a-judge" and `aidd_docs/memory/architecture.md` still names Mistral and Google as the judges (order 10 retires both).
| quality-scored-comparison-first-three-use-cases | judge-scoring-with-inter-judge-agreement (2) | no | only through `depends_on` on judge epic order 10 and the judged probe (judge spikes' live calls, Q102) | d1e35f6 |
| quality-scored-comparison-first-three-use-cases | the-rewriting-suite-scores-dense-and-moe (5) | no | only through order 2 | d1e35f6 |
| quality-scored-comparison-first-three-use-cases | a-judged-re-run-receives-a-reproduction-verdict (6) | no | Q102 directly (its not-comparable bullet compares each judge's dated id, which no judge provider publishes), order 2, and `a-cloud-subject-re-run-is-decided-per-item-under-its-suites-declared-tolerance` (`ready`, not `done`) | d1e35f6 |

Quality epic notes: Q50 to Q57 were already applied to order 2; it gains a Current state (`rewriting-business-email` is declared in `use_case_coverage.json` but not registered, so registering it changes `tests/test_use_case_coverage.py`'s expected refusal; no judged scoring rule exists). Order 5: the stale roster facts are corrected (`roster_version` 4, current entry ids); one acceptance bullet changed, because "with no change to that surface's code" contradicted the story's own read-model test and the PRD rule that a judged score never appears without its agreement figure: `read_model.COMPARISON_CELL_FIELDS` carries no judge field today, so the bullet now keeps the column grouping and adds the judge block to the cells, and "Code it changes" names `read_model.py`. Also found: `comparison.scoring_kind` knows only graded and binary rows, so a judged row gets no paired test yet (no story owns that; noted). Order 6: Q71 (a) applied (the cloud branch reuses the per-item rule of `a-cloud-subject-re-run-is-decided-per-item-under-its-suites-declared-tolerance`); an unverifiable sentence removed. Noted for delivery: whichever of that cloud-subject story and order 2 lands second gives `rewriting-business-email` its declared per-item tolerance, and free-text cloud outputs need a tolerance unit that story allows.
| no-use-case-is-silently-absent | document-comparison (3) | no | only through the judge chain (judge spikes' live calls, Q102) | 1d5b8dd |
| no-use-case-is-silently-absent | a-rag-answer (5) | no | Q109, Q110 (its `llamaindex` adapter), and the judge chain | 1d5b8dd |
| no-use-case-is-silently-absent | a-tool-calling-item (6) | no | tool-call spike's live probes P1-P4 per roster entry (runs 1-3) | 1d5b8dd |
| no-use-case-is-silently-absent | the-same-tool-calling-items-under-each-harness (7) | no | tool-call spike's framework run (run 4), Q109, Q110, order 6 | 1d5b8dd |
| no-use-case-is-silently-absent | an-agentic-plan (8) | no | tool-call spike's runs 1-4, orders 6 and 7 | 1d5b8dd |
| no-use-case-is-silently-absent | a-web-research-score (9) | no | search spike's live SearXNG capture, Q113, Q114, and the judge chain | 1d5b8dd |
| no-use-case-is-silently-absent | two-search-tools (10) | no | Q112, Q113, search spike's live Mojeek capture, order 9 | 1d5b8dd |

Use-case epic notes: Q73 (a) applied (orders 3, 5, 6, 8 and 9 each require one MoE and one tiny dense entry side by side, or a recorded refusal); Current state added to all seven. From the spikes: order 6 sends `tool_choice: "auto"` on local generations (llama.cpp #27767); order 9's first adapter is SearXNG (no account), its archive form and egress follow the spike, and its judges read archived snippets with no page fetch; order 10's second adapter is the hosted tool Q112 settles. Q109 and Q110 now also list order 5's `llamaindex` adapter. Noted for delivery: `local_client.complete_chat` returns content only, so a tool-call response raises today.
| the-engine-and-the-prompt-variant-are-measured-not-assumed | ollama-runtime-rows (6) | no | runtime Ollama spike's live session on v0.35.1 | fb13874 |
| the-engine-and-the-prompt-variant-are-measured-not-assumed | ollama-quality-rows (7) | no | rendered-prompt spike's live session, Q117 (new: its thinking-switch bullet contradicts the shipped rule), order 6 | fb13874 |
| the-engine-and-the-prompt-variant-are-measured-not-assumed | the-constrained-variant-on-the-comparator (8) | no | constrained-decoding spike's live generations, order 7 | fb13874 |
| the-engine-and-the-prompt-variant-are-measured-not-assumed | the-input-compression-variant (9) | no | compressor spike's live CPU measurement, Q115 | fb13874 |
| the-engine-and-the-prompt-variant-are-measured-not-assumed | what-a-default-ollama-install-costs (11) | no | runtime Ollama spike's live session (its defaults part), order 6 | fb13874 |
| the-engine-and-the-prompt-variant-are-measured-not-assumed | the-campaign-answers-whether-each-variant-helps (12) | no | only through orders 8 and 9 | fb13874 |

Engine epic notes: the campaign story is `proposed` because two of its five `depends_on` (orders 8 and 9) are `proposed`; the other three are `done`, and nothing blocks it of its own. Current state added to all six (only `llama.cpp` in the engine registry; `attached` lifecycle accepted but unserved; `engines.normalise_config` needs a model-path flag an attached engine lacks; no optional dependency group, and `scripts/audit_dependencies.py` would not see one). From the spikes: order 9 also pins, by checksum, the `cl100k_base` file the compressor fetches at load; order 7's code changes include carrying the roster's thinking control in Ollama's switch spelling (`check_engine_carries` refuses a control spelled for another engine). Noted: Ollama passes no `--n-cpu-moe`, so the flagship's Ollama cells fall under the campaign's run, refuse or drop rule; the epic's "Thinking control is per engine" row is already current on `main` (the 2026-10-01 log's stale-wording note on it no longer applies).
| a-score-is-published-with-its-interval-a-difference-with-its-test | a-publication-level-classification-suite (7) | no | Q105 only (every `depends_on` is `done`); ready once Q105 is answered | 545d999 |
| a-score-is-published-with-its-interval-a-difference-with-its-test | a-publication-level-translation-suite (8) | no | Q106, Q118 (`max_output_tokens`), Q119 (domain strata) | 545d999 |
| a-score-is-published-with-its-interval-a-difference-with-its-test | the-threshold-review (9) | no | orders 7 and 8, and Q120 (no published n=20 side carries an interval) | 545d999 |

Interval epic notes: order 9 already had a `Blocked:` line; it is `proposed` because both its `depends_on` are `proposed` and their published batches are its only input, and it now also names Q120. Current state added to orders 7 to 9 (suites are data through `suite_registry`; the publication gate in `suite_gate`; sampler `"1"` stratifies a classification draw by language then label and accepts only `['language']` on a translation draw, and refuses a repeated source key, so MASSIVE needs a `locale/id` key and a WMT24++ table offering one segment in several directions needs a direction-qualified key; rows carry no per-item content hash; the committed bundle is schema `"7"` with no translation row). Order 7: the licence-rung bullet applies the spike (permissive, CC BY 4.0 attribution in the results README, a different licence reopens the spike) and the sampler bullet names "the benchmark Q105 picks"; the scope note now cites the `done` cloud-batch story's derived retry budget and per-item `--resume`. Order 8: acceptance deliberately unchanged until Q106; its "published rows" claim is corrected (the bundle holds no translation row).
| one-download-holds-the-tables-their-licences-and-how-to-cite-them | a-drawn-item-reaches-the-download (7) | no | Q106 (the only question that can put a source off the permissive rung), and through `depends_on` orders 7 and 8 of the interval epic and the `ready`, unbuilt `each-release-attaches-one-archive-that-needs-no-clone` | 740f8a4 |

Bundle epic notes: Current state added (no content-hash, stable-key or redaction column; the committed suite-definition snapshots carry item text, so a no-redistribution redaction must reach them too). Acceptance: the LICENSE-DATA bullet now also requires each licence's redistribution notices (CC BY 4.0 attribution; Apache-2.0 text and a statement of change); the last bullet no longer claims the export already states hand-written-only coverage (only `LICENSE-DATA` does). Under Q106 (a) every source is permissive, so the share-alike and redaction halves are proven on constructed bundles only, as `Needs:` allows.

## Step 3: the credible-sessions epic

`a-release-is-called-credible-only-by-its-logged-client-sessions` sliced into four stories under the owner answers Q60 to Q69 (recorded on the epic by `20eaa1f`). Three-amigos: three independent lenses (product, delivery, quality) on the first drafts, reconciled, then a second-round check of the two ready candidates and the new task; every finding either amended the text or became an owner question.

| Order | Story | Status | Tag | Blocked by |
| --- | --- | --- | --- | --- |
| 1 | each-client-showing-is-logged-as-a-record-someone-who-was-not-there-can-read-back | ready | code-only | nothing |
| 2 | a-challenge-no-named-evidence-resolved-is-sustained-and-points-at-its-follow-up-item | ready | code-only | nothing (`depends_on` order 1, `ready`) |
| 3 | each-release-reads-its-credibility-verdict-from-its-records-in-its-changelog-entry | proposed | code-only | Q100 (does a dismissed session count toward the three) |
| 4 | the-first-real-client-session-is-logged-the-same-day-and-read-back-by-someone-who-was-not-there | proposed | operator | through order 3 |

The epic itself stays `proposed` (an epic status is the owner's: Q101). Two stories are `ready` under it; a delivery run picking them should know the owner has not yet accepted the epic.

Decisions taken under this run's authority, each a delivery or interpretation choice that changes no owner decision:
- Record format: JSONL (Q60 names JSONL or YAML), at `aidd_docs/results/client-sessions.jsonl`, with its own `.gitignore` negation (the folder ignores `*.jsonl`), checked by `git check-ignore --no-index` (a tracked file is otherwise reported as not ignored).
- Field classes: identity and attribution fields are refused when absent; the three content fields the PRD names (role, evidence offered, criterion disputed) are reported incomplete and not counted, which is how epic check 1 ("does not count") and check 6 read together.
- Resolving evidence is "presented within the session" (the PRD's wording); evidence found later goes to the follow-up item.
- A challenge carries a non-empty list of claims rather than one tag, so a challenge to two of the three claims is representable; the read-back checks the list against the criterion named in words.
- A showing of unreleased results is logged with `unreleased` and its commit and counts toward no release (the PRD asks every showing to be logged, and a verdict is per release).
- Append-only is enforced by a history test along `--first-parent` with `fetch-depth: 0` in CI, and corrections are appended records with their own id; deleting a sustained record would otherwise restore a revoked verdict silently.
- Revocation follows append order, not session dates (epic check 4 says "planted after a verdict was reached").
- A sustained challenge to one of the three claims blocks whether or not its session is complete or backfilled; an internal session neither counts nor blocks.
- A follow-up item may also be linked from a resolved challenge (the first draft's refusal had no source); its path is frozen once cited, and its status never changes whether the challenge is sustained.

## The redistribution task

`aidd_docs/backlog/tasks/the-model-output-fields-cite-the-terms-they-were-checked-against-and-carry-the-ai-generated-notice.md` (bundle epic, created with the redistribution spike's commit) moved `proposed -> ready` after the second-round three-amigos check: it gained `README.md`'s licence section (which carries the same unverified wording), the section 3 assumption count, and a whitespace-collapsed test for the notice. Code-only; Q111 (the epic's assumption row) does not block it.

## Step 4: stale wording in done stories

Wording only; no acceptance meaning changed; the code already follows each story's intent.

| Story | Fix |
| --- | --- |
| the-composition-check-names-every-size-class-and-refuses-an-unlabelled-single-family-one | "of the entry it cites" now notes that a cloud row carries its own subject's family and a null size class (`quality_rows.py`) |
| comparison-family-and-leader-set-records-read-as-a-fifth-table | "(today all three ...)" now says all three kinds were absent when written and the committed bundle now holds all three |
| every-roster-entry-states-its-family-its-licence-and-its-language-claim | "keeps passing unchanged" now says its family assertions are unchanged while its `roster_version` assertion follows the file, as the story's version bullet states |
| a-candidate-model-enters-the-roster-only-through-the-verification-gate-or-leaves-a-recorded-refusal | the evidence line no longer says bytes and template hash match the shipped entry (`models.json` carries neither); they are as the gate recorded them |

Not edited: the "Current state" and "Code it changes" sections the log calls stale (history of what each story found; rewriting them is not a wording fix); `the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives` (read-only for this run: Q122); the judge-call story's null rule (acceptance meaning: Q121). The other "Needs an owner edit" items are already settled on `main` (see the Q121 section header).
