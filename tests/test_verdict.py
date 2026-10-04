import json
from pathlib import Path

import pytest

from wave_local_ai_v2 import suite_registry
from wave_local_ai_v2.fiche_registry import write_fiche
from wave_local_ai_v2.verdict import (
    VERDICT_NOT_COMPARABLE,
    VERDICT_NOT_REPRODUCED,
    VERDICT_REPRODUCED,
    quality_verdict,
    runtime_verdict,
    select_quality_references,
)

BASE_FICHE = {
    "cpu": "x",
    "ram_gb": 32.0,
    "gpu_name": "RTX 4090",
    "gpu_driver_version": "1.2.3",
    "os": "z",
    "cuda_ceiling": "12.4",
    "engine_id": "llama.cpp",
    "engine_build": "b10537",
    "engine_config_hash": "e" * 64,
    "machine_id": "laptop-mobile-gpu",
    "compute_mode": "gpu",
    "roster_entry_id": "fake-entry",
    "model_sha256": "0" * 64,
    "quant": "UD-IQ4_XS",
    "flags": ["-ngl", "99"],
}


def _write_fiche(registry_dir, **overrides) -> str:
    return write_fiche({**BASE_FICHE, **overrides}, registry_dir)


def _runtime_row(fiche_hash: str, **overrides) -> dict:
    row = {
        "run_id": "run-ref",
        "roster_entry_id": "fake-entry",
        "fiche_hash": fiche_hash,
        "gen_tok_per_s": 26.0,
        "ttft_ms": 100.0,
        "prompt_tok_per_s": 280.0,
    }
    row.update(overrides)
    return row


