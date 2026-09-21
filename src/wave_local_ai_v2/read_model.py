"""The typed read layer over the two stores: four views, and every field a row
does not carry reported as a named absence.

Three rules hold everywhere in this module, and they are the reason it exists
rather than each route shaping its own dictionary:

1. **Nothing is defaulted, zero-filled, back-filled or inferred.** No `or 0`,
   no `.get(field, 0)`, no `dict.setdefault`. A field a row does not carry
   resolves to an `Absent` naming which of three finite reasons applies.
2. **Nothing is computed.** No verdict, no agreement, no score, no aggregate,
   no sum. A row's `verdict` block is returned as it stands; a number absent
   from a row is absent from the view. The one derived value in here,
   `energy_headline`, is a re-presentation of fields already on the row and is
   withheld outright when the labels it would need are not all present.
3. **Nothing is written.** Only read paths are imported, by name rather than
   by module, so `results.append_row`, `fiche_registry.write_fiche` and
   `suite_snapshot`'s exporter are not reachable from here at all.

The field sets each view renders are *partitioned* against `row_contract`
rather than hand-maintained beside it: see `RUNS_VIEW_FIELDS` below and
`tests/test_read_model.py`'s partition tests. A field added to the contract
fails the build until it is either rendered or deliberately declared
unrendered -- the drift is caught at the contract, not discovered as a
silently absent column on a pitch screen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import path_guard, roster, row_contract, scoring
from wave_local_ai_v2.fiche_registry import read_fiche
from wave_local_ai_v2.results import StoreRead, UnreadableRows, read_rows_from_floor
from wave_local_ai_v2.suite_snapshot import snapshot_filename

# The three reasons a field a view names carries no value. Finite and
# collected, so "is this a reason we ship?" is a set membership test rather
# than a grep over call sites.
ABSENT_PREDATES_SCHEMA = "predates_schema"
ABSENT_NULL_IN_ROW = "null_in_row"
ABSENT_POINTER_UNRESOLVED = "pointer_unresolved"
ABSENCE_REASONS: frozenset[str] = frozenset(
    {ABSENT_PREDATES_SCHEMA, ABSENT_NULL_IN_ROW, ABSENT_POINTER_UNRESOLVED}
)

# Which of the two quality score shapes a row publishes. The discriminator is
# the row's own declaration, read exactly as `row_contract._validate_graded_fields`
# reads it, so it cannot drift from what the writer enforced.
SCORE_SHAPE_GRADED = "graded"
SCORE_SHAPE_EXACT_MATCH = "exact_match"

# The three pointers a row cites and this module resolves.
POINTER_FICHE_HASH = "fiche_hash"
POINTER_ROSTER_ENTRY_ID = "roster_entry_id"
POINTER_SUITE = "suite_id/suite_version"


@dataclass(frozen=True)
class Absent:
    """One field's absence, carrying which of `ABSENCE_REASONS` applies."""

    reason: str
    detail: dict[str, Any]

    def as_json(self) -> dict[str, Any]:
        """The JSON form, marked so a reader cannot mistake it for a value.

        The `absent` marker is the whole point of the contract at the JSON
        boundary: `{"reason": ...}` alone is an object like any other, while
        `{"absent": true, ...}` cannot be read as a measurement by accident.
        """
        return {"absent": True, "reason": self.reason, "detail": dict(self.detail)}


def to_jsonable(value: Any) -> Any:
    """Walk `value`, replacing every `Absent` with its marked JSON form.

    The views build `Absent` instances so a caller can test them by identity;
    this is the one place they become JSON. Nothing else is transformed --
    no key is added, dropped, ordered or renamed on the way through.
    """
    if isinstance(value, Absent):
        return value.as_json()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    return value


def resolve_field(row: dict[str, Any], field: str) -> Any | Absent:
    """`row[field]`, or the `Absent` that says why there is no value.

    The absent-key branch is sound rather than a guess: `results.append_row`
    gates every write on `row_contract.validate_row`, so a row written at the
    current schema carries every key its kind requires. A key that is not
    there can therefore only mean the row predates the field -- which is why
    the absence names the row's own `schema_version` and not the service's
    floor.

    A key present with value `None` is a different fact, and `row_contract`
    says so in its own module docstring: several fields degrade to an explicit
    `None` on capture failure and the row is still complete.
    """
    if field not in row:
        return Absent(
            ABSENT_PREDATES_SCHEMA, {"row_schema_version": row.get("schema_version")}
        )
    value = row[field]
    if value is None:
        return Absent(ABSENT_NULL_IN_ROW, {})
    return value


