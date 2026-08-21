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

from typing import TypedDict

LABELS: frozenset[str] = frozenset({"billing", "technical", "account", "other"})

_LABEL_LIST = ", ".join(sorted(LABELS))
_INSTRUCTION = (
    f"Classify the following support message into exactly one of these "
    f"categories: {_LABEL_LIST}. Reply with only the single category word, "
    f"nothing else.\n\nMessage: "
)


class ClassificationItem(TypedDict):
    """One task-suite item: a prompt and its known-correct label."""

    item_id: str
    prompt: str
    expected_label: str


def _item(item_id: str, message: str, expected_label: str) -> ClassificationItem:
    return ClassificationItem(
        item_id=item_id,
        prompt=_INSTRUCTION + message,
        expected_label=expected_label,
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
