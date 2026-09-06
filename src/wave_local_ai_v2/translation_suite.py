"""Fixed translation task suite: short-form business correspondence.

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
"""

from __future__ import annotations

from typing import Literal, TypedDict

from wave_local_ai_v2.classification_suite import prompt_set_hash

# This suite's stable identity, versioned independently from the row schema
# (Methodology 19): the id names the suite, the version tracks its item set.
SUITE_ID = "translation-business-short-form"
SUITE_VERSION = "1"

# The generation cap `quality_cli.py` sends for every completion. Larger than
# the classification suite's 32 because a sentence translation truncates
# there; declared on the suite for the same reason that one is -- the cap is
# a property of what the suite asks a model to produce.
MAX_OUTPUT_TOKENS = 128
# No stop sequence is sent to any provider today.
STOP_SEQUENCES: list[str] = []
# The context every compared model is assumed to run at -- the same literal
# and the same reason `classification_suite.CONTEXT_LENGTH` carries: the
# shipped roster entry's `server_flags` value, restated rather than imported
# because a future second roster entry could run at a different context.
CONTEXT_LENGTH = 32768

# Of the four failure-taxonomy keys `scoring` publishes, `unparseable` is
# structurally unreachable on this suite: there is no closed set to parse a
# completion into and no extraction step runs before scoring (plan.md's
# Decisions), so a completion that is neither empty nor truncated is always
# scorable. Its count stays 0. The key set published on a row remains the
# contract's four, not this suite's reachable three, so a reader comparing
# two stores compares the same keys -- the precedent `judge_probe.py`'s
# `_FAILURE_COUNT_KEYS` sets for its own two unreachable keys.

_LANGUAGE_NAMES: dict[str, str] = {"en": "English", "fr": "French", "de": "German"}

# One shell for every item, parameterised by the two language names, so every
# model on every provider sees an identical instruction. The shell is written
# in English even when the source text is French or German -- the same choice
# `classification_suite._INSTRUCTION` makes. An item's `language` tag
# describes the material handed to the model, never the language the
# instruction is phrased in.
_INSTRUCTION = (
    "Translate the following {source} text into {target}. Reply with only "
    "the translation, nothing else.\n\nText: "
)


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


def _item(
    item_id: str,
    source_text: str,
    reference: str,
    *,
    language: Literal["en", "fr", "de"],
    target_language: Literal["en", "fr", "de"],
    provenance: Literal["hand_written", "licensed", "public"] = "hand_written",
) -> TranslationItem:
    instruction = _INSTRUCTION.format(
        source=_LANGUAGE_NAMES[language], target=_LANGUAGE_NAMES[target_language]
    )
    return TranslationItem(
        item_id=item_id,
        prompt=instruction + source_text,
        source_text=source_text,
        reference=reference,
        language=language,
        target_language=target_language,
        provenance=provenance,
        contamination_risk=provenance == "public",
    )


