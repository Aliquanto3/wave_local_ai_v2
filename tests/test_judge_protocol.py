import os
from unittest.mock import patch

import pytest

from wave_local_ai_v2 import prompt_provenance
from wave_local_ai_v2.judge_protocol import (
    JUDGE_LANGUAGES,
    JUDGE_PROMPT_TEMPLATES,
    JUDGE_TEMPLATE_HASHES,
    OPEN_ENDED_QUALITY_1_TO_5,
    RUBRIC_KIND_CATEGORICAL,
    RUBRIC_KIND_ORDINAL_1_5,
    Rubric,
    UnsupportedJudgeLanguageError,
    render_judge_prompt,
    rubric_text_for,
    template_for,
)

ITEM_PROMPT = "Rewrite this sentence so a beginner understands it."
SUBJECT_OUTPUT = "Here is a simpler version of the sentence."


def _render(language: str):
    return render_judge_prompt(
        rubric=OPEN_ENDED_QUALITY_1_TO_5,
        language=language,
        item_prompt=ITEM_PROMPT,
        subject_output=SUBJECT_OUTPUT,
    )


def test_every_shell_carries_exactly_the_three_slots() -> None:
    for language in JUDGE_LANGUAGES:
        shell = JUDGE_PROMPT_TEMPLATES[language]
        for slot in ("{{rubric}}", "{{item_prompt}}", "{{subject_output}}"):
            assert shell.count(slot) == 1, f"{language} shell: {slot}"


def test_a_french_item_is_rendered_from_the_french_shell() -> None:
    rendered = _render("fr")

    assert rendered["template_id"] == "judge-prompt-fr"
    assert "Barème :" in rendered["prompt"]
    assert "Rubric:" not in rendered["prompt"]
    assert ITEM_PROMPT in rendered["prompt"]
    assert SUBJECT_OUTPUT in rendered["prompt"]


def test_a_german_item_carries_the_german_id_and_its_own_hash() -> None:
    german = _render("de")
    french = _render("fr")

    assert german["template_id"] == "judge-prompt-de"
    assert german["template_hash"] != french["template_hash"]


def test_editing_a_shell_moves_its_hash_and_not_the_rubric_version() -> None:
    edited_shell = JUDGE_PROMPT_TEMPLATES["en"] + "\nAnswer carefully.\n"

    assert prompt_provenance.template_hash(edited_shell) != JUDGE_TEMPLATE_HASHES["en"]
    assert _render("en")["rubric_version"] == OPEN_ENDED_QUALITY_1_TO_5.version


def test_revising_the_rubric_moves_its_version_and_not_the_template_hashes() -> None:
    revised = Rubric(
        rubric_id=OPEN_ENDED_QUALITY_1_TO_5.rubric_id,
        version="2",
        kind=OPEN_ENDED_QUALITY_1_TO_5.kind,
        scale=OPEN_ENDED_QUALITY_1_TO_5.scale,
        categories=None,
        text={
            language: text + "\nBe strict."
            for language, text in OPEN_ENDED_QUALITY_1_TO_5.text.items()
        },
    )

    rendered = render_judge_prompt(
        rubric=revised,
        language="en",
        item_prompt=ITEM_PROMPT,
        subject_output=SUBJECT_OUTPUT,
    )

    assert rendered["rubric_version"] == "2"
    assert rendered["template_hash"] == JUDGE_TEMPLATE_HASHES["en"]


def test_the_recorded_hash_is_the_shell_not_the_filled_prompt() -> None:
    rendered = _render("en")

    assert (
        prompt_provenance.template_hash(rendered["prompt"]) != rendered["template_hash"]
    )


def test_a_language_with_no_shell_is_refused_by_name() -> None:
    with pytest.raises(UnsupportedJudgeLanguageError, match="'es'"):
        template_for("es")


def test_a_rubric_with_no_text_for_the_language_is_refused_by_name() -> None:
    english_only = Rubric(
        rubric_id="english-only",
        version="1",
        kind=RUBRIC_KIND_ORDINAL_1_5,
        scale=(1, 2, 3, 4, 5),
        categories=None,
        text={"en": "Score 1 to 5."},
    )

    with pytest.raises(UnsupportedJudgeLanguageError, match="'fr'"):
        rubric_text_for(english_only, "fr")


def test_rendering_an_unsupported_language_refuses_before_rendering() -> None:
    with pytest.raises(UnsupportedJudgeLanguageError, match="'es'"):
        _render("es")


def test_an_ordinal_rubric_carrying_categories_is_refused() -> None:
    with pytest.raises(ValueError, match="ordinal_1_5"):
        Rubric(
            rubric_id="mismatched",
            version="1",
            kind=RUBRIC_KIND_ORDINAL_1_5,
            scale=(1, 2, 3),
            categories=frozenset({"good"}),
            text={"en": "..."},
        )


