import hashlib

import pytest

from wave_local_ai_v2 import prompt_variants
from wave_local_ai_v2.prompt_variants import (
    BASELINE_ID,
    CONSTRAINED_OUTPUT_ID,
    OUTPUT_COMPRESSED_ID,
    REGISTERED_VARIANTS,
    PromptVariantError,
    applies,
    apply_variant,
    constraint_for,
    constraint_mechanisms,
    definition_hash,
    load_registry,
    resolve,
)


def _entry(**changes) -> dict:
    entry = dict(REGISTERED_VARIANTS[0])
    entry["definition"] = dict(entry["definition"])
    entry.update(changes)
    return entry


def test_the_tracked_registry_holds_baseline_version_1_as_the_identity() -> None:
    assert set(prompt_variants.REGISTRY) == {
        (BASELINE_ID, "1"),
        (OUTPUT_COMPRESSED_ID, "1"),
        (CONSTRAINED_OUTPUT_ID, "1"),
    }
    baseline = resolve(BASELINE_ID)
    assert baseline.version == "1"
    assert baseline.definition["transformation"] == "identity"
    assert baseline.definition_hash == definition_hash(baseline.definition)


def test_baseline_returns_the_authored_prompt_unchanged() -> None:
    authored = "Classify this message: «Où est ma facture ?»\n"
    for family in ("classification", "translation", None):
        application = apply_variant(resolve(BASELINE_ID, "1"), authored, family)
        assert application.prompt == authored
        assert application.noop is False


def test_output_compressed_appends_its_declared_instruction_on_classification() -> None:
    variant = resolve(OUTPUT_COMPRESSED_ID, "1")
    instruction = variant.definition["instruction"]
    authored = "Classify this message: «Où est ma facture ?»"

    application = apply_variant(variant, authored, "classification")

    # The wording is the definition: what is sent is the authored text, the
    # separator, and exactly that instruction, hashed with the entry.
    assert application.prompt == f"{authored}\n\n{instruction}"
    assert application.noop is False
    assert variant.definition["applies_to"] == ["classification"]
    assert variant.definition["applicability_reason"].strip()
    assert variant.definition_hash == definition_hash(variant.definition)


CLASSIFICATION_GRAMMAR = 'root ::= "account" | "billing" | "other" | "technical"'


def _constrained_entry(**format_changes) -> dict:
    entry = dict(REGISTERED_VARIANTS[2])
    definition = dict(entry["definition"])
    output_format = {**definition["output_formats"]["classification"], **format_changes}
    definition["output_formats"] = {"classification": output_format}
    entry["definition"] = definition
    entry["definition_hash"] = definition_hash(definition)
    return entry


def test_constrained_output_declares_a_gbnf_grammar_for_classification_only() -> None:
    variant = resolve(CONSTRAINED_OUTPUT_ID, "1")
    authored = "Classify this message: «Où est ma facture ?»"

    constraint = constraint_for(variant, "classification")

    assert constraint is not None
    assert constraint.mechanism == "gbnf"
    assert constraint.grammar == CLASSIFICATION_GRAMMAR
    assert (
        constraint.grammar_hash
        == hashlib.sha256(CLASSIFICATION_GRAMMAR.encode("utf-8")).hexdigest()
    )
    # No instruction is added: the authored prompt already states the format.
    assert apply_variant(variant, authored, "classification").prompt == authored
    assert apply_variant(variant, authored, "classification").noop is False
    assert constraint_mechanisms(variant) == frozenset({"gbnf"})
    assert variant.definition_hash == definition_hash(variant.definition)


@pytest.mark.parametrize("family", ["translation", "judge-probe", None])
def test_constrained_output_is_a_noop_without_a_grammar_outside_its_families(
    family,
) -> None:
    variant = resolve(CONSTRAINED_OUTPUT_ID, "1")

    assert constraint_for(variant, family) is None
    assert apply_variant(variant, "Translate: hello", family).noop is True


@pytest.mark.parametrize("variant_id", [BASELINE_ID, OUTPUT_COMPRESSED_ID])
def test_a_variant_without_output_formats_declares_no_constraint(variant_id) -> None:
    variant = resolve(variant_id)

    assert constraint_for(variant, "classification") is None
    assert constraint_mechanisms(variant) == frozenset()


def test_a_format_instruction_when_declared_is_appended_and_visible() -> None:
    registry = load_registry([_constrained_entry(instruction="Answer: one label.")])
    variant = registry[(CONSTRAINED_OUTPUT_ID, "1")]

    application = apply_variant(variant, "Classify: x", "classification")

    assert application.prompt == "Classify: x\n\nAnswer: one label."


