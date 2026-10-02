"""The roster composition check: Methodology 13's composition rule as a
command that can fail.

Reads the roster file, classes every entry by its declared `size_class`, and
reports per class the families it spans (`roster.family_of`, so the flagship
resolves through the in-code fallback like any row does), whether dense and
MoE are both present, its single-family-ladder label and its MoE declaration,
then per entry the figures and licence terms a published table carries.

It refuses silence, not a single-family roster: a class spanning one family
passes when the roster labels it a single-family ladder, and a class with no
MoE passes when the roster records why. Every failure names its class or its
entry; nothing is skipped. Exit `0` when nothing is named, `1` when anything
is, `2` when the roster file cannot be loaded at all.

Run it before a roster table is published. It is deliberately not part of the
merge gate while the shipped roster is expected to fail it.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from wave_local_ai_v2 import roster, settings

# What a class with entries but no declaration in the roster is read as:
# unlabelled, no MoE search, no reason. It is also named for the omission.
_UNDECLARED = roster.SizeClassDeclaration(
    single_family_ladder=False,
    moe_sought=False,
    moe_entry=None,
    moe_absent_reason=None,
)


@dataclass(frozen=True)
class EntryReport:
    """One entry as the check read it; `None` where the roster is silent."""

    entry_id: str
    size_class: str | None
    family: str | None
    kind: str
    total_params: int | None
    bytes_on_disk: int | None
    licence: roster.Licence | None


@dataclass(frozen=True)
class ClassReport:
    """One size class: its entries, families, architectures and declaration."""

    size_class: str
    entry_ids: tuple[str, ...]
    families: tuple[str, ...]
    dense_present: bool
    moe_entry_ids: tuple[str, ...]
    declaration: roster.SizeClassDeclaration | None


@dataclass(frozen=True)
class Failure:
    """One thing the roster is silent or wrong about, naming where."""

    subject: str
    reason: str


@dataclass(frozen=True)
class CompositionReport:
    """The whole check: per class, per entry, and every failure."""

    roster_path: str
    roster_version: int
    classes: tuple[ClassReport, ...]
    entries: tuple[EntryReport, ...]
    failures: tuple[Failure, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def _entry_report(entry: roster.RosterEntry) -> tuple[EntryReport, list[Failure]]:
    subject = f"entry {entry.entry_id}"
    failures: list[Failure] = []
    family: str | None
    try:
        family = roster.family_of(entry.display_id, entry)
    except roster.RosterError as exc:
        family = None
        failures.append(Failure(subject, f"no resolvable family: {exc}"))
    if entry.size_class is None:
        failures.append(Failure(subject, "declares no size_class"))
    total_params = entry.architecture.total_params
    if total_params is None:
        failures.append(Failure(subject, "declares no architecture.total_params"))
    if entry.bytes_on_disk is None:
        failures.append(Failure(subject, "declares no bytes_on_disk"))
    if entry.licence is None:
        failures.append(Failure(subject, "carries no licence block"))
    if entry.size_class is not None and total_params is not None:
        banded = roster.size_class_for(total_params)
        if banded != entry.size_class:
            failures.append(
                Failure(
                    subject,
                    f"declares size class {entry.size_class} but its "
                    f"{total_params} total parameters fall in {banded}",
                )
            )
    report = EntryReport(
        entry_id=entry.entry_id,
        size_class=entry.size_class,
        family=family,
        kind=entry.architecture.kind,
        total_params=total_params,
        bytes_on_disk=entry.bytes_on_disk,
        licence=entry.licence,
    )
    return report, failures


def _class_failures(report: ClassReport) -> list[Failure]:
    subject = f"size class {report.size_class}"
    failures: list[Failure] = []
    declaration = report.declaration
    if declaration is None:
        failures.append(
            Failure(subject, "holds entries but the roster declares nothing for it")
        )
        declaration = _UNDECLARED
    families = ", ".join(report.families)
    if len(report.families) == 1 and not declaration.single_family_ladder:
        failures.append(
            Failure(
                subject,
                f"spans one family ({families}) without the single-family-ladder label",
            )
        )
    if len(report.families) > 1 and declaration.single_family_ladder:
        failures.append(
            Failure(
                subject,
                f"is labelled a single-family ladder but spans "
                f"{len(report.families)} families ({families})",
            )
        )
    if not report.moe_entry_ids and declaration.moe_absent_reason is None:
        failures.append(
            Failure(subject, "has no MoE represented and no reason recorded")
        )
    if (
        declaration.moe_entry is not None
        and declaration.moe_entry not in report.moe_entry_ids
    ):
        failures.append(
            Failure(
                subject,
                f"declares MoE entry {declaration.moe_entry}, which is not a MoE "
                "entry of this class",
            )
        )
    if report.moe_entry_ids and declaration.moe_entry is None:
        failures.append(
            Failure(
                subject,
                f"holds MoE entry {', '.join(report.moe_entry_ids)} but its "
                "declaration names none",
            )
        )
    return failures


def check_composition(loaded: roster.RosterFile, roster_path: str) -> CompositionReport:
    """Class every entry of `loaded` and name everything the roster is silent on."""
    entries: list[EntryReport] = []
    failures: list[Failure] = []
    for entry in loaded.entries.values():
        entry_report, entry_failures = _entry_report(entry)
        entries.append(entry_report)
        failures.extend(entry_failures)

    classes: list[ClassReport] = []
    for size_class in roster.SIZE_CLASSES:
        members = [entry for entry in entries if entry.size_class == size_class]
        report = ClassReport(
            size_class=size_class,
            entry_ids=tuple(entry.entry_id for entry in members),
            families=tuple(
                sorted({entry.family for entry in members if entry.family is not None})
            ),
            dense_present=any(entry.kind == "dense" for entry in members),
            moe_entry_ids=tuple(
                entry.entry_id for entry in members if entry.kind == "moe"
            ),
            declaration=loaded.size_classes.get(size_class),
        )
        classes.append(report)
        # An empty class publishes nothing, so the rule has nothing to hold.
        if members:
            failures.extend(_class_failures(report))

    return CompositionReport(
        roster_path=roster_path,
        roster_version=loaded.roster_version,
        classes=tuple(classes),
        entries=tuple(entries),
        failures=tuple(failures),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _bands() -> str:
    parts = [roster.SIZE_CLASS_BANDS[0][0]]
    for name, edge in roster.SIZE_CLASS_BANDS[1:]:
        parts.append(f"< {edge:,} <= {name}")
    return " ".join(parts)


def _class_line(report: ClassReport) -> str:
    if not report.entry_ids:
        return f"  {report.size_class}: no entries (not published)"
    declaration = report.declaration
    if declaration is None:
        label = "undeclared"
        sought = "undeclared"
        reason = "undeclared"
    else:
        label = "single-family ladder" if declaration.single_family_ladder else "none"
        sought = _yes_no(declaration.moe_sought)
        reason = declaration.moe_absent_reason or (
            "n/a" if report.moe_entry_ids else "none"
        )
    moe = f"yes ({', '.join(report.moe_entry_ids)})" if report.moe_entry_ids else "no"
    return (
        f"  {report.size_class}: {len(report.entry_ids)} "
        f"entr{'y' if len(report.entry_ids) == 1 else 'ies'}; "
        f"families: {', '.join(report.families) or 'none resolved'}; "
        f"dense: {_yes_no(report.dense_present)}; MoE: {moe}; "
        f"label: {label}; MoE sought: {sought}; MoE absence reason: {reason}"
    )


def _figure(value: int | None, unit: str) -> str:
    return f"{value:,} {unit}" if value is not None else f"no {unit}"


def _entry_line(entry: EntryReport) -> str:
    if entry.licence is None:
        licence = "no licence block"
    else:
        licence = (
            f"licence {entry.licence.licence_id}, client commercial use "
            f"{_yes_no(entry.licence.client_commercial_use)}, read "
            f"{entry.licence.read_on.isoformat()}"
        )
    return (
        f"  {entry.entry_id}: {entry.size_class or 'no size class'}; "
        f"family {entry.family or 'unresolved'}; {entry.kind}; "
        f"{_figure(entry.total_params, 'total params')}; "
        f"{_figure(entry.bytes_on_disk, 'bytes on disk')}; {licence}"
    )


def render_report(report: CompositionReport) -> str:
    """The report as printed: classes, entries, failures, then the verdict."""
    lines = [
        (
            f"Roster composition: {report.roster_path} "
            f"(roster_version {report.roster_version})"
        ),
        f"Size classes, banded on total parameters: {_bands()}",
        *(_class_line(item) for item in report.classes),
        "Entries",
        *(_entry_line(item) for item in report.entries),
    ]
    if report.passed:
        lines.append(
            "PASS: every published size class spans two families or says it does not"
        )
    else:
        lines.append(f"Failures ({len(report.failures)})")
        lines.extend(f"  {item.subject}: {item.reason}" for item in report.failures)
        lines.append(f"FAIL: {len(report.failures)} failure(s)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the check on one roster file; exit `0` / `1` / `2`."""
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-composition-check",
        description=(
            "Report each roster size class's families, dense and MoE presence "
            "and ladder label; exit non-zero naming what the roster is silent on."
        ),
    )
    parser.add_argument(
        "--roster", type=Path, default=Path(settings.DEFAULT_ROSTER_PATH)
    )
    args = parser.parse_args(argv)
    try:
        loaded = roster.load_roster(args.roster)
    except roster.RosterError as exc:
        print(f"composition check: nothing checked: {exc}", file=sys.stderr)
        return 2
    report = check_composition(loaded, args.roster.as_posix())
    sys.stdout.write(render_report(report))
    return 0 if report.passed else 1
