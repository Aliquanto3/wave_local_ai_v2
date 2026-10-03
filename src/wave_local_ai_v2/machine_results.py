"""Each declared machine's tracked results location, and promotion into it.

A machine's location is the directory `<root>/<machine_id>/` (root:
`MACHINE_RESULTS_ROOT`, default `aidd_docs/results/machines`), holding three
files: `runtime.jsonl` and `quality.jsonl`, the rows the operator promoted from
that machine's live stores, and `refusals.jsonl`, the refusal records the
pre-flight appends there directly (a refusal carries no `run_id` to promote
by). One directory per machine, so two machines' pull requests never edit the
same file. `bundle_merge.py` derives the published bundle from every location.

Promotion (`wave-local-ai-v2-promote`) copies the rows of named `run_id`s
line-for-line and the fiches they cite file-for-file, all or nothing: an
unknown `run_id`, a row another machine produced and a fiche the live
registry does not hold each refuse the whole promotion, naming the cause,
before any file is touched.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from wave_local_ai_v2 import fiche_registry, machines, results, row_contract, settings
from wave_local_ai_v2.row_contract import RowKind

RUNTIME_FILE = "runtime.jsonl"
QUALITY_FILE = "quality.jsonl"
REFUSALS_FILE = "refusals.jsonl"


class PromotionError(ValueError):
    """Raised when a promotion is refused; nothing has been written."""


@dataclass(frozen=True)
class Location:
    """The three files of one machine's tracked results location."""

    machine_id: str
    directory: Path

    @property
    def runtime(self) -> Path:
        return self.directory / RUNTIME_FILE

    @property
    def quality(self) -> Path:
        return self.directory / QUALITY_FILE

    @property
    def refusals(self) -> Path:
        return self.directory / REFUSALS_FILE

    def rows_file(self, kind: RowKind) -> Path:
        return self.runtime if kind == "runtime" else self.quality


def location(root: Path, machine_id: str) -> Location:
    """The tracked location of `machine_id` under `root`."""
    return Location(machine_id=machine_id, directory=root / machine_id)


def row_belongs_to(row: dict[str, Any], kind: RowKind, machine_id: str) -> bool:
    """Whether `row` may sit in `machine_id`'s location.

    A row the machine produced names it. A cloud subject's quality row is
    produced by no machine (`row_contract.MACHINE_NOT_APPLICABLE`) but is run
    from one, so it travels with the machine whose CLI ran it.
    """
    if row.get("machine_id") == machine_id:
        return True
    return (
        kind == "quality"
        and row.get("machine_id") == row_contract.MACHINE_NOT_APPLICABLE
        and row.get("provider") != row_contract.SUBJECT_PROVIDER_LOCAL
    )


@dataclass(frozen=True)
class PromotionResult:
    """What one promotion appended and copied."""

    rows_added: dict[str, int]
    rows_already_present: int
    fiches_copied: list[str]
    fiches_already_present: list[str]