@pytest.mark.parametrize(
    "format_changes",
    [
        {"format": " "},
        {"instruction": ""},
        {"constraint": {"mechanism": "json_schema", "grammar": "{}"}},
        {"constraint": {"mechanism": "gbnf", "grammar": ""}},
        {"constraint": None},
    ],
)
def test_a_malformed_output_format_is_refused_at_load(format_changes) -> None:
    with pytest.raises(PromptVariantError, match="malformed output format"):
        load_registry([_constrained_entry(**format_changes)])


def test_an_output_format_without_its_instruction_key_is_refused() -> None:
    entry = _constrained_entry()
    del entry["definition"]["output_formats"]["classification"]["instruction"]
    entry["definition_hash"] = definition_hash(entry["definition"])

    with pytest.raises(PromptVariantError, match="malformed output format"):
        load_registry([entry])


def test_formats_must_match_the_declared_families() -> None:
    entry = _constrained_entry()
    entry["definition"]["applies_to"] = ["classification", "translation"]
    entry["definition_hash"] = definition_hash(entry["definition"])

    with pytest.raises(PromptVariantError, match="exactly one format"):
        load_registry([entry])


def test_a_constraining_variant_without_applies_to_is_refused() -> None:
    entry = _constrained_entry()
    del entry["definition"]["applies_to"]
    del entry["definition"]["applicability_reason"]
    entry["definition_hash"] = definition_hash(entry["definition"])

    with pytest.raises(PromptVariantError, match="must declare applies_to"):
        load_registry([entry])


@pytest.mark.parametrize("family", ["translation", "judge-probe", None])
def test_output_compressed_records_a_noop_outside_its_declared_families(
    family,
) -> None:
    variant = resolve(OUTPUT_COMPRESSED_ID, "1")
    authored = "Translate into French: the invoice is attached."

    application = apply_variant(variant, authored, family)

    assert application.prompt == authored
    assert application.noop is True
    assert applies(variant, family) is False


@pytest.mark.parametrize(
    "applies_to",
    [[], "classification", [""], [3]],
)
def test_a_malformed_applicability_is_refused_at_load(applies_to) -> None:
    definition = {
        "transformation": "identity",
        "applies_to": applies_to,
        "applicability_reason": "why",
    }
    entry = _entry(definition=definition, definition_hash=definition_hash(definition))

    with pytest.raises(PromptVariantError, match="applies_to"):
        load_registry([entry])


def test_an_applicability_without_its_reason_is_refused_at_load() -> None:
    definition = {"transformation": "identity", "applies_to": ["classification"]}
    entry = _entry(definition=definition, definition_hash=definition_hash(definition))

    with pytest.raises(PromptVariantError, match="applicability_reason"):
        load_registry([entry])


def test_an_edited_definition_at_an_unchanged_version_is_refused_naming_it() -> None:
    edited = _entry()
    edited["definition"]["description"] = "Quietly reworded."

    with pytest.raises(PromptVariantError) as excinfo:
        load_registry([edited])

    message = str(excinfo.value)
    assert "'baseline'" in message
    assert "'1'" in message
    assert "without a version bump" in message


def test_a_bumped_version_with_its_new_hash_loads_beside_its_predecessor() -> None:
    bumped_definition = {**REGISTERED_VARIANTS[0]["definition"], "description": "v2"}
    bumped = _entry(
        version="2",
        definition=bumped_definition,
        definition_hash=definition_hash(bumped_definition),
    )

    registry = load_registry([REGISTERED_VARIANTS[0], bumped])

    assert set(registry) == {(BASELINE_ID, "1"), (BASELINE_ID, "2")}


def test_an_id_and_version_declared_twice_is_refused() -> None:
    with pytest.raises(PromptVariantError, match="declared twice"):
        load_registry([REGISTERED_VARIANTS[0], REGISTERED_VARIANTS[0]])


def test_an_unknown_transformation_is_refused_at_load() -> None:
    definition = {"transformation": "rewrite_everything"}
    entry = _entry(definition=definition, definition_hash=definition_hash(definition))

    with pytest.raises(PromptVariantError, match="unknown transformation"):
        load_registry([entry])


def test_an_unregistered_variant_is_refused_naming_it() -> None:
    with pytest.raises(PromptVariantError, match="'input_compressed' is not in"):
        resolve("input_compressed")


def test_an_unregistered_version_is_refused_naming_it() -> None:
    with pytest.raises(PromptVariantError, match="no registered version '9'"):
        resolve(BASELINE_ID, "9")


def test_resolve_without_a_version_takes_the_latest(monkeypatch) -> None:
    bumped_definition = {**REGISTERED_VARIANTS[0]["definition"], "description": "v2"}
    registry = load_registry(
        [
            REGISTERED_VARIANTS[0],
            _entry(
                version="2",
                definition=bumped_definition,
                definition_hash=definition_hash(bumped_definition),
            ),
        ]
    )
    monkeypatch.setattr(prompt_variants, "REGISTRY", registry)

    assert resolve(BASELINE_ID).version == "2"
