"""Classification task suite: support-message routing -- what its scoring needs.

The suite itself is data: `suite_data/classification-support-routing.json`
holds its identity, its caps and its twenty items, resolved by id through
`suite_registry`, and is scored by the `exact_label_match` rule
(`scoring_rules.py`). This module keeps only what that scoring needs -- the
closed label set and the item shape -- and the reasoning behind the
declarations the data file cannot carry as comments.

Domain: a consultant's client support inbox, where each incoming message must be
routed to exactly one queue. Chosen over sentiment because the four routing
labels are semantically disjoint (a message is rarely ambiguous between "billing"
and "technical"), which keeps exact-label-match scoring honest -- a wrong answer
is a genuine routing error, not a borderline judgment call a fuzzier metric would
need to soften.

Every prompt embeds the closed label set verbatim and instructs the model to
answer with exactly one label word, so both the local SLM and the cloud model
see the identical instruction and the identical closed set to choose from.

Why the data declares what it declares:

- `suite_version`, versioned independently from the row schema
  (Methodology 19). "2": +5 FR + 5 DE hand-written items (Story 20) --
  adding items is the same class of change as editing a prompt
  (Methodology 2). "3": no item changed and `prompt_set_hash` does not move;
  the local path now renders each item through the model's own chat template
  under the declared thinking policy instead of posting it raw to
  `/completion`. A score under "3" measures something a score under "2" did
  not; the pair (`suite_version`, `prompt_template_id`) separates the two.
  "4": no item text changed and `prompt_set_hash` does not move; the
  definition gained `level` and every item its `licence`, which the
  published snapshot carries, and a published snapshot is never rewritten
  under its own version. What the subject is sent is identical to "3".
- `level` `development` (Methodology 4): twenty hand-written items are the
  development level's floor, not the publication level's hundred. Rows name
  the level their suite was certified at, so this score is never read as a
  publication-level one.
- Each item's `licence` `CC-BY-4.0` (Methodology 5): the repository's own
  hand-written items are published under it. It sits on the item, not only
  on the suite, because a suite may one day hold items under other terms.
  The items declare no `source` or `source_revision`: nothing was drawn from
  a public benchmark.
- `max_output_tokens` 32: the cap is a property of what the suite asks a
  model to produce (one label word), not of the harness driving the request.
- `thinking_policy` `disabled`: probed on `b10537-bf0040e15`, `Qwen3-0.6B`
  and `Qwen3.6-35B-A3B` asked through their own chat templates with thinking
  allowed spend all 32 tokens in `reasoning_content` and answer nothing; with
  thinking disabled both answer in two tokens.
- `stop_sequences` empty: none is sent to any provider.
- `context_length` 32768: the shipped roster entries' `server_flags` value,
  restated as data rather than imported, since a roster entry could run at a
  different context.
"""

from __future__ import annotations

from typing import Literal, TypedDict

LABELS: frozenset[str] = frozenset({"billing", "technical", "account", "other"})


class ClassificationItem(TypedDict):
    """One task-suite item: a prompt, its known-correct label, and its tags."""

    item_id: str
    prompt: str
    expected_label: str
    language: Literal["en", "fr", "de"]
    provenance: Literal["hand_written", "licensed", "public"]
    contamination_risk: bool