def resolve_fields(row: dict[str, Any], fields: frozenset[str]) -> dict[str, Any]:
    """`resolve_field` over `fields`, in a stable alphabetical order."""
    return {field: resolve_field(row, field) for field in sorted(fields)}


# --------------------------------------------------------------------------
# The field partition against `row_contract`.
#
# For each row kind, the union of every rendered set below and that kind's
# not-rendered set equals `row_contract.REQUIRED_FIELDS[kind]` exactly, and
# the sets are pairwise disjoint. `QUALITY_JUDGE_FIELDS` and
# `QUALITY_GRADED_FIELDS` sit outside that union, matching the contract:
# `JUDGED_FIELDS` and `GRADED_FIELDS` are conditional blocks, not required
# fields, and each of those two sets equals the contract's own exactly.
#
# The sets are declarations of *which view owns a field*, not of the JSON
# shape it lands in: `RUNS_VIEW_FIELDS` is the identity block every view
# carries, so a runtime entry still states its own `run_id` without that
# field being declared twice.
#
# Which fields a row *owes* is `row_contract`'s business and is never
# restated here.
# --------------------------------------------------------------------------

RUNS_VIEW_FIELDS: frozenset[str] = frozenset(
    {
        "run_id",
        "captured_at",
        "schema_version",
        "roster_entry_id",
        "release_version",
        "commit_sha",
        "tree_dirty",
    }
)

# Both row kinds carry the same thirteen energy/emissions fields (schema "4"),
# which is why one set serves the energy route over either store.
ENERGY_VIEW_FIELDS: frozenset[str] = frozenset(
    {
        "cpu_energy_kwh",
        "cpu_energy_method",
        "gpu_energy_kwh",
        "gpu_energy_method",
        "ram_energy_kwh",
        "ram_energy_method",
        "energy_kwh",
        "emissions_kg",
        "emission_factor_kg_per_kwh",
        "emission_region",
        "emissions_scope",
        "emissions_scope_formula_id",
        "scope_comparability",
    }
)

# The three per-channel labels, paired with the channel each labels. The
# composite (`energy_kwh` / `emissions_kg`) deliberately has no label of its
# own: the single `energy_method` field one would have read was retired at
# schema "4" and replaced by exactly these three.
ENERGY_CHANNELS: tuple[tuple[str, str, str], ...] = (
    ("cpu", "cpu_energy_kwh", "cpu_energy_method"),
    ("gpu", "gpu_energy_kwh", "gpu_energy_method"),
    ("ram", "ram_energy_kwh", "ram_energy_method"),
)

RUNTIME_VIEW_FIELDS: frozenset[str] = frozenset(
    {
        "roster_version",
        "endpoint",
        "prompt_template_id",
        "prompt_template_hash",
        "prompt_capture",
        "fiche_hash",
        "verdict",
        "max_tokens",
        "wall_clock_s",
        "ttft_ms",
        "prompt_tok_per_s",
        "gen_tok_per_s",
        "ttft_source",
        "vram_used_mib",
        "gpu_draw_w",
        "process_rss_bytes",
        "tokens_in_total",
        "tokens_out_total",
        "cost_total",
        "cost_currency",
        "cost_per_million_tokens",
        "normalization_unit",
        "kwh_price_eur",
        "kwh_price_currency",
        "kwh_price_recorded_at",
        "list_price_input_per_million",
        "list_price_output_per_million",
        "list_price_per_million_tokens",
        "list_price_currency",
        "list_price_retrieved_at",
        "sampling",
        "seed_pinned",
        "warmup_count",
        "warmup_repetitions",
        "restart_between_repetitions",
        "cooldown_s",
        "repetitions_n",
        "slot_reset_method",
        "aggregation",
        "ttft_ms_mean",
        "ttft_ms_sd",
        "ttft_ms_spread",
        "prompt_tok_per_s_mean",
        "prompt_tok_per_s_sd",
        "prompt_tok_per_s_spread",
        "gen_tok_per_s_mean",
        "gen_tok_per_s_sd",
        "gen_tok_per_s_spread",
        "unreliable",
        "thermal_posture",
    }
)

