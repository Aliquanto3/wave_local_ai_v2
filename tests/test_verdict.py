from wave_local_ai_v2.fiche_registry import write_fiche
from wave_local_ai_v2.verdict import (
    VERDICT_NOT_COMPARABLE,
    VERDICT_NOT_REPRODUCED,
    VERDICT_REPRODUCED,
    quality_verdict,
    runtime_verdict,
)

BASE_FICHE = {
    "cpu": "x",
    "ram_gb": 32.0,
    "gpu_name": "RTX 4090",
    "gpu_driver_version": "1.2.3",
    "os": "z",
    "cuda_ceiling": "12.4",
    "llama_cpp_build": "b10537",
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

    result = quality_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_REPRODUCED


def test_quality_one_differing_label_is_not_reproduced_and_names_the_item(
    tmp_path,
) -> None:
    reference = [_quality_row()]
    candidate = [_quality_row(run_id="run-candidate", predicted_label="refund")]

    result = quality_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_REPRODUCED
    assert "billing-01" in result["differing_fields"]


def test_quality_no_matching_reference_is_not_comparable() -> None:
    reference = [_quality_row(model_id="Other Model")]
    candidate = [_quality_row(run_id="run-candidate")]

    result = quality_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE


def test_quality_batches_covering_no_common_item_are_not_comparable() -> None:
    reference = [_quality_row(item_id="billing-01")]
    candidate = [_quality_row(run_id="run-candidate", item_id="refund-09")]

    result = quality_verdict(candidate, reference)

    # Zero compared items must never read as agreement.
    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["billing-01", "refund-09"]


def test_quality_a_reference_missing_one_item_is_not_comparable() -> None:
    reference = [_quality_row(item_id="billing-01")]
    candidate = [
        _quality_row(run_id="run-candidate", item_id="billing-01"),
        _quality_row(run_id="run-candidate", item_id="refund-09"),
    ]

    result = quality_verdict(candidate, reference)

    assert result["verdict"] == VERDICT_NOT_COMPARABLE
    assert result["differing_fields"] == ["refund-09"]
