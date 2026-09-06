"""The judge prompt: one shell per language, the rubric it carries, and the
two identities a judged row publishes.

Two independence rules hold the provenance apart. The shell is hashed and the
rubric is not, so revising the rubric text moves `rubric_version` and leaves
`template_hash` byte-identical; editing a shell moves its hash and leaves the
rubric version alone. And the hash is content-derived over the shell only,
never over the filled prompt, so a row written before a shell edit stays
attributable to the text it actually used rather than to whatever the shell
says today.

No provider is named here and no call is made: this module renders text and
refuses a language it has no variant for. An item is never judged in English
by default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, TypedDict

from wave_local_ai_v2 import prompt_provenance

JudgeLanguage = Literal["en", "fr", "de"]

# The languages the classification suite already publishes items in
# (`suite_gate.LANGUAGES`), restated here as the judge path's own literal
# rather than imported: a suite adding a fourth language must add a shell and
# a rubric text for it deliberately, not inherit an English fallback.
JUDGE_LANGUAGES: tuple[JudgeLanguage, ...] = ("en", "fr", "de")

# The three substitution slots every shell carries. Filled in one pass
# (`_fill`) rather than by chained `str.replace` or `str.format`: a subject
# output that happens to contain `{{rubric}}`, or a brace of its own, must not
# be able to rewrite the prompt around it.
SLOT_RUBRIC = "rubric"
SLOT_ITEM_PROMPT = "item_prompt"
SLOT_SUBJECT_OUTPUT = "subject_output"
_SLOT_PATTERN = re.compile(
    rf"\{{\{{({SLOT_RUBRIC}|{SLOT_ITEM_PROMPT}|{SLOT_SUBJECT_OUTPUT})\}}\}}"
)

# One shell per language, each written in that language. The shell holds the
# framing and the "answer in the form the rubric asks for" instruction; the
# criteria and the answer form itself belong to the rubric, which is why the
# two are versioned separately.
JUDGE_PROMPT_TEMPLATES: dict[JudgeLanguage, str] = {
    "en": (
        "You are grading one answer produced by a language model. Apply the "
        "rubric below exactly as written, and answer in the form the rubric "
        "asks for, with nothing else.\n"
        "\n"
        "Rubric:\n"
        "{{rubric}}\n"
        "\n"
        "The task the model was given:\n"
        "{{item_prompt}}\n"
        "\n"
        "The answer the model produced:\n"
        "{{subject_output}}\n"
    ),
    "fr": (
        "Tu évalues une réponse produite par un modèle de langue. Applique le "
        "barème ci-dessous exactement tel qu'il est écrit, et réponds dans la "
        "forme que le barème demande, rien d'autre.\n"
        "\n"
        "Barème :\n"
        "{{rubric}}\n"
        "\n"
        "La tâche donnée au modèle :\n"
        "{{item_prompt}}\n"
        "\n"
        "La réponse produite par le modèle :\n"
        "{{subject_output}}\n"
    ),
    "de": (
        "Du bewertest eine Antwort, die ein Sprachmodell erzeugt hat. Wende "
        "die folgenden Bewertungskriterien genau so an, wie sie geschrieben "
        "sind, und antworte in der Form, die sie verlangen, sonst nichts.\n"
        "\n"
        "Bewertungskriterien:\n"
        "{{rubric}}\n"
        "\n"
        "Die Aufgabe, die das Modell erhalten hat:\n"
        "{{item_prompt}}\n"
        "\n"
        "Die Antwort, die das Modell erzeugt hat:\n"
        "{{subject_output}}\n"
    ),
}

JUDGE_TEMPLATE_IDS: dict[JudgeLanguage, str] = {
    "en": "judge-prompt-en",
    "fr": "judge-prompt-fr",
    "de": "judge-prompt-de",
}


def _shell_hash(shell: str) -> str:
    """`prompt_provenance.template_hash` over a shell, narrowed to `str`.

    That helper returns `None` only for a `None` template, which a declared
    shell never is. Guarded rather than cast, so a shell that somehow arrived
    as `None` is named here instead of publishing a null hash on every row.
    """
    digest = prompt_provenance.template_hash(shell)
    if digest is None:
        raise ValueError(f"judge prompt shell hashed to None: {shell!r}")
    return digest


# Computed at import from the shell, never from a filled prompt: a per-item
# substitution must not move the hash. One hashing helper for the whole
# project (`prompt_provenance.template_hash`), not a second one here.
JUDGE_TEMPLATE_HASHES: dict[JudgeLanguage, str] = {
    language: _shell_hash(shell) for language, shell in JUDGE_PROMPT_TEMPLATES.items()
}

RUBRIC_KIND_ORDINAL_1_5 = "ordinal_1_5"
RUBRIC_KIND_CATEGORICAL = "categorical"
RUBRIC_KINDS = (RUBRIC_KIND_ORDINAL_1_5, RUBRIC_KIND_CATEGORICAL)


class UnsupportedJudgeLanguageError(ValueError):
    """Raised when no shell, or no rubric text, covers an item's language.

    A refusal, never a fallback: judging a French item against an English
    shell would publish a score whose prompt the row cannot honestly name.
    """


@dataclass(frozen=True)
class Rubric:
    """A versioned scoring rubric: its scale or its categories, and its text.

    `version` moves when the criteria text is revised; the shells' hashes do
    not, and vice versa. `text` holds the criteria plus the answer instruction
    per language -- the shell tells the judge to answer in the form the rubric
    states, so the form is the rubric's to declare.
    """

    rubric_id: str
    version: str
    kind: str
    scale: tuple[int, ...] | None
    categories: frozenset[str] | None
    text: dict[JudgeLanguage, str]

    def __post_init__(self) -> None:
        if self.kind not in RUBRIC_KINDS:
            raise ValueError(
                f"rubric {self.rubric_id!r} has an unrecognised kind "
                f"{self.kind!r}: must be one of {', '.join(RUBRIC_KINDS)}"
            )
        if self.kind == RUBRIC_KIND_ORDINAL_1_5 and (
            self.scale is None or self.categories is not None
        ):
            raise ValueError(
                f"rubric {self.rubric_id!r} declares kind "
                f"{RUBRIC_KIND_ORDINAL_1_5!r} but carries scale="
                f"{self.scale!r} and categories={self.categories!r}: an "
                "ordinal rubric carries a scale and no categories"
            )
        if self.kind == RUBRIC_KIND_CATEGORICAL and (
            self.categories is None or self.scale is not None
        ):
            raise ValueError(
                f"rubric {self.rubric_id!r} declares kind "
                f"{RUBRIC_KIND_CATEGORICAL!r} but carries scale={self.scale!r} "
                f"and categories={self.categories!r}: a categorical rubric "
                "carries categories and no scale"
            )


# The one rubric this increment ships. Its criteria are deliberately generic
# -- did the output do what the item asked, is it correct, is it in the right
# language -- because a suite's own rubric text belongs to the suite that
# declares it, not to this module. No categorical rubric ships: the
# categorical machinery is exercised by test fixtures until a suite declares
# one.
OPEN_ENDED_QUALITY_1_TO_5 = Rubric(
    rubric_id="open-ended-quality-1to5",
    version="1",
    kind=RUBRIC_KIND_ORDINAL_1_5,
    scale=(1, 2, 3, 4, 5),
    categories=None,
    text={
        "en": (
            "Criteria:\n"
            "1. Does the answer do what the task asked for?\n"
            "2. Is the answer correct?\n"
            "3. Is the answer written in the language the task was written in?\n"
            "\n"
            "Score the answer from 1 (meets no criterion) to 5 (meets every "
            "criterion). Answer with that single integer and nothing else."
        ),
        "fr": (
            "Critères :\n"
            "1. La réponse fait-elle ce que la tâche demandait ?\n"
            "2. La réponse est-elle correcte ?\n"
            "3. La réponse est-elle rédigée dans la langue de la tâche ?\n"
            "\n"
            "Note la réponse de 1 (aucun critère respecté) à 5 (tous les "
            "critères respectés). Réponds uniquement par cet entier, rien "
            "d'autre."
        ),
        "de": (
            "Kriterien:\n"
            "1. Erfüllt die Antwort, worum die Aufgabe gebeten hat?\n"
            "2. Ist die Antwort korrekt?\n"
            "3. Ist die Antwort in der Sprache der Aufgabe verfasst?\n"
            "\n"
            "Bewerte die Antwort von 1 (kein Kriterium erfüllt) bis 5 (alle "
            "Kriterien erfüllt). Antworte ausschließlich mit dieser einen "
            "Zahl, sonst nichts."
        ),
    },
)


class RenderedJudgePrompt(TypedDict):
    """A filled judge prompt and the provenance the row publishes with it."""

    prompt: str
    template_id: str
    template_hash: str
    language: JudgeLanguage
    rubric_id: str
    rubric_version: str
    rubric_kind: str


def template_for(language: JudgeLanguage) -> str:
    """Return the shell written in `language`, or refuse naming it."""
    shell = JUDGE_PROMPT_TEMPLATES.get(language)
    if shell is None:
        raise UnsupportedJudgeLanguageError(
            f"no judge prompt shell for language {language!r} "
            f"(available: {', '.join(sorted(JUDGE_PROMPT_TEMPLATES))})"
        )
    return shell


def rubric_text_for(rubric: Rubric, language: JudgeLanguage) -> str:
    """Return `rubric`'s criteria written in `language`, or refuse naming it."""
    text = rubric.text.get(language)
    if text is None:
        raise UnsupportedJudgeLanguageError(
            f"rubric {rubric.rubric_id!r} version {rubric.version!r} has no "
            f"text for language {language!r} "
            f"(available: {', '.join(sorted(rubric.text))})"
        )
    return text


