"""Suite definition snapshots: each registered task suite as its definition
stands at export time.

These are snapshots, not a live registry: a bundle reader resolving a
published row's `suite_id`/`suite_version` reads the exported JSON file
directly, without importing any code or checking out the commit that
produced it. Each file captures what its suite looked like at export time;
the run itself resolves the suite through `suite_registry`, never through a
snapshot, so a snapshot is published evidence and not a run input.

Every suite `suite_registry` resolves is exported under one snapshot rule:
identity, caps, and every item with every field its definition declares. A
suite is data now, so the snapshot of a shipped suite is its definition file
plus the computed `prompt_set_hash`, minus the scoring-rule name and
`task_suite`, which no snapshot has ever carried. It stays the file a bundle
reader resolves, because it is addressed by version and never overwritten.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import settings, suite_registry

SUITE_DEFINITIONS_DIR = Path(settings.DEFAULT_SUITE_DEFINITIONS_DIR)


def snapshot_filename(suite_id: str, suite_version: str) -> str:
    """The file a row citing `suite_id`/`suite_version` resolves to.

    Addressed by the pair, not by the id alone: a version bump adds a file
    beside its predecessor instead of overwriting it, so a row published under
    an older version still finds the definition it was produced against. This
    is the discipline `runtime-reference.schema-1.jsonl` already follows for
    superseded row files -- a reader chasing an old citation must not land on
    a newer artifact wearing the same name.
    """
    return f"{suite_id}@{suite_version}.json"


def build_snapshot(definition: suite_registry.SuiteDefinition) -> dict[str, Any]:
    """Return one registered suite's identity, caps and every item, plain-dict
    shaped.

    Every field an item declares is exported, so a field a later story adds
    to the data reaches the snapshot with no change here; so does any
    additional suite-level declaration (`SuiteDefinition.extra`). The
    scoring-rule name and `task_suite` are not exported: they were never part
    of a snapshot, and adding them would rewrite every committed file.
    """
    return {
        **definition.extra,
        "suite_id": definition.suite_id,
        "suite_version": definition.suite_version,
        "prompt_set_hash": definition.prompt_set_hash,
        "max_output_tokens": definition.max_output_tokens,
        "stop_sequences": list(definition.stop_sequences),
        "thinking_policy": definition.thinking_policy,
        "context_length": definition.context_length,
        "items": [dict(item) for item in definition.items],
    }


def snapshot_text(snapshot: Mapping[str, Any]) -> str:
    """The exact text a snapshot file holds (before platform newlines)."""
    return json.dumps(snapshot, indent=2, sort_keys=True)


def all_snapshots() -> list[dict[str, Any]]:
    """Every registered suite, snapshot-shaped, in suite-id order."""
    return [
        build_snapshot(suite_registry.resolve(suite_id))
        for suite_id in suite_registry.registered_ids()
    ]


def main() -> None:
    SUITE_DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)
    for snapshot in all_snapshots():
        out_path = SUITE_DEFINITIONS_DIR / snapshot_filename(
            snapshot["suite_id"], snapshot["suite_version"]
        )
        out_path.write_text(snapshot_text(snapshot), encoding="utf-8")
        print(out_path)


if __name__ == "__main__":
    main()
    sys.exit(0)