RUNTIME_FIELDS_NOT_RENDERED: frozenset[str] = frozenset(
    {
        # The benchmark prompt's own text. It is on the row so a run can be
        # reproduced, not so it can be read in a table, and one cell holding
        # it would crowd out every measurement beside it.
        "prompt",
        # The raw per-repetition array. What a reader compares is the row's
        # own `ttft_ms_mean` / `_sd` / `_spread` -- already rendered -- and
        # this is what those were computed from. Rendering both would invite
        # a recomputation in the browser, which is exactly the aggregate this
        # module refuses to produce.
        "repetitions",
    }
)

QUALITY_VIEW_FIELDS: frozenset[str] = frozenset(
    {
        "roster_version",
        "endpoint",
        "prompt_template_id",
        "prompt_template_hash",
        "prompt_capture",
        "model_id",
        "provider",
        "fiche_hash",
        "verdict",
        "task_suite",
        "item_id",
        "expected_label",
        "predicted_label",
        "sampling",
        "max_output_tokens",
        "stop_sequences",
        "thinking_policy",
        "context_length",
        "suite_id",
        "suite_version",
        "prompt_set_hash",
        "language",
        "provenance",
        "contamination_risk",
        "indicative",
        "indicative_reasons",
        "failure_reason",
        "failure_counts",
        "retries",
        "resumed",
        "tokens_in_total",
        "tokens_out_total",
        "cost_total",
        "cost_currency",
        "cost_per_million_tokens",
        "normalization_unit",
        "kwh_price_eur",
        "kwh_price_currency",
        "kwh_price_recorded_at",
        "list_price_input_per_million",
        "list_price_output_per_million",
        "list_price_per_million_tokens",
        "list_price_currency",
        "list_price_retrieved_at",
    }
)

# The exact-match shape's own three fields. Required on every quality row by
# the contract (they predate the graded block), but rendered only on a row
# that declares itself exact-match: a graded row carries them as explicit
# `null`, and publishing an accuracy of `null` beside a chrF score is the
# merge Methodology 4 forbids.
QUALITY_EXACT_MATCH_FIELDS: frozenset[str] = frozenset(
    {"correct", "suite_accuracy", "language_breakdown"}
)

QUALITY_FIELDS_NOT_RENDERED: frozenset[str] = frozenset(
    {
        # The item's own prompt text. The suite definition the row cites
        # carries it, and that pointer is resolved beside the entry -- so the
        # text is one hop away rather than duplicated on all 591 rows of a
        # store.
        "prompt",
    }
)

# Equal to the contract's own two conditional blocks, asserted rather than
# assumed (see the partition tests). A judged or graded row owes all of its
# block; a row carrying none of it resolves every field to an absence.
QUALITY_JUDGE_FIELDS: frozenset[str] = row_contract.JUDGED_FIELDS
QUALITY_GRADED_FIELDS: frozenset[str] = row_contract.GRADED_FIELDS

# The keys one per-language cell carries, per shape. The graded set is the
# contract's own declaration; the exact-match one is derived from
# `scoring.LanguageCell`, the writer's own type, because `row_contract`
# declares no counterpart for `language_breakdown` yet -- a one-line gap
# worth closing there, not worth a second hand-maintained list here.
GRADED_LANGUAGE_CELL_FIELDS: frozenset[str] = row_contract.GRADED_LANGUAGE_CELL_FIELDS
EXACT_MATCH_LANGUAGE_CELL_FIELDS: frozenset[str] = frozenset(
    scoring.LanguageCell.__annotations__
)


# The ordered, extensible list of dimensions a comparison column's identity
# is built from. Adding a dimension means appending a name here and, once it
# resolves from the row rather than the roster entry, teaching
# `_resolve_comparison_dimension` how to read it -- never reshaping the
# column-assembly loop in `_comparison_columns`. Reserved future entries:
# `machine`, `engine`, `prompt_variant`, each resolved from the row once it
# carries the field; `architecture` alone resolves from the roster entry
# today.
COMPARISON_DIMENSIONS: tuple[str, ...] = ("architecture",)


