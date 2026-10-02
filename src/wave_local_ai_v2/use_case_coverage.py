"""The use-case coverage record: every PRD use case in a declared state.

The PRD lists nine task use cases plus multilingual EN/FR/DE coverage. Each
of the ten is one entry of a record held as data (`use_case_coverage.json`,
beside the suite registry), and each entry declares exactly one state:

- `exercised`, naming the suite ids that exercise it;
- `covered-by-dimension`, naming the suite ids that carry it as a dimension
  (multilingual is a language dimension of the classification, translation
  and rewriting suites, so nothing is built for it);
- `out-of-scope-this-release`, with a non-empty reason.

A state is declared, never inferred: registering a suite does not make a use
case `exercised`; the record is edited, and the gate checks the edit. Every
suite id an entry names must resolve through `suite_registry.resolve`, so an
entry pointing at a suite that is not registered, or that the suite gate
refuses, is no state at all.

The list of required use cases is held here, not in the record: a record that
declared its own list could drop an entry and its list item together and
still pass.

`main` publishes the record into `aidd_docs/results/` only when every entry
passes. Otherwise it writes nothing and names every failing entry, not only
the first; that refusal is the honest coverage reading until the last entry
resolves.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import settings, suite_registry
from wave_local_ai_v2.suite_gate import SuiteGateError

RECORD_FILENAME = "use_case_coverage.json"

# The PRD acceptance criterion's nine task use cases, then its multilingual
# dimension, in the PRD's own order.
USE_CASES: tuple[str, ...] = (
    "classification",
    "translation",
    "document-comparison",
    "text-rewriting",
    "code-generation",
    "agentic-planning",
    "agentic-tool-calling",
    "web-research",
    "rag-answer-generation",
    "multilingual-en-fr-de",
)

EXERCISED = "exercised"
COVERED_BY_DIMENSION = "covered-by-dimension"
OUT_OF_SCOPE = "out-of-scope-this-release"
STATES: tuple[str, ...] = (EXERCISED, COVERED_BY_DIMENSION, OUT_OF_SCOPE)
_SUITE_STATES = frozenset({EXERCISED, COVERED_BY_DIMENSION})


class CoverageRefusal(ValueError):
    """Raised when the record is not publishable; names every failing entry."""

    def __init__(self, failures: Sequence[str]) -> None:
        self.failures = list(failures)
        super().__init__(
            f"{len(self.failures)} coverage entr"
            f"{'y' if len(self.failures) == 1 else 'ies'} without a resolvable "
            "state:\n" + "\n".join(f"- {failure}" for failure in self.failures)
        )


def _suite_problems(state: str, suite_ids: Any) -> list[str]:
    if not (
        isinstance(suite_ids, list)
        and suite_ids != []
        and all(isinstance(suite_id, str) and suite_id for suite_id in suite_ids)
    ):
        return [f"state {state} names no suite id"]
    problems = []
    for suite_id in suite_ids:
        try:
            suite_registry.resolve(suite_id)
        except (suite_registry.SuiteRegistryError, SuiteGateError):
            problems.append(f"suite {suite_id!r} does not resolve in the registry")
    return problems


def _entry_problems(entry: Mapping[str, Any]) -> list[str]:
    state = entry.get("state")
    if state is None or state == "":
        return ["has no state"]
    if state not in STATES:
        return [f"state {state!r} is not one of {', '.join(STATES)}"]
    if state in _SUITE_STATES:
        problems = _suite_problems(state, entry.get("suite_ids"))
        if "reason" in entry:
            problems.append(
                f"state {state} carries a reason, which only {OUT_OF_SCOPE} declares"
            )
        return problems
    problems = []
    reason = entry.get("reason")
    if not (isinstance(reason, str) and reason.strip()):
        problems.append(f"state {OUT_OF_SCOPE} has no reason")
    if "suite_ids" in entry:
        problems.append(f"state {OUT_OF_SCOPE} names suite ids, which it cannot carry")
    return problems


def check_record(data: Any) -> list[str]:
    """Every failure in the record, one line per failing entry, PRD order first."""
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return ["the record holds no 'entries' list"]

    failures: list[str] = []
    declared: dict[str, Mapping[str, Any]] = {}
    for position, entry in enumerate(entries, start=1):
        use_case = entry.get("use_case") if isinstance(entry, dict) else None
        if not isinstance(use_case, str) or not use_case:
            failures.append(f"entry {position}: names no use case")
        elif use_case not in USE_CASES:
            failures.append(f"{use_case}: not a PRD use case")
        elif use_case in declared:
            failures.append(f"{use_case}: declared more than once")
        else:
            declared[use_case] = entry

    per_use_case: list[str] = []
    for use_case in USE_CASES:
        if use_case not in declared:
            per_use_case.append(f"{use_case}: missing from the record")
            continue
        problems = _entry_problems(declared[use_case])
        if problems:
            per_use_case.append(f"{use_case}: {'; '.join(problems)}")
    return per_use_case + failures


def gate_record(data: Any) -> list[dict[str, Any]]:
    """The record's entries in PRD order, or `CoverageRefusal` naming them all."""
    failures = check_record(data)
    if failures:
        raise CoverageRefusal(failures)
    by_use_case = {entry["use_case"]: entry for entry in data["entries"]}
    return [dict(by_use_case[use_case]) for use_case in USE_CASES]


def default_record() -> Traversable:
    """The committed record, shipped beside the suite registry."""
    return resources.files("wave_local_ai_v2") / RECORD_FILENAME


def load_record(source: Path | Traversable) -> Any:
    """The record's JSON, unchecked; `gate_record` decides what it is worth."""
    return json.loads(source.read_text(encoding="utf-8"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m wave_local_ai_v2.use_case_coverage",
        description=(
            "Publish the use-case coverage record, or refuse naming every "
            "entry without a resolvable state."
        ),
    )
    parser.add_argument(
        "--record",
        type=Path,
        default=None,
        help="coverage record to gate (default: the committed record)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.DEFAULT_USE_CASE_COVERAGE_PATH),
        help=f"where to publish it (default: {settings.DEFAULT_USE_CASE_COVERAGE_PATH})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source = args.record if args.record is not None else default_record()
    try:
        entries = gate_record(load_record(source))
    except json.JSONDecodeError as error:
        print(
            f"coverage record refused: {source} is not JSON: {error}", file=sys.stderr
        )
        return 1
    except CoverageRefusal as refusal:
        print(f"coverage record refused, nothing written: {refusal}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"use_cases": entries}, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
