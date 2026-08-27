"""Suite definition snapshot: the classification suite as the code holds it
at export time.

This is a snapshot, not a live registry: a bundle reader resolving a
published row's `suite_id`/`suite_version` reads the exported JSON file
directly, without importing `classification_suite.py` or checking out the
commit that produced it. It captures what the suite looked like at export
time; it is not consulted at read time by anything the suite itself runs
through (that would make it a registry, out of this module's scope per
plan.md's Decisions -- one small module, one suite, no new CLI entry point).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from wave_local_ai_v2.classification_suite import (
    CLASSIFICATION_TASK_SUITE,
    CONTEXT_LENGTH,
    MAX_OUTPUT_TOKENS,
    PROMPT_SET_HASH,
    STOP_SEQUENCES,
    SUITE_ID,
    SUITE_VERSION,
)

SUITE_DEFINITIONS_DIR = Path("aidd_docs/results/suite-definitions")

# The six fields a bundle reader needs per item -- no derived or transient
# field (nothing `_item()` computes at import time beyond these).
_ITEM_FIELDS = (
    "item_id",
    "prompt",
    "expected_label",
    "language",
    "provenance",
    "contamination_risk",
)


def build_snapshot() -> dict[str, Any]:
    """Return the suite's identity, caps and every item, plain-dict shaped."""
    return {
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "prompt_set_hash": PROMPT_SET_HASH,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "stop_sequences": list(STOP_SEQUENCES),
        "context_length": CONTEXT_LENGTH,
        "items": [
            {field: item[field] for field in _ITEM_FIELDS}  # type: ignore[literal-required]
            for item in CLASSIFICATION_TASK_SUITE
        ],
    }


def main() -> None:
    snapshot = build_snapshot()
    SUITE_DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SUITE_DEFINITIONS_DIR / f"{snapshot['suite_id']}.json"
    out_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(out_path)


if __name__ == "__main__":
    main()
    sys.exit(0)
