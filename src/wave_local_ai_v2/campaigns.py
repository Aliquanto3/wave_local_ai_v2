"""The campaign declaration: which engines, prompt variants, roster entries and
suites one campaign crosses, on which declared machine and compute mode.

A campaign is data, not an option taken at a call site (Methodology 22). One
tracked file per campaign, `<campaigns dir>/<campaign_id>.json`, declares
every dimension; `load_declaration` checks it against the caps (at most
`MAX_ENGINES` engines and `MAX_PROMPT_VARIANTS` variants) and resolves every
id against its own registry, so an over-sized or misspelled campaign is
refused before anything runs rather than noticed after.

The declared cells are the product engine x variant x roster entry x suite.
A further dimension (the agentic harness list Methodology 23 caps at three)
extends this one declaration and its cell product; it never introduces a
second campaign file.

A run started under a campaign (`CAMPAIGN_ID`) is checked against the
declaration before any server starts (`require_run_campaign`) and stamps the
campaign id on every row; a run under none stamps `row_contract.NO_CAMPAIGN`.

The completeness command (`wave-local-ai-v2-campaign-completeness`) lists
every declared cell with the run ids that fill it and exits non-zero naming
each cell nobody ran. A cell the declaration excludes -- `refused` under the
machine epic's discipline or `dropped` with a recorded reason -- is listed
with that reason and is not a failure; an excluded cell that nonetheless
holds rows contradicts its own declaration and fails.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv

from wave_local_ai_v2 import (
    engines,
    machines,
    path_guard,
    prompt_variants,
    results,
    roster,
    row_contract,
    suite_registry,
)
from wave_local_ai_v2.settings import (
    DEFAULT_CAMPAIGNS_DIR,
    DEFAULT_QUALITY_RESULTS_PATH,
    DEFAULT_ROSTER_PATH,
)

if TYPE_CHECKING:
    from wave_local_ai_v2.settings import Settings

# Methodology 22's caps: the run count stays bounded so every declared cell
# can actually be run.
MAX_ENGINES = 2
MAX_PROMPT_VARIANTS = 4

OUTCOME_REFUSED = "refused"
OUTCOME_DROPPED = "dropped"
EXCLUSION_OUTCOMES = (OUTCOME_REFUSED, OUTCOME_DROPPED)

STATUS_FILLED = "filled"
STATUS_EMPTY = "empty"
STATUS_CONTRADICTED = "contradicted"
# The statuses that fail the completeness check.
FAILING_STATUSES = frozenset({STATUS_EMPTY, STATUS_CONTRADICTED})

DECLARATION_KEYS = (
    "campaign_id",
    "description",
    "engines",
    "prompt_variants",
    "roster_entries",
    "suites",
    "machine",
    "exclusions",
)
_EXCLUSION_COORDINATES = (
    "engine_id",
    "prompt_variant",
    "roster_entry_id",
    "suite_id",
)
_EXCLUSION_KEYS = frozenset((*_EXCLUSION_COORDINATES, "outcome", "reason", "evidence"))


class CampaignError(ValueError):
    """A declaration that fails its check, or a run outside its campaign."""


@dataclass(frozen=True)
class Cell:
    """One declared cell: engine x variant x roster entry x suite."""

    engine_id: str
    prompt_variant_id: str
    prompt_variant_version: str
    roster_entry_id: str
    suite_id: str

    def label(self) -> str:
        return (
            f"engine={self.engine_id} "
            f"variant={self.prompt_variant_id}@{self.prompt_variant_version} "
            f"roster_entry={self.roster_entry_id} suite={self.suite_id}"
        )


@dataclass(frozen=True)
class Exclusion:
    """A set of declared cells that will not be run, and why.

    A coordinate left `None` covers every declared value on that axis, so a
    roster entry the machine refuses is one exclusion, not one per cell.
    """

    outcome: str
    reason: str
    evidence: str
    engine_id: str | None = None
    prompt_variant: tuple[str, str] | None = None
    roster_entry_id: str | None = None
    suite_id: str | None = None

    def covers(self, cell: Cell) -> bool:
        return (
            (self.engine_id is None or self.engine_id == cell.engine_id)
            and (
                self.prompt_variant is None
                or self.prompt_variant
                == (cell.prompt_variant_id, cell.prompt_variant_version)
            )
            and (
                self.roster_entry_id is None
                or self.roster_entry_id == cell.roster_entry_id
            )
            and (self.suite_id is None or self.suite_id == cell.suite_id)
        )


@dataclass(frozen=True)
class CampaignDeclaration:
    """One campaign, loaded and checked against the caps and every registry."""

    campaign_id: str
    description: str
    engines: tuple[str, ...]
    prompt_variants: tuple[tuple[str, str], ...]
    roster_entries: tuple[str, ...]
    suites: tuple[str, ...]
    machine_id: str
    compute_mode: str
    exclusions: tuple[Exclusion, ...]

    def cells(self) -> list[Cell]:
        """Every declared cell, in declaration order."""
        return [
            Cell(engine_id, variant_id, version, entry_id, suite_id)
            for engine_id in self.engines
            for variant_id, version in self.prompt_variants
            for entry_id in self.roster_entries
            for suite_id in self.suites
        ]

    def exclusion_for(self, cell: Cell) -> Exclusion | None:
        return next((ex for ex in self.exclusions if ex.covers(cell)), None)


@dataclass(frozen=True)
class CellListing:
    """One line of the completeness listing."""

    cell: Cell
    status: str
    run_ids: tuple[str, ...]
    exclusion: Exclusion | None

    def render(self) -> str:
        line = f"{self.status:<12} {self.cell.label()}"
        if self.run_ids:
            line += f" runs={','.join(self.run_ids)}"
        if self.exclusion is not None:
            line += (
                f" {self.exclusion.outcome}: {self.exclusion.reason} "
                f"(evidence: {self.exclusion.evidence})"
            )
        return line


def load_declaration(
    path: Path,
    *,
    engines_path: Path = Path(engines.DEFAULT_REGISTRY_PATH),
    roster_path: Path = Path(DEFAULT_ROSTER_PATH),
    machines_path: Path = Path(machines.DEFAULT_REGISTRY_PATH),
) -> CampaignDeclaration:
    """Parse `path`, refusing any declaration outside the caps or naming an id
    absent from its registry, with the offending value named."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CampaignError(
            f"campaign declaration not readable at {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CampaignError(
            f"campaign declaration at {path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise CampaignError(f"campaign declaration at {path} must be an object")
    unknown = sorted(set(raw) - set(DECLARATION_KEYS))
    if unknown:
        raise CampaignError(
            f"campaign declaration at {path} carries unknown key(s): "
            f"{', '.join(unknown)} (declared keys: {', '.join(DECLARATION_KEYS)})"
        )
    missing = [key for key in DECLARATION_KEYS if key not in raw]
    if missing:
        raise CampaignError(
            f"campaign declaration at {path} is missing: {', '.join(missing)}"
        )

    campaign_id = _text(raw["campaign_id"], "campaign_id")
    if campaign_id == row_contract.NO_CAMPAIGN:
        raise CampaignError(
            f"campaign id {campaign_id!r} is reserved: it is what a row run "
            "under no campaign records"
        )
    if path.stem != campaign_id:
        raise CampaignError(
            f"campaign declaration {path.name} declares campaign_id "
            f"{campaign_id!r}: the file name and the id must match"
        )
    where = f"campaign {campaign_id!r}"
    description = _text(raw["description"], f"{where}: description")

    engine_ids = _id_list(raw["engines"], f"{where}: engines")
    if len(engine_ids) > MAX_ENGINES:
        raise CampaignError(
            f"{where} declares {len(engine_ids)} engines ({', '.join(engine_ids)}): "
            f"a campaign declares at most {MAX_ENGINES}"
        )
    try:
        engine_registry = engines.load_registry(engines_path)
    except engines.EngineRegistryError as exc:
        raise CampaignError(f"{where}: the engine registry refuses: {exc}") from exc
    _all_registered(where, "engine", engine_ids, engine_registry.entries)

    variants = _variant_list(raw["prompt_variants"], where)
    if len(variants) > MAX_PROMPT_VARIANTS:
        raise CampaignError(
            f"{where} declares {len(variants)} prompt variants "
            f"({', '.join(f'{v}@{n}' for v, n in variants)}): a campaign "
            f"declares at most {MAX_PROMPT_VARIANTS}"
        )
    for variant_id, version in variants:
        try:
            variant = prompt_variants.resolve(variant_id, version)
        except prompt_variants.PromptVariantError as exc:
            raise CampaignError(f"{where}: {exc}") from exc
        _refuse_an_unsupported_constraint(where, variant, engine_ids, engine_registry)

    roster_entries = _id_list(raw["roster_entries"], f"{where}: roster_entries")
    try:
        loaded_roster = roster.load_roster(roster_path)
    except roster.RosterError as exc:
        raise CampaignError(f"{where}: the roster refuses: {exc}") from exc
    _all_registered(where, "roster entry", roster_entries, loaded_roster.entries)

    suites = _id_list(raw["suites"], f"{where}: suites")
    _all_registered(where, "suite", suites, suite_registry.registered_ids())

    machine_id, compute_mode = _machine(raw["machine"], where, machines_path)

    declaration = CampaignDeclaration(
        campaign_id=campaign_id,
        description=description,
        engines=engine_ids,
        prompt_variants=variants,
        roster_entries=roster_entries,
        suites=suites,
        machine_id=machine_id,
        compute_mode=compute_mode,
        exclusions=(),
    )
    exclusions = _exclusions(raw["exclusions"], declaration)
    declaration = dataclasses.replace(declaration, exclusions=exclusions)
    for cell in declaration.cells():
        covering = [ex for ex in exclusions if ex.covers(cell)]
        if len(covering) > 1:
            raise CampaignError(
                f"{where}: cell {cell.label()} is covered by {len(covering)} "
                "exclusions; a cell is excluded once, for one reason"
            )
    return declaration


