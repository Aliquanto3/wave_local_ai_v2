"""Translation task suite: short-form business correspondence -- what its
scoring needs.

The suite itself is data: `suite_data/translation-business-short-form.json`
holds its identity, its caps and its 21 items, resolved by id through
`suite_registry`, and is scored by the `chrf_against_reference` rule
(`scoring_rules.py`). This module keeps only the item shape that scoring
reads and the reasoning behind the declarations the data file cannot carry
as comments.

Domain: the sentences a consultant's inbox actually carries -- a delivery
note, a line from a client email, a meeting time, an invoice status. Short,
professional register, one sentence per item, so a single reference
translation is a defensible target and the 128-token cap is never the reason
a model fails.

Why this suite is scored deterministically rather than judged: a reference
translation exists and can be written by hand, so the score is arithmetic
over character n-grams (`chrf.py`) with no judge model, no judge call and no
judge cost. The judged path (`judge_probe.py`) exists for the open-ended
items where no reference can be written; translation is the other half of
that split, not a cheaper version of it.

The caveat `chrf.py` states applies in full here: chrF against one reference
penalises a valid alternative translation that happens to share fewer
character n-grams with the wording on file. Read a published score as a
comparison between models measured against identical references. It is not
an absolute measure of translation quality, and the German references in
particular were not reviewed by a native speaker in-project.

Three directions arranged as a cycle -- `en->fr`, `fr->de`, `de->en`, seven
items each. Every language appears once as a source and once as a target,
which puts each source language at 33% of the suite and clears
`suite_gate.MIN_LANGUAGE_SHARE`. Every source text is authored natively in
its own language: no item is a translation of another item's source, so the
suite never asks a model to translate text a translator already smoothed.

Every prompt is one English instruction shell, "Translate the following
{source} text into {target}. Reply with only the translation, nothing
else.", followed by the source text, so every model on every provider sees
an identical instruction. An item's `language` tag describes the material
handed to the model, never the language the instruction is phrased in.

Why the data declares what it declares:

- `suite_version` "2": no item changed and `prompt_set_hash` does not move --
  the same bump, for the same reason, as the classification suite's "3": the
  local subject is rendered through the model's own chat template under the
  declared thinking policy instead of being posted raw to `/completion`. A
  chrF score under "2" is not comparable to one under "1".
- `max_output_tokens` 128, not the classification suite's 32: a sentence
  translation truncates there.
- `thinking_policy` `disabled`, on evidence: probed on `b10537-bf0040e15`,
  `Qwen3-0.6B` with thinking allowed spends all 128 tokens reasoning and
  answers nothing, while the same call with thinking disabled returns a
  complete French sentence in 30. A cap sized so that it is never the reason
  a model fails only holds under `disabled`.
- `stop_sequences` empty and `context_length` 32768: as the classification
  suite, for the same reasons.

Of the four failure-taxonomy keys `scoring` publishes, `unparseable` is
structurally unreachable on this suite: there is no closed set to parse a
completion into and no extraction step runs before scoring, so a completion
that is neither empty nor truncated is always scorable. Its count stays 0.
The key set published on a row remains the contract's four, so a reader
comparing two stores compares the same keys.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class TranslationItem(TypedDict):
    """One suite item: a prompt, its reference translation, and its tags.

    `language` is the **source** language -- the dimension `suite_gate` and
    the per-language breakdown slice on, and the same thing `language` means
    on a classification item and on a probe item. `target_language` is this
    suite's own field, and the direction is the pair of the two.
    """

    item_id: str
    prompt: str
    source_text: str
    reference: str
    language: Literal["en", "fr", "de"]
    target_language: Literal["en", "fr", "de"]
    provenance: Literal["hand_written", "licensed", "public"]
    contamination_risk: bool
