---
type: task
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
---

# Task: Register the closed harness candidate set and its three row fields

## Outcome

A row-writing path can name the agentic harness that produced a row, from a closed registry of Methodology 23's five candidates, and the row contract carries three harness fields: the harness id, the harness's own version read from the installed package at run time, and its per-call prompt overhead kept apart from the task's own tokens. It is the shared prerequisite of the RAG suite (`a-rag-answer-is-scored-over-a-local-corpus-under-a-named-harness.md`) and the tool-calling suite (`a-tool-calling-item-is-scored-from-its-transcript-never-from-a-judge.md`), split out so neither waits on the other's blocker: the epic's Sequence makes the harness registry "a prerequisite of step 4 rather than step 5".

Blocked: owner question Q33 (how per-call prompt overhead is measured), in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`.

## Scope

- Includes: the registry of `direct`, `smolagents`, `langgraph`, `pydantic-ai` and `llamaindex`, closed at five; the three row fields through `row_contract.py`; the overhead measurement as Q33 settles it, with an explicit unmeasurable value for a harness the rule cannot measure; `direct` implemented as the reference.
- Excludes: the four framework adapters (the RAG story implements `llamaindex`, the harness-comparison story the others); choosing which three harnesses a campaign compares and the three-harness cap's declaration, both owned by the campaign declaration of `the-engine-and-the-prompt-variant-are-measured-not-assumed`; any rendering.

## Done When

- A row naming a harness outside the five is refused by the writer gate.
- A `direct` row's harness version is read at run time, and its overhead is the value Q33's rule yields, never a hard-coded zero.
- A fixture harness the rule cannot measure writes the unmeasurable value, not zero, and the gate refuses a row whose overhead field is absent.

## Completion Evidence

- `tests/test_row_contract.py` cases for the three fields and the refusals, and a `direct` fixture row carrying all three.

## Cancellation

n/a: not cancelled.