def _resolve_comparison_dimension(
    row: dict[str, Any], dimension: str, resolved_roster_entry: Any | Absent
) -> Any | Absent:
    """One dimension's value for a column, given its resolved roster entry."""
    if dimension == "architecture":
        if isinstance(resolved_roster_entry, Absent):
            return resolved_roster_entry
        return resolved_roster_entry["architecture"]
    return resolve_field(row, dimension)


def load_roster_file(path: Path) -> roster.RosterFile | None:
    """The roster at `path`, or `None` when it cannot be read.

    A read-only service must not fail a whole view because the roster file is
    absent or malformed: with `None`, every `roster_entry_id` resolves to a
    `pointer_unresolved` absence naming the id, which is the same fact stated
    per row instead of as a stack trace.
    """
    try:
        return roster.load_roster(path)
    except roster.RosterError:
        return None


def _unresolved(pointer: str, value: Any) -> Absent:
    return Absent(ABSENT_POINTER_UNRESOLVED, {"pointer": pointer, "value": value})


def resolve_fiche(row: dict[str, Any], fiche_registry_dir: Path) -> Any | Absent:
    """The stored fiche the row cites, or the absence that says why not.

    A hash with no file behind it is `pointer_unresolved` naming the hash --
    never `{}`, which a caller would render as a fiche with no fields rather
    than as a fiche that is not there.

    A stored file that cannot be read or parsed is the same fact to a reader
    -- the pointer did not resolve -- and is reported the same way, exactly as
    `resolve_suite_definition` reports an unreadable snapshot. `read_fiche`
    parses JSON without catching, and one corrupt file in the registry must
    not take a whole view down with a 500.
    """
    fiche_hash = resolve_field(row, POINTER_FICHE_HASH)
    if isinstance(fiche_hash, Absent):
        return fiche_hash
    try:
        fiche = read_fiche(str(fiche_hash), fiche_registry_dir)
    except (OSError, json.JSONDecodeError):
        return _unresolved(POINTER_FICHE_HASH, fiche_hash)
    if fiche is None:
        return _unresolved(POINTER_FICHE_HASH, fiche_hash)
    return fiche


def resolve_roster_entry(
    row: dict[str, Any], roster_file: roster.RosterFile | None
) -> Any | Absent:
    """The roster entry the row cites, reduced to its identity fields."""
    entry_id = resolve_field(row, POINTER_ROSTER_ENTRY_ID)
    if isinstance(entry_id, Absent):
        return entry_id
    if roster_file is None or entry_id not in roster_file.entries:
        return _unresolved(POINTER_ROSTER_ENTRY_ID, entry_id)
    entry = roster_file.entries[str(entry_id)]
    return {
        "entry_id": entry.entry_id,
        "display_id": entry.display_id,
        "repo": entry.repo,
        "revision": entry.revision,
        "file": entry.file,
        "quant": entry.quant,
        "sha256": entry.sha256,
        "family": entry.family,
        "architecture": {
            "kind": entry.architecture.kind,
            "expert_count": entry.architecture.expert_count,
            "active_params_b": entry.architecture.active_params_b,
        },
        "roster_version": roster_file.roster_version,
    }


def resolve_suite_definition(
    row: dict[str, Any], suite_definitions_dir: Path
) -> Any | Absent:
    """The suite snapshot the row's `suite_id`/`suite_version` pair names.

    Reduced to the snapshot's identity and caps, deliberately without its
    `items` array: copying twenty prompts onto every row of a suite would
    make the response about the suite rather than about the run, and the file
    itself is one hop away for a reader who wants them.
    """
    suite_id = resolve_field(row, "suite_id")
    suite_version = resolve_field(row, "suite_version")
    for pointer_part in (suite_id, suite_version):
        if isinstance(pointer_part, Absent):
            return pointer_part

    filename = snapshot_filename(str(suite_id), str(suite_version))
    path = path_guard.resolve_within_root(suite_definitions_dir, filename)
    if path is None or not path.exists():
        return _unresolved(POINTER_SUITE, filename)
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _unresolved(POINTER_SUITE, filename)
    if not isinstance(snapshot, dict):
        return _unresolved(POINTER_SUITE, filename)

    # The stored artifact as it stands, exactly as `resolve_fiche` returns the
    # stored fiche -- minus `items` only, per the docstring above. No key is
    # renamed, defaulted or counted on the way through.
    return {
        "snapshot_filename": filename,
        **{key: value for key, value in snapshot.items() if key != "items"},
    }


