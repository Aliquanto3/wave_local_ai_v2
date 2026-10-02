---
type: task
status: done
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
order: 1
---

# Task: Register the closed harness candidate set and its three row fields

## Outcome

A row-writing path can name the agentic harness that produced a row, from a closed registry of Methodology 23's five candidates, and the row contract carries three harness fields: the harness id, the harness's own version read from the installed package at run time, and its per-call prompt overhead kept apart from the task's own tokens. It is the shared prerequisite of the RAG suite (`a-rag-answer-is-scored-over-a-local-corpus-under-a-named-harness.md`) and the tool-calling suite (`a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md`), split out so neither waits on the other's blocker: the epic's Sequence makes the harness registry "a prerequisite of step 4 rather than step 5".

Overhead rule (owner decision, 2026-10-01): per call, the token count of what the engine finally received minus the token count of the item's own rendered prompt, both under the tokenizer the row already names. The item's own tool definitions, as rendered under `direct`, are part of the item, not of the overhead. A framework that rewrites the item's prompt rather than wrapping it is recorded unmeasurable, never zero.

## Scope

- Includes: the registry of `direct`, `smolagents`, `langgraph`, `pydantic-ai` and `llamaindex`, closed at five; the three row fields through `row_contract.py`; the overhead measurement under the rule above, read from what the engine actually received rather than from a framework's self-reported count, with an explicit unmeasurable value for a harness the rule cannot measure; `direct` implemented as the reference.
- Excludes: the four framework adapters (the RAG story implements `llamaindex`, the harness-comparison story the others); choosing which three harnesses a campaign compares, owned by the campaign declaration of `the-engine-and-the-prompt-variant-are-measured-not-assumed`; the harness list on that declaration and the three-harness cap refusal, both added by `the-same-tool-calling-items-run-under-each-compared-harness.md`; any rendering.

## Done When

- A row naming a harness outside the five is refused by the writer gate.
- A `direct` row's harness version is read at run time, and its overhead is the value the rule yields from what the engine received, never a hard-coded zero.
- An item carrying tool definitions has them counted in its own prompt, not in the `direct` overhead.
- A fixture harness the rule cannot measure writes the unmeasurable value, not zero, and the gate refuses a row whose overhead field is absent.

## Completion Evidence

- `tests/test_row_contract.py` cases for the three fields and the refusals, and a `direct` fixture row carrying all three.

## Cancellation

n/a: not cancelled.
