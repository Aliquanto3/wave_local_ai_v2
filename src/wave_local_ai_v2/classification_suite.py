"""Fixed classification task suite: support-message routing.

Domain: a consultant's client support inbox, where each incoming message must be
routed to exactly one queue. Chosen over sentiment because the four routing
labels are semantically disjoint (a message is rarely ambiguous between "billing"
and "technical"), which keeps exact-label-match scoring honest -- a wrong answer
is a genuine routing error, not a borderline judgment call a fuzzier metric would
need to soften.

Every prompt embeds the closed label set verbatim and instructs the model to
answer with exactly one label word, so both the local SLM and the cloud model
see the identical instruction and the identical closed set to choose from.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Literal, TypedDict

from wave_local_ai_v2 import server

LABELS: frozenset[str] = frozenset({"billing", "technical", "account", "other"})

_LABEL_LIST = ", ".join(sorted(LABELS))
_INSTRUCTION = (
    f"Classify the following support message into exactly one of these "
    f"categories: {_LABEL_LIST}. Reply with only the single category word, "
    f"nothing else.\n\nMessage: "
)

# This suite's stable identity, versioned independently from the row schema
# (Methodology 19): the id names the suite, the version tracks its item set.
SUITE_ID = "classification-support-routing"
SUITE_VERSION = "1"

# The generation cap `quality_cli.py` sends for every local completion. Declared
# here, on the suite, rather than in the CLI: the cap is a property of what the
# suite asks a model to produce, not of the harness driving the request.
MAX_OUTPUT_TOKENS = 32
# No stop sequence is sent to either provider today.
STOP_SEQUENCES: list[str] = []
# The context every compared model is assumed to run at. Same value the
# runtime harness's server launches with (`server.CONTEXT_SIZE`); imported
# directly rather than duplicated, since `server.py` does not import this
# module and no cycle results.
CONTEXT_LENGTH = server.CONTEXT_SIZE


class ClassificationItem(TypedDict):
    """One task-suite item: a prompt, its known-correct label, and its tags."""

    item_id: str
    prompt: str
    expected_label: str
    language: Literal["en", "fr", "de"]
    provenance: Literal["hand_written", "licensed", "public"]
    contamination_risk: bool


def _item(
    item_id: str,
    message: str,
    expected_label: str,
    *,
    language: Literal["en", "fr", "de"] = "en",
    provenance: Literal["hand_written", "licensed", "public"] = "hand_written",
) -> ClassificationItem:
    return ClassificationItem(
        item_id=item_id,
        prompt=_INSTRUCTION + message,
        expected_label=expected_label,
        language=language,
        provenance=provenance,
        contamination_risk=provenance == "public",
    )


CLASSIFICATION_TASK_SUITE: list[ClassificationItem] = [
    _item(
        "billing-01",
        "I was charged twice for my subscription this month, can you refund one?",
        "billing",
    ),
    _item(
        "billing-02",
        "My invoice shows a currency I don't recognize -- can you confirm what I owe in EUR?",
        "billing",
    ),
    _item(
        "technical-01",
        "The app crashes every time I try to export a report to PDF.",
        "technical",
    ),
    _item(
        "technical-02",
        "I'm getting a 500 error when uploading a file larger than 10MB.",
        "technical",
    ),
    _item(
        "account-01",
        "I can't log in anymore since I changed my email address last week.",
        "account",
    ),
    _item(
        "account-02",
        "Please delete my account and all associated data permanently.",
        "account",
    ),
    _item(
        "other-01",
        "Do you have any plans to support a language other than English?",
        "other",
    ),
    _item(
        "other-02",
        "Just wanted to say the new dashboard redesign looks great, thanks!",
        "other",
    ),
    _item(
        "billing-03",
        "The discount code from your newsletter didn't apply at checkout.",
        "billing",
    ),
    _item(
        "technical-03",
        "Search results stopped updating after the last update went out.",
        "technical",
    ),
]


def prompt_set_hash(items: Sequence[ClassificationItem]) -> str:
    """SHA-256 hex digest over the items' prompts only, deterministically ordered.

    Deliberately not over the whole item dict: adding a non-prompt field later
    (a tag, a provenance note) must never move the hash. Only an edited prompt
    should.
    """
    sorted_items = sorted(items, key=lambda item: item["item_id"])
    serialized = "\n".join(
        f"{item['item_id']}:{item['prompt']}" for item in sorted_items
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


PROMPT_SET_HASH = prompt_set_hash(CLASSIFICATION_TASK_SUITE)
