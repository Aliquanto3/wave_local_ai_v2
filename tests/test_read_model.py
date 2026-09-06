"""The read model over the shared store fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from store_fixtures import (
    FLOOR,
    GRADED_VALUES,
    NAMED_VALUES,
    RUN_ID,
    SUITE_ID,
    make_row,
    write_store,
)

from wave_local_ai_v2 import read_model, row_contract, suite_snapshot
from wave_local_ai_v2.read_model import (
    ABSENCE_REASONS,
    ABSENT_NULL_IN_ROW,
    ABSENT_POINTER_UNRESOLVED,
    ABSENT_PREDATES_SCHEMA,
    Absent,
)


def loaded_roster(bundle: dict[str, Path]) -> Any:
    return read_model.load_roster_file(bundle["roster"])


def build_runtime(bundle: dict[str, Path], rows: list[dict[str, Any]]) -> Any:
    write_store(bundle["runtime"], rows)
    return read_model.runtime_view(
        bundle["runtime"], RUN_ID, FLOOR, bundle["fiches"], loaded_roster(bundle)
    )


def build_quality(bundle: dict[str, Path], rows: list[dict[str, Any]]) -> Any:
    write_store(bundle["quality"], rows)
    return read_model.quality_view(
        bundle["quality"],
        RUN_ID,
        FLOOR,
        loaded_roster(bundle),
        bundle["suites"],
        bundle["fiches"],
    )


def build_energy(bundle: dict[str, Path], rows: list[dict[str, Any]]) -> Any:
    write_store(bundle["runtime"], rows)
    return read_model.energy_view(bundle["runtime"], RUN_ID, FLOOR, "runtime")


def walk(value: Any) -> list[Any]:
    """Every node of a view, so an assertion can sweep a whole response."""
    found = [value]
    if isinstance(value, dict):
        for item in value.values():
            found += walk(item)
    elif isinstance(value, list):
        for item in value:
            found += walk(item)
    return found


# --------------------------------------------------------------------------
# The absence value
# --------------------------------------------------------------------------


def test_resolve_field_distinguishes_absent_key_null_and_value() -> None:
    row = {"schema_version": "7", "present": 1, "explicitly_null": None}

    absent_key = read_model.resolve_field(row, "added_later")
    null_value = read_model.resolve_field(row, "explicitly_null")

    assert absent_key == Absent(ABSENT_PREDATES_SCHEMA, {"row_schema_version": "7"})
    assert null_value == Absent(ABSENT_NULL_IN_ROW, {})
    assert read_model.resolve_field(row, "present") == 1


def test_an_absence_serialises_with_a_marker_a_value_cannot_wear() -> None:
    absent = Absent(ABSENT_NULL_IN_ROW, {})

    assert absent.as_json() == {
        "absent": True,
        "reason": ABSENT_NULL_IN_ROW,
        "detail": {},
    }
    assert read_model.to_jsonable({"a": [absent, 1]}) == {"a": [absent.as_json(), 1]}


# --------------------------------------------------------------------------
# The field partition against `row_contract`
# --------------------------------------------------------------------------

RENDERED_SETS: dict[row_contract.RowKind, dict[str, frozenset[str]]] = {
    "runtime": {
        "RUNS_VIEW_FIELDS": read_model.RUNS_VIEW_FIELDS,
        "ENERGY_VIEW_FIELDS": read_model.ENERGY_VIEW_FIELDS,
        "RUNTIME_VIEW_FIELDS": read_model.RUNTIME_VIEW_FIELDS,
    },
    "quality": {
        "RUNS_VIEW_FIELDS": read_model.RUNS_VIEW_FIELDS,
        "ENERGY_VIEW_FIELDS": read_model.ENERGY_VIEW_FIELDS,
        "QUALITY_VIEW_FIELDS": read_model.QUALITY_VIEW_FIELDS,
        "QUALITY_EXACT_MATCH_FIELDS": read_model.QUALITY_EXACT_MATCH_FIELDS,
    },
}
NOT_RENDERED: dict[row_contract.RowKind, frozenset[str]] = {
    "runtime": read_model.RUNTIME_FIELDS_NOT_RENDERED,
    "quality": read_model.QUALITY_FIELDS_NOT_RENDERED,
}


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_every_contract_field_is_rendered_or_declared_unrendered(
    kind: row_contract.RowKind,
) -> None:
    declared: set[str] = set(NOT_RENDERED[kind])
    for names in RENDERED_SETS[kind].values():
        declared |= names
    contract = set(row_contract.REQUIRED_FIELDS[kind])

    assert declared - contract == set(), (
        f"{kind}: declared but not in the contract: {sorted(declared - contract)}"
    )
    assert contract - declared == set(), (
        f"{kind}: unclassified contract field(s), neither rendered nor "
        f"declared unrendered: {sorted(contract - declared)}"
    )


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_no_field_is_owned_by_two_sets_of_one_kind(
    kind: row_contract.RowKind,
) -> None:
    sets = {**RENDERED_SETS[kind], "NOT_RENDERED": NOT_RENDERED[kind]}
    names = list(sets)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = sets[left] & sets[right]
            assert overlap == frozenset(), (
                f"{kind}: {left} and {right} both own {sorted(overlap)}"
            )


def test_the_judge_and_graded_sets_equal_the_contracts_own() -> None:
    assert read_model.QUALITY_JUDGE_FIELDS == row_contract.JUDGED_FIELDS
    assert read_model.QUALITY_GRADED_FIELDS == row_contract.GRADED_FIELDS


def test_a_field_added_to_the_contract_fails_the_partition(monkeypatch) -> None:
    # The invariant the declarations exist for: a contract change fails the
    # build naming the new field, rather than blanking a column at run time.
    monkeypatch.setitem(
        row_contract.REQUIRED_FIELDS,
        "runtime",
        row_contract.REQUIRED_FIELDS["runtime"] | {"a_field_added_later"},
    )

    with pytest.raises(AssertionError, match="a_field_added_later"):
        test_every_contract_field_is_rendered_or_declared_unrendered("runtime")


# --------------------------------------------------------------------------
# The four views
# --------------------------------------------------------------------------


def test_the_runtime_view_carries_its_fields_and_the_resolved_fiche(
    bundle: dict[str, Path],
) -> None:
    view = build_runtime(bundle, [make_row("runtime")])

    entry = view["entries"][0]
    assert entry["run_id"] == RUN_ID
    assert entry["fiche"] == {"cpu": "a cpu", "gpu": "a gpu"}
    assert entry["roster_entry"]["display_id"] == "Qwen3.6-35B-A3B"
    assert entry["verdict"] == NAMED_VALUES["verdict"]
    assert not any(isinstance(node, Absent) for node in walk(entry))
    # The energy block belongs to its own route, not to this one.
    assert "cpu_energy_kwh" not in entry


def test_the_quality_view_declares_each_rows_shape_and_its_cells(
    bundle: dict[str, Path],
) -> None:
    view = build_quality(bundle, [make_row("quality")])

    entry = view["entries"][0]
    assert view["score_shapes"] == ["exact_match"]
    assert entry["score_shape"] == "exact_match"
    assert entry["language_breakdown"]["en"] == {
        "accuracy": 1.0,
        "indicative": True,
        "n": 1,
    }
    assert entry["suite_definition"]["prompt_set_hash"] == "deadbeef"
    # The suite's items stay in the suite's own file.
    assert "items" not in entry["suite_definition"]


def test_the_energy_view_puts_each_channel_beside_its_own_label(
    bundle: dict[str, Path],
) -> None:
    view = build_energy(bundle, [make_row("runtime")])

    entry = view["entries"][0]
    assert entry["channels"]["gpu"] == {
        "energy_kwh": 0.0009,
        "energy_method": "nvml_sampled",
    }
    assert entry["emissions_kg"] == 0.000074
    assert entry["energy_headline"]["methods"] == {
        "cpu": "estimated_tdp",
        "gpu": "nvml_sampled",
        "ram": "estimated_constant",
    }
    # A composite carries no method label of its own -- the field one would
    # have read was retired at schema "4".
    assert "energy_method" not in entry
    assert "energy_method" not in entry["energy_headline"]


def test_the_runs_view_answers_two_named_collections_never_one_array(
    bundle: dict[str, Path],
) -> None:
    write_store(
        bundle["runtime"],
        [make_row("runtime"), make_row("runtime", run_id="runtime-run-2")],
    )
    write_store(bundle["quality"], [make_row("quality"), make_row("quality")])

    view = read_model.runs_view(
        bundle["runtime"], bundle["quality"], FLOOR, loaded_roster(bundle)
    )

    assert set(view) == {"runtime_runs", "quality_runs"}
    assert [run["run_id"] for run in view["runtime_runs"]["runs"]] == [
        RUN_ID,
        "runtime-run-2",
    ]
    assert view["quality_runs"]["runs"][0]["row_count"] == 2
    assert view["quality_runs"]["schema_floor"] == FLOOR
    # Identity only: no measurement field of either kind reaches the index.
    assert set(view["quality_runs"]["runs"][0]) == {
        "run_id",
        "captured_at",
        "schema_version",
        "roster_entry_id",
        "row_count",
        "roster_entry",
    }


def test_an_unknown_run_is_none_not_an_empty_list(bundle: dict[str, Path]) -> None:
    write_store(bundle["quality"], [make_row("quality")])

    assert (
        read_model.quality_view(
            bundle["quality"],
            "no-such-run",
            FLOOR,
            loaded_roster(bundle),
            bundle["suites"],
            bundle["fiches"],
        )
        is None
    )


# --------------------------------------------------------------------------
# One case per absence reason
# --------------------------------------------------------------------------


def test_a_quality_row_with_no_judge_block_is_absences_not_zeroes(
    bundle: dict[str, Path],
) -> None:
    view = build_quality(bundle, [make_row("quality")])

    judge = view["entries"][0]["judge"]
    assert set(judge) == set(row_contract.JUDGED_FIELDS)
    for field, value in judge.items():
        assert isinstance(value, Absent), f"{field} is not an absence: {value!r}"
        assert value.reason == ABSENT_PREDATES_SCHEMA
        assert value.detail == {"row_schema_version": "11"}
    assert 0 not in judge.values()


def test_a_runtime_row_missing_one_channel_label_withholds_the_headline(
    bundle: dict[str, Path],
) -> None:
    row = make_row("runtime")
    del row["gpu_energy_method"]

    view = build_energy(bundle, [row])

    headline = view["entries"][0]["energy_headline"]
    assert headline["withheld"] is True
    assert [missing["field"] for missing in headline["missing_labels"]] == [
        "gpu_energy_method"
    ]
    assert headline["missing_labels"][0]["absence"].reason == ABSENT_PREDATES_SCHEMA
    assert "energy_kwh" not in headline


def test_a_null_channel_label_also_withholds_the_headline(
    bundle: dict[str, Path],
) -> None:
    view = build_energy(bundle, [make_row("runtime", ram_energy_method=None)])

    headline = view["entries"][0]["energy_headline"]
    assert headline["withheld"] is True
    assert headline["missing_labels"][0]["absence"].reason == ABSENT_NULL_IN_ROW


def test_an_unstored_fiche_hash_is_a_named_pointer_absence_not_an_empty_object(
    bundle: dict[str, Path],
) -> None:
    view = build_runtime(bundle, [make_row("runtime", fiche_hash="f" * 64)])

    fiche = view["entries"][0]["fiche"]
    assert fiche == Absent(
        ABSENT_POINTER_UNRESOLVED, {"pointer": "fiche_hash", "value": "f" * 64}
    )
    assert fiche != {}


def test_a_roster_entry_id_absent_from_the_roster_is_a_named_pointer_absence(
    bundle: dict[str, Path],
) -> None:
    view = build_runtime(bundle, [make_row("runtime", roster_entry_id="not-in-roster")])

    assert view["entries"][0]["roster_entry"] == Absent(
        ABSENT_POINTER_UNRESOLVED,
        {"pointer": "roster_entry_id", "value": "not-in-roster"},
    )


def test_an_unresolved_suite_pointer_names_the_file_it_looked_for(
    bundle: dict[str, Path],
) -> None:
    view = build_quality(bundle, [make_row("quality", suite_version="99")])

    assert view["entries"][0]["suite_definition"] == Absent(
        ABSENT_POINTER_UNRESOLVED,
        {
            "pointer": "suite_id/suite_version",
            "value": suite_snapshot.snapshot_filename(SUITE_ID, "99"),
        },
    )


def test_a_missing_roster_file_leaves_every_entry_named_not_raising(
    bundle: dict[str, Path], tmp_path: Path
) -> None:
    write_store(bundle["runtime"], [make_row("runtime")])

    view = read_model.runtime_view(
        bundle["runtime"],
        RUN_ID,
        FLOOR,
        bundle["fiches"],
        read_model.load_roster_file(tmp_path / "no-roster.json"),
    )

    assert view is not None
    assert view["entries"][0]["roster_entry"].reason == ABSENT_POINTER_UNRESOLVED


def test_a_row_below_the_floor_is_counted_and_never_partially_rendered(
    bundle: dict[str, Path],
) -> None:
    view = build_runtime(
        bundle,
        [make_row("runtime"), make_row("runtime", schema_version="2")],
    )

    assert len(view["entries"]) == 1
    assert view["entries"][0]["schema_version"] == "11"
    assert view["unreadable"] == [
        {"schema_version": "2", "count": 1, "reason": "below_schema_floor"}
    ]


def test_a_run_whose_only_rows_are_below_the_floor_renders_nothing(
    bundle: dict[str, Path],
) -> None:
    assert build_runtime(bundle, [make_row("runtime", schema_version="2")]) is None


# --------------------------------------------------------------------------
# The two score shapes
# --------------------------------------------------------------------------


def test_the_two_score_shapes_stay_separate_in_one_response(
    bundle: dict[str, Path],
) -> None:
    exact = make_row("quality", item_id="exact-01")
    graded = make_row(
        "quality",
        item_id="graded-01",
        correct=None,
        suite_accuracy=None,
        subject_output="une sortie",
        **GRADED_VALUES,
    )

    view = build_quality(bundle, [exact, graded])

    assert view["score_shapes"] == ["exact_match", "graded"]
    exact_entry, graded_entry = view["entries"]
    assert exact_entry["score_shape"] == "exact_match"
    assert graded_entry["score_shape"] == "graded"

    for field in ("correct", "suite_accuracy", "language_breakdown"):
        assert field in exact_entry
        assert field not in graded_entry
    for field in ("item_score", "suite_score", "score_breakdown"):
        assert field in graded_entry
        assert field not in exact_entry

    assert graded_entry["score_breakdown"]["en"] == {
        "score": 0.62,
        "indicative": True,
        "n": 1,
    }


def test_a_graded_cell_missing_a_key_is_an_absence_not_a_hole(
    bundle: dict[str, Path],
) -> None:
    graded_values = {
        **GRADED_VALUES,
        "score_breakdown": {"en": {"score": 0.62, "n": 1}},
    }
    row = make_row(
        "quality",
        correct=None,
        suite_accuracy=None,
        subject_output="une sortie",
        **graded_values,
    )

    view = build_quality(bundle, [row])

    cell = view["entries"][0]["score_breakdown"]["en"]
    assert cell["score"] == 0.62
    assert cell["n"] == 1
    assert isinstance(cell["indicative"], Absent)


# --------------------------------------------------------------------------
# Sweeps over a whole response
# --------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_no_absence_anywhere_carries_a_reason_outside_the_named_three(
    bundle: dict[str, Path], kind: row_contract.RowKind
) -> None:
    stripped = make_row(kind, fiche_hash="0" * 64, roster_entry_id="unknown")
    for field in ("gpu_energy_method", "verdict", "captured_at"):
        stripped.pop(field, None)

    views = [
        build_quality(bundle, [stripped])
        if kind == "quality"
        else build_runtime(bundle, [stripped]),
        build_energy(bundle, [stripped]) if kind == "runtime" else None,
        read_model.runs_view(
            bundle["runtime"], bundle["quality"], FLOOR, loaded_roster(bundle)
        ),
    ]

    absences = [
        node for view in views for node in walk(view) if isinstance(node, Absent)
    ]
    assert absences, "the stripped fixture should produce absences to check"
    for absence in absences:
        assert absence.reason in ABSENCE_REASONS


def test_the_views_never_write_to_the_store(bundle: dict[str, Path]) -> None:
    write_store(bundle["runtime"], [make_row("runtime")])
    write_store(bundle["quality"], [make_row("quality")])
    root = bundle["runtime"].parent
    before = {name: bundle[name].read_bytes() for name in ("runtime", "quality")}
    listing_before = sorted(path.name for path in root.iterdir())
    loaded = loaded_roster(bundle)

    read_model.runtime_view(bundle["runtime"], RUN_ID, FLOOR, bundle["fiches"], loaded)
    read_model.quality_view(
        bundle["quality"], RUN_ID, FLOOR, loaded, bundle["suites"], bundle["fiches"]
    )
    read_model.energy_view(bundle["quality"], RUN_ID, FLOOR, "quality")
    read_model.runs_view(bundle["runtime"], bundle["quality"], FLOOR, loaded)

    assert {
        name: bundle[name].read_bytes() for name in ("runtime", "quality")
    } == before
    assert sorted(path.name for path in root.iterdir()) == listing_before