def promote(
    machine_id: str,
    run_ids: Sequence[str],
    *,
    live_stores: dict[RowKind, Path],
    live_fiche_dir: Path,
    root: Path,
    tracked_fiche_dir: Path,
    declared: frozenset[str] | None = None,
) -> PromotionResult:
    """Copy every row of `run_ids` and their fiches into `machine_id`'s location.

    Refused (`PromotionError`, nothing written) when `machine_id` is not a
    declared machine, a `run_id` has no row in either live store, a selected
    row does not belong to the machine (`row_belongs_to`), or a cited fiche
    is absent from the live registry or differs from the tracked copy.
    Idempotent: a line already in the location is not appended again.
    """
    declared_ids = machines.declared_machine_ids() if declared is None else declared
    if machine_id not in declared_ids:
        raise PromotionError(
            f"machine {machine_id!r} is not a declared machine "
            f"(declared: {', '.join(sorted(declared_ids))})"
        )
    wanted = set(run_ids)
    selected: dict[RowKind, list[str]] = {}
    found: set[str] = set()
    cited: set[str] = set()
    for kind, store in live_stores.items():
        selected[kind] = []
        for line in results.read_lines(store):
            row = json.loads(line)
            if row.get("run_id") not in wanted:
                continue
            found.add(row["run_id"])
            if not row_belongs_to(row, kind, machine_id):
                item = row.get("item_id")
                raise PromotionError(
                    f"{kind} row of run {row['run_id']!r}"
                    f"{'' if item is None else f' (item {item!r})'} names machine_id "
                    f"{row.get('machine_id')!r}, not {machine_id!r}: only the "
                    "machine that produced a row promotes it"
                )
            if isinstance(row.get("fiche_hash"), str):
                cited.add(row["fiche_hash"])
            selected[kind].append(line)
    unknown = [run_id for run_id in run_ids if run_id not in found]
    if unknown:
        raise PromotionError(
            f"run_id(s) {', '.join(repr(r) for r in unknown)} have no row in "
            f"{', '.join(str(p) for p in live_stores.values())}"
        )
    for fiche_hash in sorted(cited):
        _check_fiche(fiche_hash, live_fiche_dir, tracked_fiche_dir)

    target = location(root, machine_id)
    added: dict[str, int] = {}
    already = 0
    for kind, lines in selected.items():
        path = target.rows_file(kind)
        present = set(results.read_lines(path))
        new_lines = []
        for line in lines:
            if line in present:
                already += 1
            else:
                present.add(line)
                new_lines.append(line)
        added[kind] = len(new_lines)
        if new_lines:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.writelines(line + "\n" for line in new_lines)
    copied: list[str] = []
    present_fiches: list[str] = []
    for fiche_hash in sorted(cited):
        if fiche_registry.copy_fiche(fiche_hash, live_fiche_dir, tracked_fiche_dir):
            copied.append(fiche_hash)
        else:
            present_fiches.append(fiche_hash)
    return PromotionResult(
        rows_added=added,
        rows_already_present=already,
        fiches_copied=copied,
        fiches_already_present=present_fiches,
    )


def _check_fiche(fiche_hash: str, live_dir: Path, tracked_dir: Path) -> None:
    """Refuse before writing anything if the fiche could not be copied."""
    live = fiche_registry.read_fiche(fiche_hash, live_dir)
    if live is None:
        raise PromotionError(
            f"fiche {fiche_hash!r} cited by a promoted row is not in the live "
            f"registry {live_dir}"
        )
    source = live_dir / f"{fiche_hash}.json"
    target = tracked_dir / f"{fiche_hash}.json"
    if target.exists() and target.read_bytes() != source.read_bytes():
        raise PromotionError(
            f"fiche {fiche_hash!r} in the tracked registry {tracked_dir} differs "
            f"from the live one in {live_dir}; a stored fiche is never overwritten"
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-promote",
        description=(
            "Copy named runs' rows and fiches from this machine's live stores "
            "into its tracked results location."
        ),
    )
    parser.add_argument(
        "--machine",
        default=None,
        metavar="MACHINE_ID",
        help="The location's machine (default: MACHINE_ID).",
    )
    parser.add_argument(
        "--run-id", action="append", required=True, dest="run_ids", metavar="RUN_ID"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Promote; exit 1 naming the refusal, nothing written."""
    args = _parse_args(argv)
    load_dotenv()
    machine_id = args.machine or os.environ.get("MACHINE_ID")
    if not machine_id:
        print(
            "error: no machine named: pass --machine or set MACHINE_ID", file=sys.stderr
        )
        sys.exit(1)
    live_stores: dict[RowKind, Path] = {
        "runtime": Path(
            os.environ.get("RUNTIME_RESULTS_PATH", settings.DEFAULT_RESULTS_PATH)
        ),
        "quality": Path(
            os.environ.get(
                "QUALITY_RESULTS_PATH", settings.DEFAULT_QUALITY_RESULTS_PATH
            )
        ),
    }
    root = settings.machine_results_root_from_env()
    try:
        outcome = promote(
            machine_id,
            args.run_ids,
            live_stores=live_stores,
            live_fiche_dir=settings.fiche_registry_dir_from_env(),
            root=root,
            tracked_fiche_dir=settings.tracked_fiche_registry_dir_from_env(),
        )
    except (OSError, ValueError) as exc:  # PromotionError, FicheCopyError, bad JSON
        print(f"error: promotion refused: {exc}", file=sys.stderr)
        sys.exit(1)
    target = location(root, machine_id)
    print(
        f"promoted into {target.directory}: "
        f"{outcome.rows_added.get('runtime', 0)} runtime row(s), "
        f"{outcome.rows_added.get('quality', 0)} quality row(s) added, "
        f"{outcome.rows_already_present} already present; "
        f"{len(outcome.fiches_copied)} fiche(s) copied, "
        f"{len(outcome.fiches_already_present)} already tracked"
    )