TRANSLATION_TASK_SUITE: list[TranslationItem] = [
    # en -> fr
    _item(
        "en-fr-01",
        "Could you confirm the delivery date for the order we placed last week?",
        "Pourriez-vous confirmer la date de livraison de la commande que nous "
        "avons passée la semaine dernière ?",
        language="en",
        target_language="fr",
    ),
    _item(
        "en-fr-02",
        "The invoice was sent to your accounting department this morning.",
        "La facture a été envoyée à votre service comptabilité ce matin.",
        language="en",
        target_language="fr",
    ),
    _item(
        "en-fr-03",
        "I would like to move our meeting to Thursday afternoon if that suits you.",
        "Je souhaiterais déplacer notre réunion à jeudi après-midi si cela "
        "vous convient.",
        language="en",
        target_language="fr",
    ),
    _item(
        "en-fr-04",
        "Please find attached the updated quotation for the maintenance contract.",
        "Veuillez trouver ci-joint le devis actualisé pour le contrat de maintenance.",
        language="en",
        target_language="fr",
    ),
    _item(
        "en-fr-05",
        "Our office will be closed next Monday for a public holiday.",
        "Nos bureaux seront fermés lundi prochain en raison d'un jour férié.",
        language="en",
        target_language="fr",
    ),
    _item(
        "en-fr-06",
        "The shipment left our warehouse yesterday and should arrive within "
        "three days.",
        "L'expédition a quitté notre entrepôt hier et devrait arriver sous "
        "trois jours.",
        language="en",
        target_language="fr",
    ),
    _item(
        "en-fr-07",
        "Thank you for your prompt reply; I have forwarded it to the project manager.",
        "Merci pour votre réponse rapide ; je l'ai transmise au chef de projet.",
        language="en",
        target_language="fr",
    ),
    # fr -> de
    _item(
        "fr-de-01",
        "Le contrat arrive à échéance à la fin du mois et doit être renouvelé.",
        "Der Vertrag läuft Ende des Monats aus und muss verlängert werden.",
        language="fr",
        target_language="de",
    ),
    _item(
        "fr-de-02",
        "Nous avons bien reçu votre paiement et nous vous en remercions.",
        "Wir haben Ihre Zahlung erhalten und danken Ihnen dafür.",
        language="fr",
        target_language="de",
    ),
    _item(
        "fr-de-03",
        "Le devis que vous nous avez transmis dépasse notre budget annuel.",
        "Der Kostenvoranschlag, den Sie uns übermittelt haben, übersteigt "
        "unser Jahresbudget.",
        language="fr",
        target_language="de",
    ),
    _item(
        "fr-de-04",
        "Merci de nous indiquer un créneau disponible la semaine prochaine.",
        "Bitte teilen Sie uns einen freien Termin in der nächsten Woche mit.",
        language="fr",
        target_language="de",
    ),
    _item(
        "fr-de-05",
        "La réunion de lancement se tiendra dans nos locaux à dix heures.",
        "Das Auftaktgespräch findet um zehn Uhr in unseren Räumen statt.",
        language="fr",
        target_language="de",
    ),
    _item(
        "fr-de-06",
        "Notre équipe technique examinera votre demande dès demain matin.",
        "Unser technisches Team wird Ihre Anfrage gleich morgen früh prüfen.",
        language="fr",
        target_language="de",
    ),
    _item(
        "fr-de-07",
        "Veuillez nous retourner le document signé avant vendredi.",
        "Bitte senden Sie uns das unterschriebene Dokument vor Freitag zurück.",
        language="fr",
        target_language="de",
    ),
    # de -> en
    _item(
        "de-en-01",
        "Die Rechnung für das dritte Quartal wurde gestern versendet.",
        "The invoice for the third quarter was sent yesterday.",
        language="de",
        target_language="en",
    ),
    _item(
        "de-en-02",
        "Wir bitten Sie, die beigefügten Unterlagen bis Montag zu prüfen.",
        "We ask you to review the attached documents by Monday.",
        language="de",
        target_language="en",
    ),
    _item(
        "de-en-03",
        "Der Liefertermin verschiebt sich um zwei Wochen nach hinten.",
        "The delivery date is being pushed back by two weeks.",
        language="de",
        target_language="en",
    ),
    _item(
        "de-en-04",
        "Unser Angebot gilt bis zum Ende des laufenden Monats.",
        "Our offer is valid until the end of the current month.",
        language="de",
        target_language="en",
    ),
    _item(
        "de-en-05",
        "Bitte richten Sie Ihre Fragen künftig an unsere Serviceabteilung.",
        "Please direct your questions to our service department from now on.",
        language="de",
        target_language="en",
    ),
    _item(
        "de-en-06",
        "Die Schulung für die neuen Mitarbeiter beginnt am Dienstagmorgen.",
        "The training for the new employees starts on Tuesday morning.",
        language="de",
        target_language="en",
    ),
    _item(
        "de-en-07",
        "Wir haben Ihre Adressänderung im System hinterlegt.",
        "We have recorded your change of address in the system.",
        language="de",
        target_language="en",
    ),
]

# The three directions this suite declares, in the cycle order above. A
# fourth pair appearing here is a suite edit, not a tag typo to be tolerated.
DIRECTIONS: tuple[tuple[str, str], ...] = (("en", "fr"), ("fr", "de"), ("de", "en"))

# Hashed through `classification_suite.prompt_set_hash`, not a second hashing
# rule of this suite's own, so two published `prompt_set_hash` values are
# comparable. Editing any prompt moves this hash and must move
# `SUITE_VERSION` with it (Methodology 2).
PROMPT_SET_HASH = prompt_set_hash(TRANSLATION_TASK_SUITE)
