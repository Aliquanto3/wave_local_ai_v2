"""Derive the published bundle from every machine's tracked results location.

The bundle is three files, `runtime-reference.jsonl`,
`quality-reference.jsonl` and `refusals-reference.jsonl`, built by
`wave-local-ai-v2-merge-bundle` from the locations `machine_results.py`
defines and never edited by hand: CI runs the same command with `--check`
and fails when the committed bundle differs from what it derives.

The merge never chooses between machines. It refuses, writing nothing:

- a location directory named for an undeclared machine;
- a row or refusal record whose `machine_id` resolves to no declared machine,
  or that sits in another machine's location;
- a row with no `run_id`, and one `run_id` in two locations (one row would
  reach the bundle twice);
- a **fiche-hash collision**: two rows citing one `fiche_hash` under two
  different machine ids, named with both rows, both machine ids and the hash.
  A cloud subject's row (`machine_id` `not_applicable`) cites the fiche of
  the machine that ran it, so it is outside the keying, never a third claim.

Rows keep their bytes: each line is carried as the harness wrote it, in
sorted machine-id order and append order within a file, so the same
locations always produce a byte-identical bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from wave_local_ai_v2 import machine_results, machines, profiles, results, settings
from wave_local_ai_v2.row_contract import RowKind

ROW_KINDS: tuple[RowKind, ...] = ("runtime", "quality")

# The committed bundle before any machine promoted a row: the schema-"7"
# curated snapshot of 2026-08-27, whose rows predate `machine_id` and so can
# never be derived by this merge. `--check` accepts exactly these bytes (line
# endings normalised) while every location is empty, and write mode refuses
# to overwrite them. The bundle republication story `git mv`s them to
# `*-reference.schema-7.jsonl` before its first merge, then deletes this pin.
PRE_MERGE_SNAPSHOT: dict[str, str] = {
    "runtime": "9fb5882ee4249dba0a6b208dc9dd8f05b53b01a0da73d92a21e14f6165ac1c57",  # pragma: allowlist secret
    "quality": "6a7d72432d88adad7455c938b6adc693c483a202b9896b27e59f55475e6ba9a7",  # pragma: allowlist secret
}


class MergeRefusal(ValueError):
    """Raised when the locations cannot be merged; nothing has been written."""


@dataclass(frozen=True)
class BundlePaths:
    runtime: Path
    quality: Path
    refusals: Path

    def for_kind(self, kind: str) -> Path:
        return {"runtime": self.runtime, "quality": self.quality}.get(
            kind, self.refusals
        )


@dataclass(frozen=True)
class Bundle:
    """The derived bundle: each file's lines, in their published order."""

    lines: dict[str, list[str]]

    def text(self, kind: str) -> str:
        return "".join(line + "\n" for line in self.lines[kind])

    @property
    def empty(self) -> bool:
        return not any(self.lines.values())


@dataclass(frozen=True)
class FicheCollision:
    """Two rows claiming one fiche hash under two machine ids."""

    fiche_hash: str
    first: dict[str, Any]
    second: dict[str, Any]

    def describe(self) -> str:
        return (
            f"fiche hash collision on {self.fiche_hash!r}: "
            f"{_label(self.first)} names machine_id {self.first['machine_id']!r}, "
            f"{_label(self.second)} names machine_id "
            f"{self.second['machine_id']!r}; the merge does not choose between "
            "them"
        )


def _label(row: Mapping[str, Any]) -> str:
    kind = row.get("_kind", "row")
    item = f", item {row['item_id']!r}" if row.get("item_id") is not None else ""
    return f"{kind} row of run {row.get('run_id')!r}{item}"


def fiche_collisions(
    rows: Iterable[Mapping[str, Any]], declared: frozenset[str]
) -> list[FicheCollision]:
    """Every pair of rows citing one fiche hash under different declared machines.

    Only rows naming a declared machine are keyed: a cloud row's
    `not_applicable` claims no fiche of its own.
    """
    owners: dict[str, Mapping[str, Any]] = {}
    found: list[FicheCollision] = []
    for row in rows:
        fiche_hash = row.get("fiche_hash")
        machine_id = row.get("machine_id")
        if not isinstance(fiche_hash, str) or machine_id not in declared:
            continue
        first = owners.setdefault(fiche_hash, row)
        if first.get("machine_id") != machine_id:
            found.append(FicheCollision(fiche_hash, dict(first), dict(row)))
    return found


