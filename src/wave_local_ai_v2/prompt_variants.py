"""The prompt variant registry: every declared transformation of an item's
authored prompt, each versioned like a prompt template (Methodology 2, 22).

A variant transforms the prompt and nothing else -- never the scorer, the
expected output, the parser, the generation caps or the item set. It is
applied to the authored prompt *before* the engine's own templating, through
`apply_variant` and nowhere else, so the string a row publishes as `prompt`
is what the engine finally received and a variant's effect is visible in it
rather than claimed about it.

Each entry carries its id, its version, its definition and a content hash of
that definition. The registry is checked when this module loads: an entry
whose definition no longer hashes to the hash it declares was edited without
a version bump, and the import fails naming it -- the same rule an edited
suite prompt is held to. Changing a definition therefore means bumping its
version *and* recording the new hash, which leaves the old (id, version)
naming the definition its published rows ran under.

A definition may declare the task families (a suite's `task_suite`) it
`applies_to`, with its `applicability_reason`; one that declares none applies
to every family. A variant never removes an item: an item of a family it does
not apply to is still run, with the authored prompt unchanged, and its row
records that the transformation was a no-op.

`baseline` and `output_compressed` are registered today. The other two
variants the epic declares (`constrained_output`, `input_compressed`) are
added by their own stories.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

BASELINE_ID = "baseline"
OUTPUT_COMPRESSED_ID = "output_compressed"

TRANSFORMATION_IDENTITY = "identity"
TRANSFORMATION_APPEND_INSTRUCTION = "append_instruction"

# What separates the authored prompt from an appended instruction.
INSTRUCTION_SEPARATOR = "\n\n"


class PromptVariantError(ValueError):
    """Raised for a registry entry that fails its check, or an unknown variant."""


@dataclass(frozen=True)
class PromptVariant:
    """One registered variant at one version."""

    variant_id: str
    version: str
    definition: Mapping[str, Any]
    definition_hash: str


@dataclass(frozen=True)
class VariantApplication:
    """What a variant made of one authored prompt, and whether it skipped it.

    `noop` is true when the item's task family is outside the variant's
    declared `applies_to`: the transformation was not applied and `prompt`
    is the authored text.
    """

    prompt: str
    noop: bool


def definition_hash(definition: Mapping[str, Any]) -> str:
    """SHA-256 hex digest of `definition` as canonical JSON (sorted keys)."""
    canonical = json.dumps(
        dict(definition), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# The tracked registry. Editing a `definition` here without bumping its
# `version` (and recording the new `definition_hash`) fails the import.
REGISTERED_VARIANTS: tuple[Mapping[str, Any], ...] = (
    {
        "variant_id": BASELINE_ID,
        "version": "1",
        "definition": {
            "transformation": TRANSFORMATION_IDENTITY,
            "description": (
                "The item's authored prompt, unchanged: the reference arm "
                "every other variant is compared against."
            ),
        },
        "definition_hash": (
            "aea6cde7c1e788c7a9c47050ec7888d8dce7963b95814e5b3f2cd47d8a69ea93"  # pragma: allowlist secret
        ),
    },
    {
        "variant_id": OUTPUT_COMPRESSED_ID,
        "version": "1",
        "definition": {
            "transformation": TRANSFORMATION_APPEND_INSTRUCTION,
            "instruction": (
                "Answer as tersely as possible: no greeting, no explanation, "
                "no filler words, no full sentences. Output only what the task "
                "asks for."
            ),
            "applies_to": ["classification"],
            "applicability_reason": (
                "A classification answer is one label scored by exact match, so "
                "a terse-output instruction can only change how the label is "
                "worded around, and the test behind the family reads the "
                "effect. A translation's length is set by its source and its "
                "reference, so a terse instruction could only remove content "
                "the reference requires: the variant records a no-op there."
            ),
            "description": (
                "The item's authored prompt followed by a terse-output "
                "(Caveman-style) instruction: does telling a small model to "
                "answer tersely help or hurt it?"
            ),
        },
        "definition_hash": (
            "f210943107058d5a9ebbbac26eee312b01f3220bfe874e56676d0fa41c69388c"  # pragma: allowlist secret
        ),
    },
)


def load_registry(
    entries: Iterable[Mapping[str, Any]],
) -> Mapping[tuple[str, str], PromptVariant]:
    """Check every entry and index it by (id, version), or raise naming it.

    Refused: a definition that does not hash to its declared hash (edited
    without a version bump), and an (id, version) pair declared twice.
    """
    registry: dict[tuple[str, str], PromptVariant] = {}
    for entry in entries:
        variant = PromptVariant(
            variant_id=entry["variant_id"],
            version=entry["version"],
            definition=MappingProxyType(dict(entry["definition"])),
            definition_hash=entry["definition_hash"],
        )
        key = (variant.variant_id, variant.version)
        if key in registry:
            raise PromptVariantError(
                f"prompt variant {variant.variant_id!r} version "
                f"{variant.version!r} is declared twice"
            )
        actual = definition_hash(variant.definition)
        if actual != variant.definition_hash:
            raise PromptVariantError(
                f"prompt variant {variant.variant_id!r} version "
                f"{variant.version!r} has a definition hashing to {actual} but "
                f"declares {variant.definition_hash}: its definition was edited "
                "without a version bump"
            )
        applies_to = variant.definition.get("applies_to")
        if applies_to is not None and (
            not isinstance(applies_to, list)
            or not applies_to
            or not all(isinstance(family, str) and family for family in applies_to)
            or not isinstance(variant.definition.get("applicability_reason"), str)
            or not variant.definition["applicability_reason"].strip()
        ):
            raise PromptVariantError(
                f"prompt variant {variant.variant_id!r} version "
                f"{variant.version!r} declares applies_to {applies_to!r}: it "
                "must be a non-empty list of task families with a non-empty "
                "applicability_reason"
            )
        if variant.definition.get("transformation") not in _TRANSFORMATIONS:
            raise PromptVariantError(
                f"prompt variant {variant.variant_id!r} version "
                f"{variant.version!r} declares an unknown transformation "
                f"{variant.definition.get('transformation')!r}"
            )
        registry[key] = variant
    return MappingProxyType(registry)


def resolve(variant_id: str, version: str | None = None) -> PromptVariant:
    """The registered variant `variant_id` at `version` (latest when None).

    Raises `PromptVariantError` naming the id, or the version, that the
    registry does not hold.
    """
    versions = [variant for key, variant in REGISTRY.items() if key[0] == variant_id]
    if not versions:
        raise PromptVariantError(
            f"prompt variant {variant_id!r} is not in the registry"
        )
    if version is None:
        return max(versions, key=lambda variant: int(variant.version))
    for variant in versions:
        if variant.version == version:
            return variant
    raise PromptVariantError(
        f"prompt variant {variant_id!r} has no registered version {version!r}"
    )


def applies(variant: PromptVariant, task_family: str | None) -> bool:
    """Whether `variant` transforms a prompt of `task_family`.

    A definition declaring no `applies_to` applies to every family, and to a
    prompt that belongs to none (`None`: the runtime benchmark's fixed
    prompt); one declaring a list applies only to the families it names.
    """
    applies_to = variant.definition.get("applies_to")
    return applies_to is None or task_family in applies_to


def apply_variant(
    variant: PromptVariant, authored_prompt: str, task_family: str | None
) -> VariantApplication:
    """What `variant` makes of `authored_prompt`, before any templating.

    The one place a variant is applied: every writer's subject call sends
    the returned `prompt`, and every row publishes it as
    `prompt_before_template` beside the returned `noop`. Outside the
    variant's declared families the authored text comes back unchanged and
    `noop` is true: the item is still run, never dropped.
    """
    if not applies(variant, task_family):
        return VariantApplication(prompt=authored_prompt, noop=True)
    transform = _TRANSFORMATIONS[variant.definition["transformation"]]
    return VariantApplication(
        prompt=transform(variant.definition, authored_prompt), noop=False
    )


def _identity(definition: Mapping[str, Any], prompt: str) -> str:
    return prompt


def _append_instruction(definition: Mapping[str, Any], prompt: str) -> str:
    return f"{prompt}{INSTRUCTION_SEPARATOR}{definition['instruction']}"


# The transformation each definition names, by its `transformation` key.
_TRANSFORMATIONS: dict[str, Callable[[Mapping[str, Any], str], str]] = {
    TRANSFORMATION_IDENTITY: _identity,
    TRANSFORMATION_APPEND_INSTRUCTION: _append_instruction,
}

REGISTRY: Mapping[tuple[str, str], PromptVariant] = load_registry(REGISTERED_VARIANTS)