def _unreadable_as_json(unreadable: list[UnreadableRows]) -> list[dict[str, Any]]:
    return [
        {
            "schema_version": entry.schema_version,
            "count": entry.count,
            "reason": entry.reason,
        }
        for entry in unreadable
    ]


def _identity(row: dict[str, Any]) -> dict[str, Any]:
    return resolve_fields(row, RUNS_VIEW_FIELDS)


def _rows_for_run(store: StoreRead, run_id: str) -> list[dict[str, Any]]:
    return [row for row in store.rows if row.get("run_id") == run_id]


def _dedup_key(value: Any) -> Any:
    """A hashable stand-in for `value`, since an `Absent` carries a `dict`.

    Two `Absent`s with the same reason and detail dedupe together; two with
    different detail (e.g. a different unresolved id) stay distinct entries,
    matching "unresolved ids kept as their own absence rather than dropped".
    """
    if isinstance(value, Absent):
        return ("absent", value.reason, tuple(sorted(value.detail.items())))
    return value


def _runs_collection(
    path: Path,
    floor: str,
    roster_file: roster.RosterFile | None,
    *,
    with_suites: bool,
) -> dict[str, Any]:
    """One store's runs, grouped by `run_id` in first-seen file order."""
    store = read_rows_from_floor(path, floor)
    first_row: dict[str, dict[str, Any]] = {}
    row_counts: dict[str, int] = {}
    models: dict[str, dict[Any, Any]] = {}
    suites: dict[str, dict[Any, Any]] = {}
    for row in store.rows:
        run_id = row.get("run_id")
        key = "" if run_id is None else str(run_id)
        if key not in first_row:
            first_row[key] = row
        row_counts[key] = row_counts.get(key, 0) + 1

        entry_id = resolve_field(row, POINTER_ROSTER_ENTRY_ID)
        run_models = models.setdefault(key, {})
        model_key = _dedup_key(entry_id)
        if model_key not in run_models:
            run_models[model_key] = resolve_roster_entry(row, roster_file)

        if with_suites:
            task_suite = resolve_field(row, "task_suite")
            run_suites = suites.setdefault(key, {})
            run_suites.setdefault(_dedup_key(task_suite), task_suite)

    runs = []
    for key, row in first_row.items():
        entry: dict[str, Any] = {
            # The run's own first row states these; they are not reduced,
            # ranged or otherwise summarised across the run, since a min/max
            # over `captured_at` would be an aggregate this module does not
            # produce.
            **_identity(row),
            "row_count": row_counts[key],
            "roster_entry": resolve_roster_entry(row, roster_file),
            "models": list(models[key].values()),
        }
        if with_suites:
            entry["suites"] = list(suites[key].values())
        runs.append(entry)

    return {
        "schema_floor": floor,
        "runs": runs,
        "unreadable": _unreadable_as_json(store.unreadable),
    }


def runs_view(
    runtime_path: Path,
    quality_path: Path,
    floor: str,
    roster_file: roster.RosterFile | None,
) -> dict[str, Any]:
    """The run index: two separately named collections, never one array.

    The two CLIs mint independent `run_id`s over independent stores, so a
    single sorted list would invite a join that has no meaning. Naming the
    collections separately makes the response un-mergeable by shape rather
    than by convention -- and each carries its own `unreadable` count, since
    "how many rows this store holds that I could not read" is a fact about
    one file, not about the pair.

    `suites` is a quality-only key: a runtime row carries no suite dimension,
    so a runtime entry carries `models` only, never `suites` set to an
    absence -- a key that is always absent is worse than a key that does not
    exist.
    """
    return {
        "runtime_runs": _runs_collection(
            runtime_path, floor, roster_file, with_suites=False
        ),
        "quality_runs": _runs_collection(
            quality_path, floor, roster_file, with_suites=True
        ),
    }


def _resolve_language_cells(
    row: dict[str, Any], field: str, cell_fields: frozenset[str]
) -> Any | Absent:
    """A per-language breakdown with each cell resolved key by key.

    The `n` and the `indicative` mark travel with the score they qualify
    (Methodology 4), and a cell missing one of them shows an absence rather
    than a hole a reader would fill in themselves.
    """
    breakdown = resolve_field(row, field)
    if isinstance(breakdown, Absent) or not isinstance(breakdown, dict):
        return breakdown
    return {
        language: (
            {key: resolve_field(cell, key) for key in sorted(cell_fields)}
            if isinstance(cell, dict)
            else cell
        )
        for language, cell in breakdown.items()
    }