def unresolved_machine_rows(
    rows: Iterable[tuple[RowKind, Mapping[str, Any]]], declared: frozenset[str]
) -> list[str]:
    """A description of every row whose `machine_id` resolves to no declared
    machine (a cloud row's `not_applicable` resolves by stating none)."""
    return [
        f"{_label(dict(row, _kind=kind))} names machine_id "
        f"{row.get('machine_id')!r}, which is not a declared machine"
        for kind, row in rows
        if row.get("machine_id") not in declared
        and not any(
            machine_results.row_belongs_to(dict(row), kind, machine_id)
            for machine_id in declared
        )
    ]


def unresolved_refusals(
    records: Iterable[Mapping[str, Any]],
    *,
    roster_entry_ids: Iterable[str],
    profile_registry: profiles.ProfileRegistry,
    declared: frozenset[str],
) -> list[str]:
    """A description of every refusal record whose roster entry, machine or
    profile does not resolve."""
    entries = set(roster_entry_ids)
    problems: list[str] = []
    for record in records:
        entry_id = record.get("roster_entry_id")
        where = (
            f"refusal record of {entry_id!r} refused at {record.get('refused_at')!r}"
        )
        if entry_id not in entries:
            problems.append(f"{where}: roster entry does not resolve")
        if record.get("machine_id") not in declared:
            problems.append(
                f"{where}: machine_id {record.get('machine_id')!r} does not resolve"
            )
        if record.get("profile_id") not in profiles.declared_profiles(
            profile_registry, str(entry_id)
        ):
            problems.append(
                f"{where}: profile_id {record.get('profile_id')!r} does not resolve"
            )
    return problems


def collect(root: Path, declared: frozenset[str]) -> Bundle:
    """Read every declared machine's location into one bundle, or refuse."""
    if root.is_dir():
        strays = sorted(
            child.name
            for child in root.iterdir()
            if child.is_dir() and child.name not in declared
        )
        if strays:
            raise MergeRefusal(
                f"location(s) {', '.join(repr(s) for s in strays)} under {root} "
                "name no declared machine"
            )
    lines: dict[str, list[str]] = {"runtime": [], "quality": [], "refusals": []}
    keyed: list[dict[str, Any]] = []
    run_location: dict[str, str] = {}
    for machine_id in sorted(declared):
        location = machine_results.location(root, machine_id)
        for kind in ROW_KINDS:
            path = location.rows_file(kind)
            for line in results.read_lines(path):
                row = json.loads(line)
                _check_row(row, kind, machine_id, path, declared)
                run_id = row.get("run_id")
                if not isinstance(run_id, str) or not run_id:
                    raise MergeRefusal(
                        f"{kind} row in {path} carries no run_id; every bundle row "
                        "names the run that wrote it"
                    )
                other = run_location.setdefault(run_id, machine_id)
                if other != machine_id:
                    raise MergeRefusal(
                        f"run {run_id!r} is in both {other!r}'s and {machine_id!r}'s "
                        "locations; a run is promoted by one machine"
                    )
                keyed.append(dict(row, _kind=kind))
                lines[kind].append(line)
        for line in results.read_lines(location.refusals):
            record = json.loads(line)
            if record.get("machine_id") != machine_id:
                raise MergeRefusal(
                    f"refusal record in {location.refusals} names machine_id "
                    f"{record.get('machine_id')!r}, not {machine_id!r}"
                )
            lines["refusals"].append(line)
    collisions = fiche_collisions(keyed, declared)
    if collisions:
        raise MergeRefusal("; ".join(c.describe() for c in collisions))
    return Bundle(lines=lines)


def _check_row(
    row: dict[str, Any],
    kind: RowKind,
    machine_id: str,
    path: Path,
    declared: frozenset[str],
) -> None:
    if machine_results.row_belongs_to(row, kind, machine_id):
        return
    unresolved = unresolved_machine_rows([(kind, row)], declared)
    if unresolved:
        raise MergeRefusal(f"{unresolved[0]} (in {path})")
    raise MergeRefusal(
        f"{_label(dict(row, _kind=kind))} names machine_id "
        f"{row.get('machine_id')!r} but is filed in {machine_id!r}'s location {path}"
    )


