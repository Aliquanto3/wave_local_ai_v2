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

`baseline` is the only entry today. The other three variants the epic
declares (`constrained_output`, `output_compressed`, `input_compressed`) are
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

TRANSFORMATION_IDENTITY = "identity"


class PromptVariantError(ValueError):
    """Raised for a registry entry that fails its check, or an unknown variant."""


@dataclass(frozen=True)
class PromptVariant:
    """One registered variant at one version."""

    variant_id: str
    version: str
    definition: Mapping[str, Any]
    definition_hash: str


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


def apply_variant(variant: PromptVariant, authored_prompt: str) -> str:
    """The prompt `variant` makes of `authored_prompt`, before any templating.

    The one place a variant is applied: every writer's subject call sends
    what this returns, and every row publishes it as `prompt_before_template`.
    """
    transform = _TRANSFORMATIONS[variant.definition["transformation"]]
    return transform(authored_prompt)


def _identity(prompt: str) -> str:
    return prompt


# The transformation each definition names, by its `transformation` key.
_TRANSFORMATIONS: dict[str, Callable[[str], str]] = {
    TRANSFORMATION_IDENTITY: _identity,
}

REGISTRY: Mapping[tuple[str, str], PromptVariant] = load_registry(REGISTERED_VARIANTS)