def score_shape_of(row: dict[str, Any]) -> str:
    """Which of the two quality score shapes `row` declares.

    The same rule `row_contract._validate_graded_fields` applies at the
    writer: carrying any member of `GRADED_FIELDS` is the declaration. Read
    the same way here so the discriminator cannot drift from the one the
    store was validated against.
    """
    if QUALITY_GRADED_FIELDS & row.keys():
        return SCORE_SHAPE_GRADED
    return SCORE_SHAPE_EXACT_MATCH


def _quality_entry(
    row: dict[str, Any],
    *,
    fiche_registry_dir: Path,
    roster_file: roster.RosterFile | None,
    suite_definitions_dir: Path,
) -> dict[str, Any]:
    shape = score_shape_of(row)
    entry: dict[str, Any] = {
        **_identity(row),
        **resolve_fields(row, QUALITY_VIEW_FIELDS),
        "score_shape": shape,
        "roster_entry": resolve_roster_entry(row, roster_file),
        "fiche": resolve_fiche(row, fiche_registry_dir),
        "suite_definition": resolve_suite_definition(row, suite_definitions_dir),
        # Every judge field, resolved. No store holds a judged row today, so
        # every one of these is an absence -- the live path this ships, not a
        # branch reserved for later. `agreement` and `single_judge` are
        # rendered as they stand; no agreement is computed here.
        "judge": resolve_fields(row, QUALITY_JUDGE_FIELDS),
    }
    # The shape's own fields, and the other shape's omitted entirely: never
    # null-filled, never both under one key.
    if shape == SCORE_SHAPE_GRADED:
        entry.update(resolve_fields(row, QUALITY_GRADED_FIELDS))
        entry["score_breakdown"] = _resolve_language_cells(
            row, "score_breakdown", GRADED_LANGUAGE_CELL_FIELDS
        )
    else:
        entry.update(resolve_fields(row, QUALITY_EXACT_MATCH_FIELDS))
        entry["language_breakdown"] = _resolve_language_cells(
            row, "language_breakdown", EXACT_MATCH_LANGUAGE_CELL_FIELDS
        )
    return entry


def quality_view(
    quality_path: Path,
    run_id: str,
    floor: str,
    roster_file: roster.RosterFile | None,
    suite_definitions_dir: Path,
    fiche_registry_dir: Path,
) -> dict[str, Any] | None:
    """One entry per quality row of `run_id`, or `None` when the run has none.

    `None` is not an empty list: a run with no readable row and a run that
    does not exist are different facts, and the caller answers them
    differently.
    """
    store = read_rows_from_floor(quality_path, floor)
    rows = _rows_for_run(store, run_id)
    if not rows:
        return None
    entries = [
        _quality_entry(
            row,
            fiche_registry_dir=fiche_registry_dir,
            roster_file=roster_file,
            suite_definitions_dir=suite_definitions_dir,
        )
        for row in rows
    ]
    return {
        "store": "quality",
        "run_id": run_id,
        "schema_floor": floor,
        # Stated at the response level so a reader meeting a mixed response
        # knows both shapes are in it before reading a single entry.
        "score_shapes": sorted({str(entry["score_shape"]) for entry in entries}),
        "entries": entries,
        "unreadable": _unreadable_as_json(store.unreadable),
    }


def runtime_view(
    runtime_path: Path,
    run_id: str,
    floor: str,
    fiche_registry_dir: Path,
    roster_file: roster.RosterFile | None,
) -> dict[str, Any] | None:
    """One entry per runtime row of `run_id`, each with its fiche resolved."""
    store = read_rows_from_floor(runtime_path, floor)
    rows = _rows_for_run(store, run_id)
    if not rows:
        return None
    entries = [
        {
            **_identity(row),
            **resolve_fields(row, RUNTIME_VIEW_FIELDS),
            "roster_entry": resolve_roster_entry(row, roster_file),
            "fiche": resolve_fiche(row, fiche_registry_dir),
        }
        for row in rows
    ]
    return {
        "store": "runtime",
        "run_id": run_id,
        "schema_floor": floor,
        "entries": entries,
        "unreadable": _unreadable_as_json(store.unreadable),
    }


