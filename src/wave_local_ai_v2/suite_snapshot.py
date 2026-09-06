"""Suite definition snapshots: each task suite as the code holds it at
export time.

These are snapshots, not a live registry: a bundle reader resolving a
published row's `suite_id`/`suite_version` reads the exported JSON file
directly, without importing the suite module or checking out the commit that
produced it. Each file captures what its suite looked like at export time; it
is not consulted at read time by anything the suite itself runs through (that
would make it a registry, out of this module's scope per plan.md's
Decisions).

Two suites are exported now, classification and translation, under one
snapshot rule: identity, caps, and every item reduced to the fields a bundle
reader needs. Only the per-item field tuple differs, because the two suites
carry different item shapes -- an expected label on one, a reference
translation and a target language on the other. The rule did not change to
accommodate the second suite; it was parameterised.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import classification_suite, translation_suite

SUITE_DEFINITIONS_DIR = Path("aidd_docs/results/suite-definitions")

# The fields a bundle reader needs per item -- no derived or transient field
# (nothing `_item()` computes at import time beyond these).
CLASSIFICATION_ITEM_FIELDS = (
    "item_id",
    "prompt",
    "expected_label",
    "language",
    "provenance",
    "contamination_risk",
)
TRANSLATION_ITEM_FIELDS = (
    "item_id",
    "prompt",
    "source_text",
    "reference",
    "language",
    "target_language",
    "provenance",
    "contamination_risk",
)


def build_snapshot(
    *,
    suite_id: str,
    suite_version: str,
    prompt_set_hash: str,
    max_output_tokens: int,
    stop_sequences: Sequence[str],
    context_length: int,
    items: Sequence[Mapping[str, Any]],
    item_fields: Sequence[str],
) -> dict[str, Any]:
    """Return one suite's identity, caps and every item, plain-dict shaped."""
    return {
        "suite_id": suite_id,
        "suite_version": suite_version,
        "prompt_set_hash": prompt_set_hash,
        "max_output_tokens": max_output_tokens,
        "stop_sequences": list(stop_sequences),
        "context_length": context_length,
        "items": [{field: item[field] for field in item_fields} for item in items],
    }


def classification_snapshot() -> dict[str, Any]:
    """The classification suite, snapshot-shaped."""
    return build_snapshot(
        suite_id=classification_suite.SUITE_ID,
        suite_version=classification_suite.SUITE_VERSION,
        prompt_set_hash=classification_suite.PROMPT_SET_HASH,
        max_output_tokens=classification_suite.MAX_OUTPUT_TOKENS,
        stop_sequences=classification_suite.STOP_SEQUENCES,
        context_length=classification_suite.CONTEXT_LENGTH,
        items=classification_suite.CLASSIFICATION_TASK_SUITE,
        item_fields=CLASSIFICATION_ITEM_FIELDS,
    )


def translation_snapshot() -> dict[str, Any]:
    """The translation suite, snapshot-shaped."""
    return build_snapshot(
        suite_id=translation_suite.SUITE_ID,
        suite_version=translation_suite.SUITE_VERSION,
        prompt_set_hash=translation_suite.PROMPT_SET_HASH,
        max_output_tokens=translation_suite.MAX_OUTPUT_TOKENS,
        stop_sequences=translation_suite.STOP_SEQUENCES,
        context_length=translation_suite.CONTEXT_LENGTH,
        items=translation_suite.TRANSLATION_TASK_SUITE,
        item_fields=TRANSLATION_ITEM_FIELDS,
    )


SNAPSHOT_BUILDERS = (classification_snapshot, translation_snapshot)


def main() -> None:
    SUITE_DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)
    for builder in SNAPSHOT_BUILDERS:
        snapshot = builder()
        out_path = SUITE_DEFINITIONS_DIR / f"{snapshot['suite_id']}.json"
        out_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(out_path)


if __name__ == "__main__":
    main()
    sys.exit(0)
