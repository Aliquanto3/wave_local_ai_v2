"""Replay a suite's recorded selection rule over a source table.

`uv run python -m wave_local_ai_v2.subset_replay (--suite ID | --definition
PATH) --source ROWS.jsonl`

The answer to "how did you pick these items" is this command, not a
sentence. It loads the suite through the registry (so the rule and the items
have already passed its checks and the gate), reads the source table -- one
JSON object per line, each a row carrying `source`, `language`, the rule's
stable source key and its content fields -- re-draws the subset with
`subset_sampler.replay`, and compares:

- exit `0`: the same item ids in the same order, and every drawn item's text
  still matches its recorded content hash;
- exit `1`: otherwise, naming the first position where the ids differ, every
  item whose source text no longer matches its hash, every item the source
  no longer holds -- or why nothing could be replayed (no rule, an unreadable
  source, a source the rule cannot draw from).

The source table is read with the standard library. The loader and the
generator recorded on the rule are printed, not enforced: a generator that
draws differently shows up as differing ids, and the canonical ordering is
what removes the dependency on the order a loader delivered the rows in.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import subset_sampler, suite_registry


def read_source(path: Path) -> list[dict[str, Any]]:
    """The rows of a JSONL source table; raises naming the line."""
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path} line {number} is not JSON: {error}"
                ) from error
            if not isinstance(row, dict):
                raise TypeError(f"{path} line {number} is not a JSON object")
            rows.append(row)
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m wave_local_ai_v2.subset_replay",
        description="Re-draw a suite's subset from its recorded selection rule.",
    )
    suite = parser.add_mutually_exclusive_group(required=True)
    suite.add_argument("--suite", help="a registered suite id")
    suite.add_argument(
        "--definition", type=Path, help="a suite definition file outside the registry"
    )
    parser.add_argument(
        "--source", type=Path, required=True, help="the source table, JSON lines"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        definition = (
            suite_registry.resolve(args.suite)
            if args.suite is not None
            else suite_registry.load_definition(args.definition)
        )
        rows = read_source(args.source)
    except (OSError, ValueError, TypeError) as error:
        # `SuiteRegistryError`, `SuiteGateError` and a bad source line are
        # all `ValueError`s naming what is wrong.
        print(f"replay refused: {error}", file=sys.stderr)
        return 1

    rule = definition.extra.get("selection_rule")
    if rule is None:
        print(
            f"replay refused: suite {definition.suite_id!r} records no selection rule",
            file=sys.stderr,
        )
        return 1
    try:
        report = subset_sampler.replay(definition.items, rule, rows)
    except subset_sampler.SubsetSamplerError as error:
        print(f"replay refused: {error}", file=sys.stderr)
        return 1

    loader, generator = rule["loader"], rule["generator"]
    print(
        f"suite {definition.suite_id}@{definition.suite_version}: sampler "
        f"{rule['sampler_version']}, seed {rule['seed']} (attempts "
        f"{rule['attempts']}, seeds tried {rule['seeds_tried']}), recorded loader "
        f"{loader['library']} {loader['version']}, recorded generator "
        f"{generator['library']} {generator['version']}"
    )
    if report.reproduced:
        print(f"reproduced: {len(report.recorded_ids)} items, same ids, same order")
        return 0
    position = report.first_difference
    if position is not None:
        recorded = _at(report.recorded_ids, position)
        redrawn = _at(report.redrawn_ids, position)
        print(
            f"not reproduced: ids differ from position {position}: recorded "
            f"{recorded}, redrawn {redrawn}",
            file=sys.stderr,
        )
    for item_id in report.edited:
        print(
            f"not reproduced: item {item_id!r} no longer matches its content_hash",
            file=sys.stderr,
        )
    for item_id in report.absent:
        print(f"not reproduced: item {item_id!r} is not in the source", file=sys.stderr)
    return 1


def _at(ids: tuple[str, ...], position: int) -> str:
    return repr(ids[position]) if position < len(ids) else "nothing"


if __name__ == "__main__":
    sys.exit(main())