def _fill(shell: str, values: dict[str, str]) -> str:
    """Substitute every slot in `shell` in one pass over the shell's own text."""
    return _SLOT_PATTERN.sub(lambda match: values[match.group(1)], shell)


def render_judge_prompt(
    *,
    rubric: Rubric,
    language: JudgeLanguage,
    item_prompt: str,
    subject_output: str,
) -> RenderedJudgePrompt:
    """Render one judge prompt and the provenance a judged row publishes.

    `template_hash` is the shell's hash, not the filled prompt's: the prompt
    changes per item, the shell does not, and it is the shell a reader needs
    to re-derive. Refuses (`UnsupportedJudgeLanguageError`) when either the
    shell or the rubric text is missing for `language`, before anything is
    rendered.
    """
    shell = template_for(language)
    text = rubric_text_for(rubric, language)
    return RenderedJudgePrompt(
        prompt=_fill(
            shell,
            {
                SLOT_RUBRIC: text,
                SLOT_ITEM_PROMPT: item_prompt,
                SLOT_SUBJECT_OUTPUT: subject_output,
            },
        ),
        template_id=JUDGE_TEMPLATE_IDS[language],
        template_hash=JUDGE_TEMPLATE_HASHES[language],
        language=language,
        rubric_id=rubric.rubric_id,
        rubric_version=rubric.version,
        rubric_kind=rubric.kind,
    )