def _energy_entry(row: dict[str, Any]) -> dict[str, Any]:
    channels = {
        channel: {
            "energy_kwh": resolve_field(row, energy_field),
            "energy_method": resolve_field(row, method_field),
        }
        for channel, energy_field, method_field in ENERGY_CHANNELS
    }
    composite = resolve_fields(
        row,
        ENERGY_VIEW_FIELDS
        - {energy for _, energy, _ in ENERGY_CHANNELS}
        - {method for _, _, method in ENERGY_CHANNELS},
    )
    missing_labels = [
        {"field": method_field, "absence": channels[channel]["energy_method"]}
        for channel, _, method_field in ENERGY_CHANNELS
        if isinstance(channels[channel]["energy_method"], Absent)
    ]
    if missing_labels:
        # No headline at all rather than one carrying an unlabelled number:
        # each missing label states its own three-reason absence, so the
        # caller learns which label is missing and why without a fourth
        # reason being invented for the composite.
        headline: dict[str, Any] = {
            "withheld": True,
            "missing_labels": missing_labels,
        }
    else:
        headline = {
            "energy_kwh": composite["energy_kwh"],
            "emissions_kg": composite["emissions_kg"],
            # Three labels, never one: the single `energy_method` field a
            # composite headline would have carried was retired at schema "4".
            "methods": {
                channel: channels[channel]["energy_method"]
                for channel, _, _ in ENERGY_CHANNELS
            },
        }
    return {
        **_identity(row),
        "channels": channels,
        **composite,
        "energy_headline": headline,
    }


def energy_view(
    path: Path, run_id: str, floor: str, store_name: str
) -> dict[str, Any] | None:
    """The per-run energy detail over exactly one store.

    `store_name` is the caller's explicit choice, never probed: both row
    kinds carry the same thirteen energy fields, so reading one store then
    the other would make the service read both to answer one view and leave
    the response ambiguous about where a number came from.
    """
    read = read_rows_from_floor(path, floor)
    rows = _rows_for_run(read, run_id)
    if not rows:
        return None
    return {
        "store": store_name,
        "run_id": run_id,
        "schema_floor": floor,
        "entries": [_energy_entry(row) for row in rows],
        "unreadable": _unreadable_as_json(read.unreadable),
    }


@dataclass(frozen=True)
class _ComparisonColumn:
    """One `(suite_id, roster_entry_id)` column, backed by its winning run.

    `rows_by_item` is keyed by `_dedup_key(item_id)` -- an `Absent` `item_id`
    is unhashable on its own, exactly the reason `_runs_collection` dedupes
    the same way -- and carries the item's own (possibly absent) id beside
    its row, so the union and the cells can both be built from it without
    resolving the row twice.
    """

    roster_entry_id: Any
    run_id: Any
    suite_version: Any
    prompt_set_hash: Any
    thinking_policy: Any
    roster_entry: Any
    dimensions: dict[str, Any]
    rows_by_item: dict[Any, tuple[Any, dict[str, Any]]]


def _captured_at_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    """`(captured_at, run_id)` as strings, so the latest run sorts greatest.

    Compared as strings, not parsed as datetimes: `captured_at` is written as
    ISO 8601 in one timezone, which already sorts correctly lexically, and
    parsing here would be one more thing this module computes rather than
    reads. `run_id` breaks a tie deterministically rather than by dict order.
    """
    captured_at = row.get("captured_at")
    run_id = row.get("run_id")
    return (
        "" if captured_at is None else str(captured_at),
        "" if run_id is None else str(run_id),
    )