def _normalised(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    return path.read_bytes().replace(b"\r\n", b"\n")


def is_pre_merge_snapshot(paths: BundlePaths) -> bool:
    """Whether the committed runtime and quality files are the pinned snapshot."""
    for kind, digest in PRE_MERGE_SNAPSHOT.items():
        content = _normalised(paths.for_kind(kind))
        if content is None or hashlib.sha256(content).hexdigest() != digest:
            return False
    return True


def check(bundle: Bundle, paths: BundlePaths) -> list[str]:
    """Every way the committed bundle differs from `bundle`; empty when equal.

    The pinned pre-merge snapshot passes only while no location holds a
    record and no refusals file has been published beside it.
    """
    if bundle.empty and is_pre_merge_snapshot(paths) and not paths.refusals.exists():
        return []
    problems = []
    for kind, expected in bundle.lines.items():
        path = paths.for_kind(kind)
        content = _normalised(path)
        if content is None:
            problems.append(f"{path} is missing; the merge derives it")
        elif content != bundle.text(kind).encode("utf-8"):
            problems.append(
                f"{path} differs from what the merge derives from the per-machine "
                f"locations ({len(expected)} line(s)); the bundle is never hand-edited"
            )
    return problems


def write(bundle: Bundle, paths: BundlePaths) -> None:
    """Write the three bundle files, refusing to overwrite the pinned snapshot."""
    if is_pre_merge_snapshot(paths):
        raise MergeRefusal(
            f"{paths.runtime} and {paths.quality} are the schema-7 curated "
            "snapshot; supersede them first (git mv to *-reference.schema-7.jsonl), "
            "never overwrite them"
        )
    for kind in bundle.lines:
        path = paths.for_kind(kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(bundle.text(kind))


def bundle_paths_from_env(bundle_dir: Path | None) -> BundlePaths:
    """The three bundle files: under `bundle_dir` when given, else configured."""
    defaults = BundlePaths(
        runtime=Path(settings.DEFAULT_RUNTIME_REFERENCE_PATH),
        quality=Path(settings.DEFAULT_QUALITY_REFERENCE_PATH),
        refusals=Path(settings.DEFAULT_REFUSALS_REFERENCE_PATH),
    )
    if bundle_dir is not None:
        return BundlePaths(
            runtime=bundle_dir / defaults.runtime.name,
            quality=bundle_dir / defaults.quality.name,
            refusals=bundle_dir / defaults.refusals.name,
        )
    return BundlePaths(
        runtime=Path(os.environ.get("RUNTIME_REFERENCE_PATH", defaults.runtime)),
        quality=Path(os.environ.get("QUALITY_REFERENCE_PATH", defaults.quality)),
        refusals=Path(os.environ.get("REFUSALS_REFERENCE_PATH", defaults.refusals)),
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-merge-bundle",
        description="Derive the published bundle from every machine's location.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 when the committed bundle differs.",
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=None,
        help="Read or write the three bundle files in this directory instead.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Merge (or check); exit 1 on a refusal or a differing bundle."""
    args = _parse_args(argv)
    load_dotenv()
    root = settings.machine_results_root_from_env()
    paths = bundle_paths_from_env(args.bundle_dir)
    try:
        bundle = collect(root, machines.declared_machine_ids())
    except (OSError, ValueError) as exc:  # MergeRefusal, bad JSON, bad registry
        print(f"error: merge refused: {exc}", file=sys.stderr)
        sys.exit(1)
    counts = ", ".join(f"{len(v)} {k}" for k, v in bundle.lines.items())
    if args.check:
        problems = check(bundle, paths)
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        if problems:
            sys.exit(1)
        if bundle.empty and is_pre_merge_snapshot(paths):
            print(
                "bundle check: no location holds a record yet and the committed "
                "bundle is the pinned schema-7 snapshot, unchanged"
            )
        else:
            print(f"bundle check: committed bundle equals the merge ({counts})")
        return
    try:
        write(bundle, paths)
    except MergeRefusal as exc:
        print(f"error: merge refused: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"bundle written from {root}: {counts}")
