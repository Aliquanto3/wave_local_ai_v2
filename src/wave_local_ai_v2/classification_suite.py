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

LABELS: frozenset[str] = frozenset({"billing", "technical", "account", "other"})

_LABEL_LIST = ", ".join(sorted(LABELS))
_INSTRUCTION = (
    f"Classify the following support message into exactly one of these "
    f"categories: {_LABEL_LIST}. Reply with only the single category word, "
    f"nothing else.\n\nMessage: "
)

# This suite's stable identity, versioned independently from the row schema
# (Methodology 19): the id names the suite, the version tracks its item set.
# "2": +5 FR + 5 DE hand-written items (Story 20: the-classification-suite-
# reaches-twenty-items-across-three-languages) -- adding items is the same
# class of change as editing a prompt (Methodology 2).
SUITE_ID = "classification-support-routing"
SUITE_VERSION = "2"

# The generation cap `quality_cli.py` sends for every local completion. Declared
# here, on the suite, rather than in the CLI: the cap is a property of what the
# suite asks a model to produce, not of the harness driving the request.
MAX_OUTPUT_TOKENS = 32
# No stop sequence is sent to either provider today.
STOP_SEQUENCES: list[str] = []
# The context every compared model is assumed to run at. Phase 2 of the
# versioned-roster increment moved `context_size` from a `server.py` module
# constant into the roster entry's own `server_flags` (`roster.py`), so this
# suite-level assumption is now a literal matching the shipped roster entry's
# value (`aidd_docs/roster/models.json`) rather than an import: `server.py`
# no longer exposes one context-size constant to import, since a future
# second roster entry could run at a different context.
CONTEXT_LENGTH = 32768


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
    _item(
        "billing-fr-01",
        "Le prélèvement automatique de ce mois ne correspond pas au montant "
        "indiqué sur mon devis, pouvez-vous vérifier ?",
        "billing",
        language="fr",
    ),
    _item(
        "technical-fr-01",
        "Depuis la dernière mise à jour, l'application se fige dès que "
        "j'ouvre le tableau de bord.",
        "technical",
        language="fr",
    ),
    _item(
        "account-fr-01",
        "Je n'ai jamais reçu l'e-mail de confirmation pour activer mon "
        "compte, pouvez-vous le renvoyer ?",
        "account",
        language="fr",
    ),
    _item(
        "other-fr-01",
        "Est-ce que vous prévoyez une version mobile de l'application dans "
        "les prochains mois ?",
        "other",
        language="fr",
    ),
    _item(
        "technical-fr-02",
        "Le fichier que j'exporte en CSV contient des caractères accentués "
        "mal encodés.",
        "technical",
        language="fr",
    ),
    _item(
        "billing-de-01",
        "Auf meiner letzten Rechnung fehlt der vereinbarte Rabatt aus unserem Vertrag.",
        "billing",
        language="de",
    ),
    _item(
        "technical-de-01",
        "Der Upload bricht immer bei etwa 80 Prozent ab, egal welche Datei "
        "ich verwende.",
        "technical",
        language="de",
    ),
    _item(
        "account-de-01",
        "Ich möchte meine Zwei-Faktor-Authentifizierung deaktivieren, finde "
        "aber die Option nicht.",
        "account",
        language="de",
    ),
    _item(
        "other-de-01",
        "Gibt es einen Zeitplan für die nächste Feature-Ankündigung?",
        "other",
        language="de",
    ),
    _item(
        "account-de-02",
        "Mein Account wurde offenbar mit einer falschen E-Mail-Adresse "
        "verknüpft, können Sie das korrigieren?",
        "account",
        language="de",
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