def test_a_categorical_rubric_carrying_a_scale_is_refused() -> None:
    with pytest.raises(ValueError, match="categorical"):
        Rubric(
            rubric_id="mismatched",
            version="1",
            kind=RUBRIC_KIND_CATEGORICAL,
            scale=(1, 2, 3),
            categories=frozenset({"good"}),
            text={"en": "..."},
        )


def test_a_rubric_of_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="ternary"):
        Rubric(
            rubric_id="mismatched",
            version="1",
            kind="ternary",
            scale=(1, 2, 3),
            categories=None,
            text={"en": "..."},
        )


def test_an_ordinal_rubric_with_no_scale_is_refused() -> None:
    with pytest.raises(ValueError, match="ordinal_1_5"):
        Rubric(
            rubric_id="mismatched",
            version="1",
            kind=RUBRIC_KIND_ORDINAL_1_5,
            scale=None,
            categories=None,
            text={"en": "..."},
        )


def test_a_categorical_rubric_with_no_categories_is_refused() -> None:
    with pytest.raises(ValueError, match="categorical"):
        Rubric(
            rubric_id="mismatched",
            version="1",
            kind=RUBRIC_KIND_CATEGORICAL,
            scale=None,
            categories=None,
            text={"en": "..."},
        )


def test_a_subject_output_containing_a_slot_marker_is_not_re_substituted() -> None:
    # One pass over the shell, not chained replaces: an output quoting the
    # marker text must land in the prompt verbatim, not rewrite the prompt.
    rendered = render_judge_prompt(
        rubric=OPEN_ENDED_QUALITY_1_TO_5,
        language="en",
        item_prompt=ITEM_PROMPT,
        subject_output="{{rubric}}",
    )

    assert rendered["prompt"].count(OPEN_ENDED_QUALITY_1_TO_5.text["en"]) == 1
    assert rendered["prompt"].endswith("{{rubric}}\n")


# --- The stable prefix: instructions and rubric first, item text after ---

_ITEM_SLOTS = ("{{item_prompt}}", "{{subject_output}}")


@pytest.mark.parametrize("language", JUDGE_LANGUAGES)
def test_every_shell_places_the_rubric_before_every_item_slot(language) -> None:
    shell = JUDGE_PROMPT_TEMPLATES[language]
    rubric_at = shell.index("{{rubric}}")

    for slot in _ITEM_SLOTS:
        assert rubric_at < shell.index(slot), (
            f"{language} shell places {slot} before the rubric: the judge "
            "prompt would lose its stable prefix"
        )


@pytest.mark.parametrize("language", JUDGE_LANGUAGES)
def test_two_items_share_a_byte_identical_prefix_ending_after_the_rubric(
    language,
) -> None:
    first = render_judge_prompt(
        rubric=OPEN_ENDED_QUALITY_1_TO_5,
        language=language,
        item_prompt="Summarise the attached meeting notes in two sentences.",
        subject_output="The team agreed to ship on Friday.",
    )["prompt"]
    second = render_judge_prompt(
        rubric=OPEN_ENDED_QUALITY_1_TO_5,
        language=language,
        item_prompt="Write a polite reply declining the invitation.",
        subject_output="Thank you, but I cannot attend.",
    )["prompt"]

    shell = JUDGE_PROMPT_TEMPLATES[language]
    rubric_slot = "{{rubric}}"
    before_rubric = shell[: shell.index(rubric_slot)]
    # Everything up to the first item slot: the instructions, the rubric and
    # the shell's own heading for the item, all item-independent.
    after_rubric = shell[
        shell.index(rubric_slot) + len(rubric_slot) : shell.index("{{item_prompt}}")
    ]
    expected_prefix = (
        before_rubric
        + rubric_text_for(OPEN_ENDED_QUALITY_1_TO_5, language)
        + after_rubric
    )

    assert first.startswith(expected_prefix)
    assert second.startswith(expected_prefix)
    # The shared prefix ends exactly where the first item substitution starts.
    shared = os.path.commonprefix([first, second])
    assert shared == expected_prefix


def test_a_shell_with_an_item_slot_before_the_rubric_breaks_the_prefix() -> None:
    # The counter-example the ordering test above exists to catch: with the
    # item first, two items' prompts diverge before the rubric is reached.
    misordered = "Task:\n{{item_prompt}}\nRubric:\n{{rubric}}\n{{subject_output}}\n"

    assert misordered.index("{{item_prompt}}") < misordered.index("{{rubric}}")
    with patch.dict(JUDGE_PROMPT_TEMPLATES, {"en": misordered}):
        first = _render("en")["prompt"]
        second = render_judge_prompt(
            rubric=OPEN_ENDED_QUALITY_1_TO_5,
            language="en",
            item_prompt="A different task entirely.",
            subject_output=SUBJECT_OUTPUT,
        )["prompt"]
    rubric_text = rubric_text_for(OPEN_ENDED_QUALITY_1_TO_5, "en")

    assert rubric_text not in os.path.commonprefix([first, second])