def _comparison_columns(
    store: StoreRead, roster_file: roster.RosterFile | None
) -> list[tuple[Any, list[_ComparisonColumn]]]:
    """The quality store's rows, grouped by `suite_id` then `roster_entry_id`.

    One column per group, backed only by the rows of the single run carrying
    the greatest `captured_at` in it -- a later run of the same model on the
    same suite supersedes an earlier one rather than being merged with it.
    Suites, and roster_entry_ids within a suite, are ordered by their string
    form for a stable response rather than by first-seen file order.
    """
    groups: dict[Any, tuple[Any, dict[Any, dict[Any, list[dict[str, Any]]]]]] = {}
    for row in store.rows:
        suite_id = resolve_field(row, "suite_id")
        suite_key = _dedup_key(suite_id)
        entry_id = resolve_field(row, POINTER_ROSTER_ENTRY_ID)
        entry_key = _dedup_key(entry_id)
        run_id = row.get("run_id")
        run_key = "" if run_id is None else str(run_id)

        _, by_entry = groups.setdefault(suite_key, (suite_id, {}))
        by_run = by_entry.setdefault(entry_key, {})
        by_run.setdefault(run_key, []).append(row)

    result: list[tuple[Any, list[_ComparisonColumn]]] = []
    for suite_key in sorted(groups, key=str):
        suite_id, by_entry = groups[suite_key]
        columns: list[_ComparisonColumn] = []
        for entry_key in sorted(by_entry, key=str):
            by_run = by_entry[entry_key]
            winning_run_key = max(
                by_run, key=lambda key: _captured_at_sort_key(by_run[key][0])
            )
            winning_rows = by_run[winning_run_key]
            sample = winning_rows[0]
            roster_entry = resolve_roster_entry(sample, roster_file)
            dimensions = {
                dimension: _resolve_comparison_dimension(
                    sample, dimension, roster_entry
                )
                for dimension in COMPARISON_DIMENSIONS
            }
            rows_by_item = {
                _dedup_key(resolve_field(row, "item_id")): (
                    resolve_field(row, "item_id"),
                    row,
                )
                for row in winning_rows
            }
            columns.append(
                _ComparisonColumn(
                    roster_entry_id=resolve_field(sample, POINTER_ROSTER_ENTRY_ID),
                    run_id=resolve_field(sample, "run_id"),
                    suite_version=resolve_field(sample, "suite_version"),
                    prompt_set_hash=resolve_field(sample, "prompt_set_hash"),
                    thinking_policy=resolve_field(sample, "thinking_policy"),
                    roster_entry=roster_entry,
                    dimensions=dimensions,
                    rows_by_item=rows_by_item,
                )
            )
        result.append((suite_id, columns))
    return result


def comparison_view(
    quality_path: Path,
    floor: str,
    roster_file: roster.RosterFile | None,
    suite_definitions_dir: Path,
    fiche_registry_dir: Path,
) -> dict[str, Any]:
    """Every roster model, side by side, over the same items of each suite.

    Store-wide by construction -- no `run_id` names all the rows a column
    needs, since each column may be backed by a different run of a different
    model. One entry per `suite_id` present in the quality store; within it,
    one column per `(suite_id, roster_entry_id)` and one row per `item_id`
    the union of every column's suite carries. A column missing an item its
    suite union carries renders that cell `{"status": "not_compared"}` --
    never a blank or a zero.
    """
    store = read_rows_from_floor(quality_path, floor)
    grouped = _comparison_columns(store, roster_file)

    suites = []
    for suite_id, columns in grouped:
        item_order: dict[Any, Any] = {}
        for column in columns:
            for key, (item_id, _row) in column.rows_by_item.items():
                item_order.setdefault(key, item_id)
        sorted_keys = sorted(item_order, key=lambda key: str(item_order[key]))

        items = []
        for key in sorted_keys:
            item_id = item_order[key]
            cells = []
            for column in columns:
                entry = column.rows_by_item.get(key)
                if entry is None:
                    cells.append({"status": "not_compared", "item_id": item_id})
                else:
                    _, row = entry
                    cells.append(
                        {
                            "status": "compared",
                            **_quality_entry(
                                row,
                                fiche_registry_dir=fiche_registry_dir,
                                roster_file=roster_file,
                                suite_definitions_dir=suite_definitions_dir,
                            ),
                        }
                    )
            items.append({"item_id": item_id, "cells": cells})

        suites.append(
            {
                "suite_id": suite_id,
                "columns": [
                    {
                        "roster_entry_id": column.roster_entry_id,
                        "run_id": column.run_id,
                        "suite_version": column.suite_version,
                        "prompt_set_hash": column.prompt_set_hash,
                        "thinking_policy": column.thinking_policy,
                        "roster_entry": column.roster_entry,
                        "dimensions": column.dimensions,
                    }
                    for column in columns
                ],
                "items": items,
            }
        )

    return {
        "store": "quality",
        "schema_floor": floor,
        "suites": suites,
        "unreadable": _unreadable_as_json(store.unreadable),
    }