def declaration_path(campaign_id: str, campaigns_dir: Path) -> Path:
    """The file `campaign_id` is declared in, never outside `campaigns_dir`."""
    path = path_guard.resolve_within_root(campaigns_dir, f"{campaign_id}.json")
    if path is None:
        raise CampaignError(
            f"campaign id {campaign_id!r} does not name a file inside {campaigns_dir}"
        )
    return path


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CampaignError(f"{where} must be a non-empty string, got {value!r}")
    return value


def _id_list(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise CampaignError(f"{where} must be a non-empty list, got {value!r}")
    ids = tuple(_text(item, where) for item in value)
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise CampaignError(f"{where} declares {', '.join(duplicates)} twice")
    return ids


def _refuse_an_unsupported_constraint(
    where: str,
    variant: prompt_variants.PromptVariant,
    engine_ids: tuple[str, ...],
    engine_registry: engines.EngineRegistry,
) -> None:
    """Refuse a constraining variant on an engine lacking its mechanism.

    The engine entry declares the mechanisms it supports; one declaring none
    of the variant's cannot run the cell, which stays undeclarable until the
    engine's own outcome (a mechanism, or a recorded drop) is settled.
    """
    needed = prompt_variants.constraint_mechanisms(variant)
    if not needed:
        return
    for engine_id in engine_ids:
        supported = set(engine_registry.entries[engine_id].constraint_mechanisms)
        missing = sorted(needed - supported)
        if missing:
            declared = ", ".join(sorted(supported)) or "none"
            raise CampaignError(
                f"{where}: prompt variant {variant.variant_id!r} version "
                f"{variant.version!r} constrains output through "
                f"{', '.join(sorted(needed))}, but engine {engine_id!r} declares "
                f"constraint mechanisms: {declared}; the cell cannot run until "
                "that engine's constraint outcome is recorded"
            )


def _variant_list(value: object, where: str) -> tuple[tuple[str, str], ...]:
    field = f"{where}: prompt_variants"
    if not isinstance(value, list) or not value:
        raise CampaignError(f"{field} must be a non-empty list, got {value!r}")
    variants = tuple(_variant(item, field) for item in value)
    duplicates = sorted({v for v in variants if variants.count(v) > 1})
    if duplicates:
        raise CampaignError(
            f"{field} declares {', '.join(f'{v}@{n}' for v, n in duplicates)} twice"
        )
    return variants


def _variant(value: object, where: str) -> tuple[str, str]:
    if not isinstance(value, dict) or set(value) != {"id", "version"}:
        raise CampaignError(
            f"{where}: each variant is {{'id', 'version'}}, got {value!r}"
        )
    return _text(value["id"], where), _text(value["version"], where)


def _all_registered(
    where: str, kind: str, declared: Iterable[str], registered: Iterable[str]
) -> None:
    known = set(registered)
    absent = [item for item in declared if item not in known]
    if absent:
        raise CampaignError(
            f"{where} names {kind} id(s) absent from the registry: "
            f"{', '.join(absent)} (registered: {', '.join(sorted(known))})"
        )


def _machine(value: object, where: str, machines_path: Path) -> tuple[str, str]:
    if not isinstance(value, dict) or set(value) != {"machine_id", "compute_mode"}:
        raise CampaignError(
            f"{where}: machine is {{'machine_id', 'compute_mode'}}, got {value!r}"
        )
    machine_id = _text(value["machine_id"], f"{where}: machine.machine_id")
    compute_mode = _text(value["compute_mode"], f"{where}: machine.compute_mode")
    try:
        registry = machines.load_registry(machines_path)
        entry = machines.resolve_machine(registry, machine_id)
    except machines.MachineRegistryError as exc:
        raise CampaignError(f"{where}: {exc}") from exc
    if compute_mode not in machines.COMPUTE_MODES:
        raise CampaignError(
            f"{where}: compute mode {compute_mode!r} is not one of "
            f"{', '.join(machines.COMPUTE_MODES)}"
        )
    if compute_mode == machines.COMPUTE_MODE_GPU and not entry.gpu_present:
        raise CampaignError(
            f"{where}: compute mode gpu on machine {machine_id!r}, which is "
            "declared to have no GPU"
        )
    return machine_id, compute_mode


def _exclusions(
    value: object, declaration: CampaignDeclaration
) -> tuple[Exclusion, ...]:
    where = f"campaign {declaration.campaign_id!r}: exclusions"
    if not isinstance(value, list):
        raise CampaignError(f"{where} must be a list, got {value!r}")
    parsed: list[Exclusion] = []
    for position, item in enumerate(value):
        at = f"{where}[{position}]"
        if not isinstance(item, dict):
            raise CampaignError(f"{at} must be an object")
        unknown = sorted(set(item) - _EXCLUSION_KEYS)
        if unknown:
            raise CampaignError(f"{at} carries unknown key(s): {', '.join(unknown)}")
        outcome = item.get("outcome")
        if outcome not in EXCLUSION_OUTCOMES:
            raise CampaignError(
                f"{at}: outcome must be one of {', '.join(EXCLUSION_OUTCOMES)}, "
                f"got {outcome!r}"
            )
        reason = _text(item.get("reason"), f"{at}: reason")
        evidence = _text(item.get("evidence"), f"{at}: evidence")
        variant = (
            _variant(item["prompt_variant"], f"{at}: prompt_variant")
            if "prompt_variant" in item
            else None
        )
        exclusion = Exclusion(
            outcome=outcome,
            reason=reason,
            evidence=evidence,
            engine_id=_coordinate(item, "engine_id", declaration.engines, at),
            prompt_variant=variant,
            roster_entry_id=_coordinate(
                item, "roster_entry_id", declaration.roster_entries, at
            ),
            suite_id=_coordinate(item, "suite_id", declaration.suites, at),
        )
        if variant is not None and variant not in declaration.prompt_variants:
            raise CampaignError(
                f"{at}: prompt_variant {variant[0]}@{variant[1]} is not declared "
                "by this campaign"
            )
        parsed.append(exclusion)
    return tuple(parsed)


def _coordinate(
    item: dict[str, Any], key: str, declared: Sequence[str], at: str
) -> str | None:
    if key not in item:
        return None
    value = _text(item[key], f"{at}: {key}")
    if value not in declared:
        raise CampaignError(
            f"{at}: {key} {value!r} is not declared by this campaign "
            f"(declared: {', '.join(declared)})"
        )
    return value


def check_run(
    declaration: CampaignDeclaration,
    *,
    engine_id: str,
    prompt_variant: prompt_variants.PromptVariant,
    roster_entry_id: str,
    suite_id: str | None,
    machine_id: str,
    compute_mode: str,
    cloud_providers: Iterable[str] = (),
) -> None:
    """Refuse a run outside `declaration`, naming every offending dimension.

    `suite_id` is `None` for a run that scores no suite (the runtime CLI's
    fixed prompt), whose suite is therefore not checked. A cell the
    declaration excludes is refused too: running it would contradict the
    reason the campaign recorded for not running it.
    """
    problems: list[str] = []
    if engine_id not in declaration.engines:
        problems.append(
            f"engine {engine_id!r} is not declared "
            f"(declared: {', '.join(declaration.engines)})"
        )
    variant = (prompt_variant.variant_id, prompt_variant.version)
    if variant not in declaration.prompt_variants:
        problems.append(
            f"prompt variant {variant[0]}@{variant[1]} is not declared (declared: "
            f"{', '.join(f'{v}@{n}' for v, n in declaration.prompt_variants)})"
        )
    if roster_entry_id not in declaration.roster_entries:
        problems.append(
            f"roster entry {roster_entry_id!r} is not declared "
            f"(declared: {', '.join(declaration.roster_entries)})"
        )
    if suite_id is not None and suite_id not in declaration.suites:
        problems.append(
            f"suite {suite_id!r} is not declared "
            f"(declared: {', '.join(declaration.suites)})"
        )
    if (machine_id, compute_mode) != (declaration.machine_id, declaration.compute_mode):
        problems.append(
            f"machine {machine_id!r} in mode {compute_mode!r} is not the declared "
            f"machine {declaration.machine_id!r} in mode {declaration.compute_mode!r}"
        )
    clouds = sorted(cloud_providers)
    if clouds:
        problems.append(
            f"cloud provider(s) {', '.join(clouds)} are enabled in "
            "QUALITY_PROVIDERS: a campaign declares engines, and a cloud "
            "subject runs on none"
        )
    if not problems and suite_id is not None:
        cell = Cell(engine_id, variant[0], variant[1], roster_entry_id, suite_id)
        exclusion = declaration.exclusion_for(cell)
        if exclusion is not None:
            problems.append(
                f"cell {cell.label()} is declared {exclusion.outcome}: "
                f"{exclusion.reason}"
            )
    if problems:
        raise CampaignError(
            f"run refused under campaign {declaration.campaign_id!r}: "
            + "; ".join(problems)
        )


def require_run_campaign(
    settings: Settings,
    *,
    engine_id: str,
    prompt_variant: prompt_variants.PromptVariant,
    roster_entry_id: str,
    suite_id: str | None,
    machine_id: str,
    compute_mode: str,
    cloud_providers: Iterable[str] = (),
) -> str:
    """The `campaign_id` this run's rows carry, or `CampaignError`.

    No `CAMPAIGN_ID`: the run belongs to no campaign and its rows say so
    (`row_contract.NO_CAMPAIGN`). Otherwise the declaration is loaded and the
    run checked against it, before any server starts.
    """
    if settings.campaign_id is None:
        return row_contract.NO_CAMPAIGN
    declaration = load_declaration(
        declaration_path(settings.campaign_id, settings.campaigns_dir),
        roster_path=settings.roster_path,
    )
    check_run(
        declaration,
        engine_id=engine_id,
        prompt_variant=prompt_variant,
        roster_entry_id=roster_entry_id,
        suite_id=suite_id,
        machine_id=machine_id,
        compute_mode=compute_mode,
        cloud_providers=cloud_providers,
    )
    return declaration.campaign_id


def completeness(
    declaration: CampaignDeclaration, rows: Iterable[dict[str, Any]]
) -> list[CellListing]:
    """Every declared cell, in declaration order, with the run ids filling it.

    A row fills a cell when it names this campaign, the cell's engine,
    variant, roster entry and suite, and the campaign's machine and mode.
    The listing depends on nothing but the declaration and the rows, so the
    same rows always give the same listing.
    """
    run_ids: dict[Cell, set[str]] = {}
    for row in rows:
        if row.get("campaign_id") != declaration.campaign_id:
            continue
        if (row.get("machine_id"), row.get("compute_mode")) != (
            declaration.machine_id,
            declaration.compute_mode,
        ):
            continue
        cell = Cell(
            str(row.get("engine_id")),
            str(row.get("prompt_variant_id")),
            str(row.get("prompt_variant_version")),
            str(row.get("roster_entry_id")),
            str(row.get("suite_id")),
        )
        run_ids.setdefault(cell, set()).add(str(row.get("run_id")))

    listing: list[CellListing] = []
    for cell in declaration.cells():
        filled = tuple(sorted(run_ids.get(cell, ())))
        exclusion = declaration.exclusion_for(cell)
        if exclusion is not None:
            status = STATUS_CONTRADICTED if filled else exclusion.outcome
        else:
            status = STATUS_FILLED if filled else STATUS_EMPTY
        listing.append(CellListing(cell, status, filled, exclusion))
    return listing


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="wave-local-ai-v2-campaign-completeness")
    parser.add_argument("--campaign", required=True, metavar="CAMPAIGN_ID")
    parser.add_argument(
        "--campaigns-dir",
        type=Path,
        default=None,
        help=f"Where declarations live (default: CAMPAIGNS_DIR or {DEFAULT_CAMPAIGNS_DIR}).",
    )
    parser.add_argument(
        "--rows",
        type=Path,
        action="append",
        default=None,
        help=(
            "A quality rows file to read; repeatable "
            f"(default: QUALITY_RESULTS_PATH or {DEFAULT_QUALITY_RESULTS_PATH})."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """List every declared cell; exit 1 naming each empty or contradicted one,
    2 when the declaration or the rows cannot be read."""
    args = _parse_args(argv)
    load_dotenv()
    campaigns_dir = args.campaigns_dir or Path(
        os.environ.get("CAMPAIGNS_DIR", DEFAULT_CAMPAIGNS_DIR)
    )
    rows_paths = args.rows or [
        Path(os.environ.get("QUALITY_RESULTS_PATH", DEFAULT_QUALITY_RESULTS_PATH))
    ]
    roster_path = Path(os.environ.get("ROSTER_PATH", DEFAULT_ROSTER_PATH))
    try:
        declaration = load_declaration(
            declaration_path(args.campaign, campaigns_dir), roster_path=roster_path
        )
        absent = [str(path) for path in rows_paths if not path.is_file()]
        if absent:
            raise CampaignError(f"rows file(s) not found: {', '.join(absent)}")
        rows = [row for path in rows_paths for row in results.read_rows(path)]
    except (CampaignError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    listing = completeness(declaration, rows)
    for line in listing:
        print(line.render())
    failing = [line for line in listing if line.status in FAILING_STATUSES]
    if failing:
        for line in failing:
            print(
                f"error: campaign {declaration.campaign_id!r}: {line.status} cell "
                f"{line.cell.label()}",
                file=sys.stderr,
            )
        sys.exit(1)
    print(
        f"campaign {declaration.campaign_id!r}: {len(listing)} declared cell(s), "
        "none empty"
    )