def test_matching_reference_with_equal_medians_is_reproduced(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    reference = _runtime_row(fiche_hash)
    candidate = _runtime_row(fiche_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["reference_run_id"] == "run-ref"


def test_a_99_percent_delta_is_reproduced_a_101_percent_delta_is_not(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    reference = _runtime_row(fiche_hash, gen_tok_per_s=100.0)

    within = _runtime_row(fiche_hash, gen_tok_per_s=90.1)
    result_within = runtime_verdict(within, [reference], registry_dir, tolerance=0.10)
    assert result_within["verdict"] == VERDICT_REPRODUCED

    outside = _runtime_row(fiche_hash, gen_tok_per_s=89.9)
    result_outside = runtime_verdict(outside, [reference], registry_dir, tolerance=0.10)
    assert result_outside["verdict"] == VERDICT_NOT_REPRODUCED


def test_differing_gpu_name_alone_is_not_comparable_and_names_it(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    reference_hash = _write_fiche(registry_dir, gpu_name="RTX 4090")
    candidate_hash = _write_fiche(registry_dir, gpu_name="RTX 3090")
    reference = _runtime_row(reference_hash)
    candidate = _runtime_row(candidate_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert "gpu_name" in result["differing_fields"]


def test_differing_cpu_or_driver_alone_still_matches_and_reports(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    reference_hash = _write_fiche(registry_dir, cpu="cpu-a", gpu_driver_version="1.0")
    candidate_hash = _write_fiche(registry_dir, cpu="cpu-b", gpu_driver_version="2.0")
    reference = _runtime_row(reference_hash)
    candidate = _runtime_row(candidate_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["reference_run_id"] == "run-ref"


def test_empty_reference_list_is_not_comparable_never_not_reproduced(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    candidate = _runtime_row(fiche_hash)

    result = runtime_verdict(candidate, [], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE


def test_a_match_carries_the_reference_repetitions_and_not_the_candidates(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    reference = _runtime_row(fiche_hash, repetitions=[{"wall_clock_s": 1.0}])
    candidate = _runtime_row(
        fiche_hash, run_id="run-candidate", repetitions=[{"wall_clock_s": 2.0}]
    )

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    # The candidate's own repetitions are a sibling key of the row this block
    # is attached to, so duplicating them inside it would carry two copies.
    assert result["reference_repetitions"] == [{"wall_clock_s": 1.0}]
    assert "candidate_machine_state" not in result


def test_a_reference_row_for_another_roster_entry_is_not_comparable(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    reference = _runtime_row(fiche_hash, roster_entry_id="some-other-entry")
    candidate = _runtime_row(fiche_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert "roster_entry_id" in result["reason"]


def test_a_reference_row_with_no_fiche_hash_is_not_comparable(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    # The state of both committed reference files today: rows that predate
    # `fiche_hash` entirely.
    reference = _runtime_row(fiche_hash)
    del reference["fiche_hash"]
    candidate = _runtime_row(fiche_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["no reference row has a registered fiche"]


def test_a_candidate_whose_fiche_is_not_registered_is_not_comparable(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    reference = _runtime_row(fiche_hash)
    candidate = _runtime_row("deadbeef" * 8, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == [
        "fiche_hash: candidate row's fiche is not registered"
    ]


def test_a_matching_reference_with_no_usable_gen_tok_per_s_is_not_comparable(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    reference = _runtime_row(fiche_hash)
    del reference["gen_tok_per_s"]
    candidate = _runtime_row(fiche_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    # Never a crash between the measurement and the write: the run is kept.
    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert "gen_tok_per_s" in result["reason"]


def test_an_unusable_reported_metric_nulls_its_delta_without_blocking(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir)
    reference = _runtime_row(fiche_hash, ttft_ms=0.0)
    del reference["prompt_tok_per_s"]
    candidate = _runtime_row(fiche_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["ttft_ms_delta"] is None
    assert result["prompt_tok_per_s_delta"] is None


def test_a_blocking_field_null_on_both_sides_is_not_comparable(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(registry_dir, engine_build=None)
    reference = _runtime_row(fiche_hash)
    candidate = _runtime_row(fiche_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    # Two unknown builds are not evidence of the same build.
    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert "engine_build" in result["differing_fields"]


def test_an_engine_mismatch_is_not_comparable_naming_engine_id(tmp_path) -> None:
    """Two fiches identical except for `engine_id` hash differently, and the
    verdict between their rows names the engine instead of comparing medians."""
    registry_dir = tmp_path / "fiches"
    reference_hash = _write_fiche(registry_dir)
    candidate_hash = _write_fiche(registry_dir, engine_id="ollama")
    assert reference_hash != candidate_hash
    reference = _runtime_row(reference_hash)
    # A median 50% slower would be `not_reproduced` if the rows were compared.
    candidate = _runtime_row(candidate_hash, run_id="run-candidate", gen_tok_per_s=13.0)

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["engine_id"]


def test_a_legacy_reference_fiche_with_no_engine_field_is_not_comparable(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    legacy = {
        key: value
        for key, value in BASE_FICHE.items()
        if key
        not in (
            "engine_id",
            "engine_build",
            "engine_config_hash",
            "machine_id",
            "compute_mode",
        )
    }
    legacy["llama_cpp_build"] = "b10537"
    candidate_hash = _write_fiche(registry_dir)
    # Stored as the committed legacy fiches are: under projection "1", which
    # the verdict never re-hashes, so its name only has to resolve.
    legacy_hash = "1" * 64
    (registry_dir / f"{legacy_hash}.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )

    result = runtime_verdict(
        _runtime_row(candidate_hash, run_id="run-candidate"),
        [_runtime_row(legacy_hash)],
        registry_dir,
        tolerance=0.10,
    )

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["compute_mode", "engine_build", "engine_id"]


def test_a_blocking_field_null_on_the_reference_only_is_not_comparable(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    reference_hash = _write_fiche(registry_dir, gpu_name=None)
    candidate_hash = _write_fiche(registry_dir)
    reference = _runtime_row(reference_hash)
    candidate = _runtime_row(candidate_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["gpu_name"]


def test_a_blocking_field_null_on_the_candidate_only_is_not_comparable(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    reference_hash = _write_fiche(registry_dir)
    # `flags` stays out of the fiche hash, so a non-blocking field is varied
    # too: otherwise write-once storage hands back the reference's fiche.
    candidate_hash = _write_fiche(registry_dir, flags=None, cpu="cpu-b")
    reference = _runtime_row(reference_hash)
    candidate = _runtime_row(candidate_hash, run_id="run-candidate")

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["reference_run_id"] is None
    assert result["differing_fields"] == ["flags"]
    assert "null" in result["reason"]


def test_a_cpu_only_candidate_against_a_gpu_reference_is_not_comparable(
    tmp_path,
) -> None:
    """Epic success check 1 at the verdict: one machine, one model, two modes.

    The fiches hash apart and are both stored, so each row reads its own
    flags, and the verdict names `compute_mode` instead of comparing a CPU
    median against a GPU one."""
    registry_dir = tmp_path / "fiches"
    gpu_hash = _write_fiche(registry_dir)
    cpu_hash = _write_fiche(
        registry_dir,
        compute_mode="cpu_only",
        flags=["-ngl", "0", "--device", "none"],
    )
    assert gpu_hash != cpu_hash
    reference = _runtime_row(gpu_hash)
    candidate = _runtime_row(cpu_hash, run_id="run-candidate", gen_tok_per_s=26.0)

    result = runtime_verdict(candidate, [reference], registry_dir, tolerance=0.10)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert "compute_mode" in result["differing_fields"]


def test_a_mode_mismatch_alone_is_not_comparable_naming_compute_mode(
    tmp_path,
) -> None:
    """Even with an identical flag list, the mode alone blocks."""
    registry_dir = tmp_path / "fiches"
    gpu_hash = _write_fiche(registry_dir)
    cpu_hash = _write_fiche(registry_dir, compute_mode="cpu_only")

    result = runtime_verdict(
        _runtime_row(cpu_hash, run_id="run-candidate"),
        [_runtime_row(gpu_hash)],
        registry_dir,
        tolerance=0.10,
    )

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["compute_mode"]


def _no_gpu_fiche(registry_dir, **overrides) -> str:
    return _write_fiche(
        registry_dir,
        machine_id="pro-pc-no-gpu",
        compute_mode="cpu_only",
        gpu_name=None,
        gpu_driver_version=None,
        cuda_ceiling=None,
        flags=["-ngl", "0", "--device", "none"],
        **overrides,
    )


def test_two_cpu_only_runs_on_a_declared_gpu_less_machine_can_reproduce(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _no_gpu_fiche(registry_dir)

    result = runtime_verdict(
        _runtime_row(fiche_hash, run_id="run-candidate", gen_tok_per_s=25.0),
        [_runtime_row(fiche_hash)],
        registry_dir,
        tolerance=0.10,
    )

    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["differing_fields"] == []


def test_a_gpu_that_failed_capture_on_a_gpu_declaring_machine_never_matches(
    tmp_path,
) -> None:
    """The null-never-matches rule still holds where a GPU is declared: the
    laptop declares one, so its null `gpu_name` is a failed capture."""
    registry_dir = tmp_path / "fiches"
    fiche_hash = _write_fiche(
        registry_dir, compute_mode="cpu_only", gpu_name=None, flags=["-ngl", "0"]
    )

    result = runtime_verdict(
        _runtime_row(fiche_hash, run_id="run-candidate"),
        [_runtime_row(fiche_hash)],
        registry_dir,
        tolerance=0.10,
    )

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["gpu_name"]


def test_an_undeclared_machine_never_declares_its_gpu_absent(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = _no_gpu_fiche(registry_dir, cpu="other")
    # Re-stored under an id the registry does not declare.
    undeclared_hash = _write_fiche(
        registry_dir,
        machine_id="someone-elses-box",
        compute_mode="cpu_only",
        gpu_name=None,
        flags=["-ngl", "0", "--device", "none"],
    )
    assert fiche_hash != undeclared_hash

    result = runtime_verdict(
        _runtime_row(undeclared_hash, run_id="run-candidate"),
        [_runtime_row(undeclared_hash)],
        registry_dir,
        tolerance=0.10,
    )

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["gpu_name"]


_TOLERANCE = {
    "value": 0.1,
    "unit": "fraction_of_items",
    "suite_id": "fixture-suite",
    "suite_version": "1",
}


def _local_verdict(candidate: list[dict], reference: list[dict]) -> dict:
    return quality_verdict(candidate, reference, provider="local", tolerance=_TOLERANCE)


def _quality_row(model_id="Fake Model", suite_version="1", seed=1, **overrides) -> dict:
    row = {
        "run_id": "run-ref",
        "model_id": model_id,
        "suite_version": suite_version,
        "sampling": {"seed": seed},
        "item_id": "billing-01",
        "predicted_label": "billing",
    }
    row.update(overrides)
    return row


def test_quality_identical_labels_are_reproduced() -> None:
    reference = [_quality_row()]
    candidate = [_quality_row(run_id="run-candidate")]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_REPRODUCED


def test_quality_one_differing_label_is_not_reproduced_and_names_the_item(
    tmp_path,
) -> None:
    reference = [_quality_row()]
    candidate = [_quality_row(run_id="run-candidate", predicted_label="refund")]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_REPRODUCED
    assert "billing-01" in result["differing_fields"]


def test_quality_reference_selection_never_crosses_task_suites() -> None:
    # One store -- and so one reference file -- holds two suites, and the two
    # version themselves independently, so a shared suite_version is not
    # evidence that two rows describe the same batch. Without the task_suite
    # filter the classification rows below join the comparison, the item_ids
    # stop matching, and a batch that reproduced item for item reports
    # not_comparable.
    reference = [
        _quality_row(task_suite="classification", item_id="billing-01"),
        _quality_row(
            task_suite="translation",
            item_id="en-fr-01",
            predicted_label=None,
            item_score=0.8,
        ),
    ]
    candidate = [
        _quality_row(
            run_id="run-candidate",
            task_suite="translation",
            item_id="en-fr-01",
            predicted_label=None,
            item_score=0.8,
        )
    ]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["compared_field"] == "item_score"


def test_a_publication_batch_never_selects_the_hand_written_suites_reference() -> None:
    # Both classification suites share task_suite, and each versions itself
    # independently: at a shared suite_version the hand-written suite's rows
    # must not stand in as the reference of a MInDS-14 batch.
    reference = [
        _quality_row(
            task_suite="classification",
            suite_id="classification-support-routing",
            item_id="billing-01",
        )
    ]
    candidate = [
        _quality_row(
            run_id="run-candidate",
            task_suite="classification",
            suite_id="classification-banking-intents-minds14",
            item_id="PolyAI/minds14:en-US~ABROAD/a.wav",
            predicted_label="abroad",
        )
    ]

    assert select_quality_references(candidate, reference) == []
    result = _local_verdict(candidate, reference)
    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["reference_run_id"] is None


def test_a_row_without_a_suite_id_is_matched_on_task_suite_as_before() -> None:
    reference = [_quality_row(task_suite="classification")]
    with_id = [
        _quality_row(
            run_id="run-candidate",
            task_suite="classification",
            suite_id="classification-support-routing",
        )
    ]
    without_id = [_quality_row(run_id="run-candidate", task_suite="classification")]

    assert select_quality_references(with_id, reference) == reference
    assert select_quality_references(without_id, reference) == reference
    assert _local_verdict(with_id, reference)["verdict"] == VERDICT_REPRODUCED


def _two_run_reference(first_label: str, second_label: str) -> list[dict]:
    # The two-quality-runs protocol: every regenerated bundle carries two
    # runs of one batch, so the verdict must say which one it compared.
    return [
        _quality_row(run_id="run-ref-a", item_id="billing-01"),
        _quality_row(
            run_id="run-ref-a", item_id="refund-09", predicted_label=first_label
        ),
        _quality_row(run_id="run-ref-b", item_id="billing-01"),
        _quality_row(
            run_id="run-ref-b", item_id="refund-09", predicted_label=second_label
        ),
    ]


def _two_item_candidate() -> list[dict]:
    return [
        _quality_row(run_id="run-candidate", item_id="billing-01"),
        _quality_row(
            run_id="run-candidate", item_id="refund-09", predicted_label="refund"
        ),
    ]


def test_quality_two_reference_runs_compare_against_the_named_run() -> None:
    reference = _two_run_reference(first_label="refund", second_label="billing")

    result = _local_verdict(_two_item_candidate(), reference)

    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["reference_run_id"] == "run-ref-a"


def test_quality_a_disagreement_in_the_named_run_alone_is_not_reproduced() -> None:
    reference = _two_run_reference(first_label="billing", second_label="refund")

    result = _local_verdict(_two_item_candidate(), reference)

    assert result["verdict"] == VERDICT_NOT_REPRODUCED
    assert result["reference_run_id"] == "run-ref-a"
    assert result["differing_fields"] == ["refund-09"]


def test_quality_no_matching_reference_is_not_comparable() -> None:
    reference = [_quality_row(model_id="Other Model")]
    candidate = [_quality_row(run_id="run-candidate")]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE


def test_quality_batches_covering_no_common_item_are_not_comparable() -> None:
    reference = [_quality_row(item_id="billing-01")]
    candidate = [_quality_row(run_id="run-candidate", item_id="refund-09")]

    result = _local_verdict(candidate, reference)

    # Zero compared items must never read as agreement.
    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["billing-01", "refund-09"]


def test_quality_a_reference_missing_one_item_is_not_comparable() -> None:
    reference = [_quality_row(item_id="billing-01")]
    candidate = [
        _quality_row(run_id="run-candidate", item_id="billing-01"),
        _quality_row(run_id="run-candidate", item_id="refund-09"),
    ]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["refund-09"]


def test_quality_a_label_decided_verdict_names_the_field_it_decided_on() -> None:
    result = _local_verdict([_quality_row(run_id="run-candidate")], [_quality_row()])

    assert result["compared_field"] == "predicted_label"


def _graded_row(item_id="en-fr-01", item_score=0.83, **overrides) -> dict:
    """A translation row: no label on either side, a chrF score instead."""
    row = {
        "run_id": "run-ref",
        "model_id": "Fake Model",
        "suite_version": "1",
        "sampling": {"seed": 1},
        "item_id": item_id,
        "predicted_label": None,
        "item_score": item_score,
    }
    row.update(overrides)
    return row


def test_quality_identical_item_scores_are_reproduced_on_the_score() -> None:
    reference = [_graded_row()]
    candidate = [_graded_row(run_id="run-candidate")]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_REPRODUCED
    # Named, so a reader can tell a score reproduction from a label one
    # without going back to the rows.
    assert result["compared_field"] == "item_score"


def test_quality_one_differing_item_score_is_not_reproduced_and_names_the_item() -> (
    None
):
    reference = [_graded_row(item_id="fr-de-03", item_score=0.71)]
    candidate = [
        _graded_row(run_id="run-candidate", item_id="fr-de-03", item_score=0.68)
    ]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_REPRODUCED
    assert result["differing_fields"] == ["fr-de-03"]
    assert result["compared_field"] == "item_score"


def test_quality_two_batches_with_nothing_comparable_are_not_comparable() -> None:
    # Every predicted_label and every item_score null on both sides: two runs
    # of a suite that publishes neither. Comparing two sets of nulls would
    # report `reproduced` off no evidence at all.
    reference = [_quality_row(predicted_label=None, item_score=None)]
    candidate = [
        _quality_row(run_id="run-candidate", predicted_label=None, item_score=None)
    ]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["compared_field"] is None
    assert "no comparable per-item value" in result["reason"]


def test_quality_a_row_carrying_no_score_key_at_all_is_not_comparable() -> None:
    # An older row predating the graded block carries no `item_score` key.
    reference = [_quality_row(predicted_label=None)]
    candidate = [_quality_row(run_id="run-candidate", predicted_label=None)]

    result = _local_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE


def test_quality_a_label_on_one_side_alone_still_decides_on_the_label() -> None:
    # The candidate answered nothing on this item and the reference answered
    # "billing": that is a real difference, not an absence of evidence.
    reference = [_quality_row()]
    candidate = [_quality_row(run_id="run-candidate", predicted_label=None)]

    result = _local_verdict(candidate, reference)

    assert result["compared_field"] == "predicted_label"
    assert result["verdict"] == VERDICT_NOT_REPRODUCED


def test_quality_a_label_anywhere_in_the_batch_outranks_a_score() -> None:
    # A batch carrying both is an exact-match batch that also happens to
    # publish a score: the label is the value the suite is scored on.
    reference = [_quality_row(item_score=0.4)]
    candidate = [_quality_row(run_id="run-candidate", item_score=0.9)]

    result = _local_verdict(candidate, reference)

    assert result["compared_field"] == "predicted_label"
    assert result["verdict"] == VERDICT_REPRODUCED


def test_a_suite_version_bump_supersedes_rather_than_reproduces() -> None:
    """Supersession is structural here, not editorial.

    The chat-template increment bumped both suites precisely so its rows
    cannot be compared against the untemplated ones: a batch that scored the
    same items with the subject sent a different string is not a reproduction
    of the old batch, and nothing in the store had to be edited to say so.
    """
    untemplated = [_quality_row(suite_version="2")]
    templated = [_quality_row(suite_version="3", run_id="run-candidate")]

    result = _local_verdict(templated, untemplated)

    assert result["verdict"] == "not_comparable"
    assert "suite_version" in result["reason"]
    assert result["reference_run_id"] is None


# --- the subject rule: local identical, cloud within the declared tolerance --


def _batch(
    run_id: str, labels: list[str | None], provider: str = "mistral"
) -> list[dict]:
    return [
        _quality_row(
            run_id=run_id,
            item_id=f"item-{index:02d}",
            predicted_label=label,
            provider=provider,
        )
        for index, label in enumerate(labels)
    ]


def _cloud_pair(diverging: int, total: int = 20) -> tuple[list[dict], list[dict]]:
    reference = _batch("run-ref", ["billing"] * total)
    candidate = _batch(
        "run-candidate", ["technical"] * diverging + ["billing"] * (total - diverging)
    )
    return candidate, reference


def _cloud_verdict(candidate, reference, **kwargs) -> dict:
    return quality_verdict(
        candidate, reference, provider="mistral", tolerance=_TOLERANCE, **kwargs
    )


def test_a_cloud_batch_diverging_within_its_tolerance_is_reproduced_naming_them() -> (
    None
):
    candidate, reference = _cloud_pair(diverging=2)

    result = _cloud_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["differing_fields"] == ["item-00", "item-01"]
    assert result["divergence"] == 0.1
    assert result["subject_rule"] == "within_tolerance"
    assert result["tolerance"] == _TOLERANCE
    assert result["single_run_indicative"] is None


def test_a_cloud_batch_diverging_beyond_its_tolerance_is_not_reproduced() -> None:
    candidate, reference = _cloud_pair(diverging=3)

    result = _cloud_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_REPRODUCED
    assert result["differing_fields"] == ["item-00", "item-01", "item-02"]
    assert result["divergence"] == 0.15
    assert result["tolerance"]["suite_version"] == "1"


@pytest.mark.parametrize("blocker", ["model_not_served", "no_seed"])
def test_a_cloud_batch_that_cannot_be_rerun_is_single_run_indicative(blocker) -> None:
    candidate, reference = _cloud_pair(diverging=20)

    result = _cloud_verdict(candidate, reference, rerun_blocker=blocker)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["verdict"] != VERDICT_NOT_REPRODUCED
    assert result["single_run_indicative"] == blocker
    assert blocker in result["reason"]
    assert result["reference_run_id"] == "run-ref"


def test_a_local_batch_with_one_diverging_item_is_still_not_reproduced() -> None:
    reference = _batch("run-ref", ["billing"] * 20, provider="local")
    candidate = _batch(
        "run-candidate", ["technical"] + ["billing"] * 19, provider="local"
    )

    result = quality_verdict(
        candidate, reference, provider="local", tolerance=_TOLERANCE
    )

    assert result["verdict"] == VERDICT_NOT_REPRODUCED
    assert result["differing_fields"] == ["item-00"]
    assert result["subject_rule"] == "identical"
    assert result["tolerance"] is None


def test_a_local_batch_is_never_marked_single_run_indicative() -> None:
    with pytest.raises(ValueError, match="only a cloud subject"):
        quality_verdict(
            [], [], provider="local", tolerance=_TOLERANCE, rerun_blocker="no_seed"
        )


def test_an_unknown_rerun_blocker_is_refused() -> None:
    with pytest.raises(ValueError, match="model_not_served, no_seed"):
        _cloud_verdict([], [], rerun_blocker="rate_limited")


def test_an_all_null_cloud_batch_is_not_comparable() -> None:
    reference = _batch("run-ref", [None] * 20)
    candidate = _batch("run-candidate", [None] * 20)

    result = _cloud_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["compared_field"] is None
    assert result["tolerance"] == _TOLERANCE


def test_a_cloud_item_null_on_one_side_counts_as_diverging() -> None:
    reference = _batch("run-ref", ["billing"] * 20)
    candidate = _batch("run-candidate", [None] * 3 + ["billing"] * 17)
    # Null on both sides is not agreement on a cloud batch either.
    reference[3]["predicted_label"] = candidate[3]["predicted_label"] = None

    result = _cloud_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_REPRODUCED
    assert result["differing_fields"] == ["item-00", "item-01", "item-02", "item-03"]


@pytest.mark.parametrize(
    ("candidate", "reference", "reason"),
    [
        ([], [], "no reference row"),
        (_cloud_pair(0)[0][:19], _cloud_pair(0)[1], "on one side only"),
    ],
)
def test_a_cloud_batch_keeps_the_existing_not_comparable_triggers(
    candidate, reference, reason
) -> None:
    result = _cloud_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert reason in result["reason"]
    assert result["subject_rule"] == "within_tolerance"


def test_the_committed_mistral_rerun_is_reproduced_under_the_declared_tolerance() -> (
    None
):
    """The one observed cloud re-run: the two committed mistral-small-2603
    batches, which the identical rule published as not_reproduced on one
    item, read back under the classification suite's declared tolerance.
    Superseded with the schema-7 bundle on 2026-10-04 and kept unedited."""
    rows = [
        json.loads(line)
        for line in Path("aidd_docs/results/quality-reference.schema-7.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    mistral = [row for row in rows if row["provider"] == "mistral"]
    reference = [row for row in mistral if row["run_id"].startswith("5e13166d")]
    candidate = [row for row in mistral if row["run_id"].startswith("d20afbda")]
    suite = suite_registry.resolve("classification-support-routing")
    tolerance = {
        "value": suite.divergence_tolerance["value"],
        "unit": suite.divergence_tolerance["unit"],
        "suite_id": suite.suite_id,
        "suite_version": suite.suite_version,
    }

    result = quality_verdict(
        candidate, reference, provider="mistral", tolerance=tolerance
    )

    assert candidate[0]["verdict"]["verdict"] == VERDICT_NOT_REPRODUCED
    assert result["verdict"] == VERDICT_REPRODUCED
    assert result["differing_fields"] == ["other-de-01"]
    assert result["divergence"] == 0.05
