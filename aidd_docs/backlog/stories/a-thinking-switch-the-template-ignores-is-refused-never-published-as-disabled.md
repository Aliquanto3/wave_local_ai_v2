---
type: story
status: ready
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parent: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
order: 2
---

# Story: A thinking switch the template ignores is refused, never published as disabled

**As** an academic or technical reviewer comparing a reasoning model against one that answers directly
**I want** each roster entry to declare the thinking control its own chat template honours, and a batch run under `thinking_policy: disabled` to prove that control changes the rendered prompt before any item is generated
**So that** no row claims a thinking policy the model never applied, which is the first silently wrong row a non-Qwen entry would otherwise produce

Maps to: Methodology 3 ("thinking policy belong[s] to the suite definition, [is] identical across every model compared on an item, and [is] recorded per row"); PRD AC "Given a supported task suite, running it against a local model and a cloud model produces one quality score ... from the same suite items rendered per provider under Methodology 2 and 3"; epic Boundaries "a verification step per candidate model ... the chat template read from `/props` and its thinking control established through `/apply-template`"; epic decision "The thinking control is per entry, declared and verified"; epic Dependencies "The thinking control differs per family and only Qwen's is probed"; epic success check 5.

Needs: a real local model run, only for the evidence: one load of the already-downloaded `qwen3-0.6b-q8` under the pinned build to show the shipped control verifies live. Every acceptance condition is proved against a stubbed server.

Current state: `local_client._thinking_kwargs` maps `disabled` to exactly `{"chat_template_kwargs": {"enable_thinking": False}}` for every model, a Qwen template convention a template that does not declare it ignores silently. `render_prompt` already sends the same arguments to `/apply-template`. Both suites declare `THINKING_POLICY = disabled`, and every quality row carries `thinking_policy` since schema 11.

## Acceptance

- Each roster entry declares its thinking control: the request arguments that disable reasoning under its template, or `none` for a model that does not reason. The four shipped Qwen entries declare the `chat_template_kwargs.enable_thinking: false` control they run under today. `local_client` sends the entry's declared control, and the Qwen spelling no longer exists as a module-wide default.
- Before the first item of a batch run under `disabled`, the declared control is verified: the client renders one fixed probe message through `/apply-template` with the control and without it. Two byte-identical renders refuse the batch before any generation, naming the entry, the control and the template hash, and no row is written.
- A batch under `disabled` against an entry declaring `none` sends no control, and the refusal above does not apply to it; the declaration is the entry's to justify, and the candidate gate (order 4) is where it is checked against a live generation.
- An entry declaring no control and not declaring `none` cannot be run under `disabled`: the run refuses, naming the entry, rather than falling back to the Qwen spelling.
- `allowed` still sends nothing, and the shipped entries' rendered prompts, `prompt_template_hash` and generations are byte-identical to today's under both policies, so no published quality row is invalidated.

## Code it changes

- `src/wave_local_ai_v2/roster.py`: the thinking-control declaration on an entry and its shape validation.
- `src/wave_local_ai_v2/local_client.py`: the control read from the entry; the with-and-without render comparison as a named function the candidate gate reuses.
- `src/wave_local_ai_v2/quality_cli.py`: the verification called once per batch before its first item.
- `aidd_docs/roster/models.json`: the control on the four shipped entries.

## Tests it needs

- `tests/test_local_client.py` (HTTP stubbed): a stubbed `/apply-template` returning identical strings with and without the control refuses the batch before any `/v1/chat/completions` call, asserted on the stub's call count; differing strings pass; the declared control is what the chat call sends.
- `tests/test_quality_cli.py` (HTTP stubbed): a refused verification writes no row; a shipped Qwen entry's batch writes the same rendered prompt as before.
- `tests/test_roster.py`: an entry with a malformed control is refused naming the field; the shipped entries all declare one.

## Evidence it publishes

- One live verification against `qwen3-0.6b-q8` on the dev machine, the two rendered strings and the pass recorded in the story's task evidence. It is written to no results file.

## Cancellation

n/a: not cancelled.
