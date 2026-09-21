"""The read model over the shared store fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from store_fixtures import (
    FLOOR,
    GRADED_VALUES,
    NAMED_VALUES,
    ROSTER_ENTRY_ID,
    RUN_ID,
    SUITE_ID,
    make_row,
    write_store,
)

from wave_local_ai_v2 import read_model, results, row_contract, settings, suite_snapshot
from wave_local_ai_v2.read_model import (
    ABSENCE_REASONS,
    ABSENT_NULL_IN_ROW,
    ABSENT_POINTER_UNRESOLVED,
    ABSENT_PREDATES_SCHEMA,
    Absent,
)

# The committed reference bundle, entirely schema "7" -- see
# tests/test_reference_bundle.py's own PUBLISHED_BUNDLE_SCHEMA_VERSION for why
# this is pinned rather than read from row_contract.SCHEMA_VERSION.
REFERENCE_BUNDLE_SCHEMA_VERSION = "7"
QUALITY_REFERENCE_PATH = Path(settings.DEFAULT_QUALITY_REFERENCE_PATH)
RUNTIME_REFERENCE_PATH = Path(settings.DEFAULT_RUNTIME_REFERENCE_PATH)
SUITE_DEFINITIONS_DIR = Path(settings.DEFAULT_SUITE_DEFINITIONS_DIR)
FICHE_REGISTRY_DIR = Path(settings.DEFAULT_FICHE_REGISTRY_DIR)
ROSTER_PATH = Path(settings.DEFAULT_ROSTER_PATH)


def reference_bundle_quality_view() -> dict[str, Any]:
    run_id = results.read_rows(QUALITY_REFERENCE_PATH)[0]["run_id"]
    view = read_model.quality_view(
        QUALITY_REFERENCE_PATH,
        str(run_id),
        REFERENCE_BUNDLE_SCHEMA_VERSION,
        read_model.load_roster_file(ROSTER_PATH),
        SUITE_DEFINITIONS_DIR,
        FICHE_REGISTRY_DIR,
    )
    assert view is not None
    return view


def reference_bundle_runtime_view() -> dict[str, Any]:
    run_id = results.read_rows(RUNTIME_REFERENCE_PATH)[0]["run_id"]
    view = read_model.runtime_view(
        RUNTIME_REFERENCE_PATH,
        str(run_id),
        REFERENCE_BUNDLE_SCHEMA_VERSION,
        FICHE_REGISTRY_DIR,
        read_model.load_roster_file(ROSTER_PATH),
    )
    assert view is not None
    return view


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
        "release_version",
        "commit_sha",
        "tree_dirty",
        "row_count",
        "roster_entry",
        "models",
        "suites",
    }
    # Runtime carries models but never a suites key at all: the concept does
    # not apply to a runtime row.
    assert "suites" not in view["runtime_runs"]["runs"][0]


def test_the_runs_view_surfaces_the_three_relocated_fields(
    bundle: dict[str, Path],
) -> None:
    write_store(
        bundle["runtime"],
        [
            make_row(
                "runtime",
                release_version="1.2.3",
                commit_sha="deadbeef",
                tree_dirty=True,
            )
        ],
    )

    view = read_model.runs_view(
        bundle["runtime"], bundle["quality"], FLOOR, loaded_roster(bundle)
    )

    run = view["runtime_runs"]["runs"][0]
    assert run["release_version"] == "1.2.3"
    assert run["commit_sha"] == "deadbeef"
    assert run["tree_dirty"] is True
    # Relocated out of the per-run-entry views, not duplicated into them.
    assert "release_version" not in view["runtime_runs"]["runs"][0]["roster_entry"]


def test_the_runs_view_enumerates_distinct_models_and_suites(
    bundle: dict[str, Path],
) -> None:
    write_store(
        bundle["quality"],
        [
            make_row("quality", task_suite="suite-a"),
            make_row("quality", task_suite="suite-b"),
            make_row("quality", roster_entry_id="unknown-entry", task_suite="suite-a"),
        ],
    )

    view = read_model.runs_view(
        bundle["runtime"], bundle["quality"], FLOOR, loaded_roster(bundle)
    )

    run = view["quality_runs"]["runs"][0]
    assert run["suites"] == ["suite-a", "suite-b"]
    models = run["models"]
    assert len(models) == 2
    assert models[0]["display_id"] == "Qwen3.6-35B-A3B"
    assert isinstance(models[1], Absent)
    assert models[1].reason == ABSENT_POINTER_UNRESOLVED


def test_a_runtime_only_store_carries_models_but_no_suites_key(
    bundle: dict[str, Path],
) -> None:
    write_store(bundle["runtime"], [make_row("runtime")])

    view = read_model.runs_view(
        bundle["runtime"], bundle["quality"], FLOOR, loaded_roster(bundle)
    )

    run = view["runtime_runs"]["runs"][0]
    assert run["models"][0]["display_id"] == "Qwen3.6-35B-A3B"
    assert "suites" not in run


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


def test_a_corrupt_fiche_file_is_the_same_named_absence_not_a_raise(
    bundle: dict[str, Path],
) -> None:
    # A stored file that cannot be parsed is the same fact to a reader as one
    # that is not there -- the pointer did not resolve -- and `read_fiche`
    # parses JSON without catching. One hand-edited file in the registry must
    # not take a whole view down, exactly as `resolve_suite_definition` and
    # `load_roster_file` already refuse to let their own files do.
    (bundle["fiches"] / f"{'c' * 64}.json").write_text("{not json", encoding="utf-8")

    view = build_runtime(bundle, [make_row("runtime", fiche_hash="c" * 64)])

    assert view["entries"][0]["fiche"] == Absent(
        ABSENT_POINTER_UNRESOLVED, {"pointer": "fiche_hash", "value": "c" * 64}
    )


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


def test_a_suite_pointer_carrying_traversal_is_the_same_unresolved_absence(
    bundle: dict[str, Path], tmp_path: Path
) -> None:
    # `snapshot_filename` is a raw f-string: a `suite_id`/`suite_version`
    # pair that composes to a path escaping `suite_definitions_dir` must
    # degrade exactly like a missing snapshot -- never read the escaped file,
    # even when a real, well-formed snapshot sits at that escaped location.
    filename = suite_snapshot.snapshot_filename("../secrets", "99")
    (tmp_path / filename).write_text(
        json.dumps({"prompt_set_hash": "escaped", "items": []}), encoding="utf-8"
    )

    view = build_quality(
        bundle, [make_row("quality", suite_id="../secrets", suite_version="99")]
    )

    assert view["entries"][0]["suite_definition"] == Absent(
        ABSENT_POINTER_UNRESOLVED,
        {"pointer": "suite_id/suite_version", "value": filename},
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
# The comparison view: one column per (suite_id, roster_entry_id), one row
# per item_id the union of every column's suite carries.
# --------------------------------------------------------------------------

SECOND_ROSTER_ENTRY_ID = "qwen3-4b-q4km"


def two_entry_roster_path(tmp_path: Path) -> Path:
    """A roster carrying the fixture's own MoE entry plus one dense entry."""
    path = tmp_path / "two-entry-roster.json"

    def server_flags() -> dict[str, Any]:
        return {
            "n_gpu_layers": 99,
            "context_size": 32768,
            "flash_attention": "on",
            "jinja": True,
            "parallel_slots": 1,
            "load_mode": "mmap",
            "sampler": {
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 0,
                "min_p": 0.0,
                "presence_penalty": 0.0,
            },
        }

    path.write_text(
        json.dumps(
            {
                "roster_version": 3,
                "entries": {
                    ROSTER_ENTRY_ID: {
                        "repo": "unsloth/Qwen3.6-35B-A3B-GGUF",
                        "revision": "main",
                        "file": "model.gguf",
                        "display_id": "Qwen3.6-35B-A3B",
                        "quant": "UD-IQ4_XS",
                        "sha256": "c" * 64,
                        "architecture": {
                            "kind": "moe",
                            "expert_count": 48,
                            "active_params_b": 3.0,
                        },
                        "server_flags": server_flags(),
                        "validated_host": {
                            "n_cpu_moe": 37,
                            "threads": 8,
                            "fiche_summary": "a laptop",
                        },
                    },
                    SECOND_ROSTER_ENTRY_ID: {
                        "repo": "unsloth/Qwen3-4B-GGUF",
                        "revision": "main",
                        "file": "model.gguf",
                        "display_id": "Qwen3-4B",
                        "quant": "Q4_K_M",
                        "sha256": "d" * 64,
                        "architecture": {
                            "kind": "dense",
                            "expert_count": None,
                            "active_params_b": 4.0,
                        },
                        "server_flags": server_flags(),
                        "validated_host": {
                            "n_cpu_moe": None,
                            "threads": 8,
                            "fiche_summary": "a laptop",
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def build_comparison(
    bundle: dict[str, Path], rows: list[dict[str, Any]], roster_path: Path
) -> Any:
    write_store(bundle["quality"], rows)
    return read_model.comparison_view(
        bundle["quality"],
        FLOOR,
        read_model.load_roster_file(roster_path),
        bundle["suites"],
        bundle["fiches"],
    )


def _column(view: dict[str, Any], roster_entry_id: str) -> dict[str, Any]:
    for suite in view["suites"]:
        for column in suite["columns"]:
            if column["roster_entry_id"] == roster_entry_id:
                return column
    raise AssertionError(f"no column for {roster_entry_id!r} in {view!r}")


def _cell(suite: dict[str, Any], item_id: str, column_index: int) -> dict[str, Any]:
    for item in suite["items"]:
        if item["item_id"] == item_id:
            return item["cells"][column_index]
    raise AssertionError(f"no item {item_id!r} in {suite!r}")


def test_a_comparisons_columns_each_name_their_own_suite_version(
    bundle: dict[str, Path], tmp_path: Path
) -> None:
    roster_path = two_entry_roster_path(tmp_path)
    older = make_row(
        "quality",
        roster_entry_id=ROSTER_ENTRY_ID,
        suite_version="1",
        item_id="item-01",
        run_id="run-moe",
    )
    newer_shared = make_row(
        "quality",
        roster_entry_id=SECOND_ROSTER_ENTRY_ID,
        suite_version="2",
        item_id="item-01",
        run_id="run-dense",
    )
    newer_only = make_row(
        "quality",
        roster_entry_id=SECOND_ROSTER_ENTRY_ID,
        suite_version="2",
        item_id="item-02",
        run_id="run-dense",
    )

    view = build_comparison(bundle, [older, newer_shared, newer_only], roster_path)

    assert len(view["suites"]) == 1
    suite = view["suites"][0]
    assert suite["suite_id"] == SUITE_ID
    assert len(suite["columns"]) == 2
    older_column = _column(view, ROSTER_ENTRY_ID)
    newer_column = _column(view, SECOND_ROSTER_ENTRY_ID)
    assert older_column["suite_version"] == "1"
    assert newer_column["suite_version"] == "2"

    older_index = suite["columns"].index(older_column)
    newer_index = suite["columns"].index(newer_column)
    assert _cell(suite, "item-02", older_index)["status"] == "not_compared"
    assert _cell(suite, "item-02", older_index) == {
        "status": "not_compared",
        "item_id": "item-02",
    }
    assert _cell(suite, "item-02", newer_index)["status"] == "compared"
    assert _cell(suite, "item-01", older_index)["status"] == "compared"
    assert _cell(suite, "item-01", newer_index)["status"] == "compared"


def test_a_comparison_column_with_an_unresolved_roster_entry_id_still_appears(
    bundle: dict[str, Path], tmp_path: Path
) -> None:
    view = build_comparison(
        bundle,
        [make_row("quality", roster_entry_id="not-in-roster")],
        two_entry_roster_path(tmp_path),
    )

    column = _column(view, "not-in-roster")
    assert column["roster_entry"] == Absent(
        ABSENT_POINTER_UNRESOLVED,
        {"pointer": "roster_entry_id", "value": "not-in-roster"},
    )
    assert column["dimensions"]["architecture"] == column["roster_entry"]


def test_a_comparison_column_is_backed_by_only_the_later_run(
    bundle: dict[str, Path], tmp_path: Path
) -> None:
    older_run = make_row(
        "quality",
        roster_entry_id=ROSTER_ENTRY_ID,
        item_id="item-01",
        run_id="run-older",
        captured_at="2026-01-01T00:00:00+00:00",
        correct=False,
    )
    newer_run = make_row(
        "quality",
        roster_entry_id=ROSTER_ENTRY_ID,
        item_id="item-01",
        run_id="run-newer",
        captured_at="2026-02-01T00:00:00+00:00",
        correct=True,
    )

    view = build_comparison(
        bundle, [older_run, newer_run], two_entry_roster_path(tmp_path)
    )

    suite = view["suites"][0]
    assert len(suite["columns"]) == 1
    column = suite["columns"][0]
    assert column["run_id"] == "run-newer"
    cell = _cell(suite, "item-01", 0)
    assert cell["run_id"] == "run-newer"
    assert cell["correct"] is True


COMPARISON_ENTRY_FIELDS: frozenset[str] = (
    read_model.RUNS_VIEW_FIELDS
    | read_model.QUALITY_VIEW_FIELDS
    | read_model.QUALITY_EXACT_MATCH_FIELDS
    | read_model.QUALITY_GRADED_FIELDS
    | read_model.QUALITY_JUDGE_FIELDS
    | frozenset(
        {
            "score_shape",
            "roster_entry",
            "fiche",
            "suite_definition",
            "score_breakdown",
            "language_breakdown",
            "status",
        }
    )
)


# The fields RUNTIME_VIEW_FIELDS owns that QUALITY_VIEW_FIELDS does not: the
# runtime-exclusive measurements (ttft_ms, wall_clock_s, gen_tok_per_s, ...).
# Identity/pricing fields (cost_total, roster_version, ...) legitimately
# carry the same name on both row kinds and are not what "quality-only" means
# here -- see RUNTIME_VIEW_FIELDS' own set for the full shared block.
RUNTIME_EXCLUSIVE_FIELDS: frozenset[str] = (
    read_model.RUNTIME_VIEW_FIELDS
    - read_model.QUALITY_VIEW_FIELDS
    - read_model.RUNS_VIEW_FIELDS
)


def test_no_runtime_or_energy_field_is_reachable_on_a_comparison_entry() -> None:
    assert COMPARISON_ENTRY_FIELDS & RUNTIME_EXCLUSIVE_FIELDS == frozenset()
    assert COMPARISON_ENTRY_FIELDS & read_model.ENERGY_VIEW_FIELDS == frozenset()


# --------------------------------------------------------------------------
# The committed reference bundle: every field the story names, over real rows
# at schema "7" -- see plan.md's Decisions for which fields this bundle's own
# floor already carries and which one it predates.
# --------------------------------------------------------------------------


def test_the_reference_bundle_quality_row_carries_the_storys_named_fields() -> None:
    entry = reference_bundle_quality_view()["entries"][0]

    for field in ("contamination_risk", "indicative_reasons", "failure_counts"):
        assert not isinstance(entry[field], Absent), f"{field} is unexpectedly absent"

    assert entry["thinking_policy"] == Absent(
        ABSENT_PREDATES_SCHEMA, {"row_schema_version": "7"}
    )


def test_the_reference_bundle_suite_definition_carries_the_suites_own_caps() -> None:
    entry = reference_bundle_quality_view()["entries"][0]

    suite_definition = entry["suite_definition"]
    assert not isinstance(suite_definition, Absent)
    for field in ("max_output_tokens", "stop_sequences", "context_length"):
        assert field in suite_definition


def test_the_reference_bundle_runtime_row_carries_the_storys_named_fields() -> None:
    entry = reference_bundle_runtime_view()["entries"][0]

    for field in (
        "ttft_source",
        "ttft_ms_spread",
        "prompt_tok_per_s_spread",
        "gen_tok_per_s_spread",
        "unreliable",
    ):
        assert not isinstance(entry[field], Absent), f"{field} is unexpectedly absent"


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
