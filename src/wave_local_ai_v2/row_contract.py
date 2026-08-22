"""The row contract: one required-field list per row kind, extended by every
later story rather than duplicated.

`append_row` (`results.py`) gates on `validate_row` before writing a line, so
an incomplete row can never land on disk. A key present with value `None` is
not missing -- several fields degrade to an explicit `None` on capture failure
(`hardware.py`, `timings.py`, `gpu.py`, `energy.py`) and are still complete.
"""

from __future__ import annotations

from typing import Any, Literal

from wave_local_ai_v2 import aggregation, prompt_provenance

# "2": the runtime row's shape changed incompatibly (a scalar `gen_tok_per_s`
# became a median over a repetition set). Quality rows move to "2" with it
# because the constant is shared -- splitting into per-kind versions is out
# of scope for this increment.
SCHEMA_VERSION = "2"

RowKind = Literal["runtime", "quality"]

REQUIRED_FIELDS: dict[RowKind, frozenset[str]] = {
    "runtime": frozenset(
        {
            "schema_version",
            "run_id",
            "captured_at",
            # provenance.capture_provenance
            "release_version",
            "commit_sha",
            "tree_dirty",
            # prompt_provenance: call-path identity
            "endpoint",
            "prompt_template_id",
            "prompt_template_hash",
            "prompt_capture",
            # hardware.HardwareFiche
            "cpu",
            "ram_gb",
            "gpu_name",
            "gpu_driver_version",
            "os",
            "cuda_ceiling",
            "llama_cpp_build",
            "model_file",
            "quant",
            "flags",
            "prompt",
            "max_tokens",
            "wall_clock_s",
            # timings.Timings
            "ttft_ms",
            "prompt_tok_per_s",
            "gen_tok_per_s",
            # gpu.GpuStats
            "vram_used_mib",
            "gpu_draw_w",
            "process_rss_bytes",
            # energy.EnergyResult
            "energy_kwh",
            "energy_method",
            # repetitions.run_repetition_set / __init__._run
            "sampling",
            "seed_pinned",
            "warmup_count",
            "warmup_repetitions",
            "restart_between_repetitions",
            "cooldown_s",
            "repetitions_n",
            "slot_reset_method",
            "repetitions",
            # aggregation.aggregate_timings / aggregation.AGGREGATION_LABELS
            "aggregation",
            "ttft_ms_mean",
            "ttft_ms_sd",
            "prompt_tok_per_s_mean",
            "prompt_tok_per_s_sd",
            "gen_tok_per_s_mean",
            "gen_tok_per_s_sd",
        }
    ),
    "quality": frozenset(
        {
            "schema_version",
            "run_id",
            "captured_at",
            # provenance.capture_provenance
            "release_version",
            "commit_sha",
            "tree_dirty",
            # prompt_provenance: call-path identity
            "endpoint",
            "prompt_template_id",
            "prompt_template_hash",
            "prompt_capture",
            "model_id",
            "provider",
            "task_suite",
            "item_id",
            "prompt",
            "expected_label",
            "predicted_label",
            "correct",
            "suite_accuracy",
            "sampling",
            "max_output_tokens",
            "stop_sequences",
            "context_length",
            "suite_id",
            "suite_version",
            "prompt_set_hash",
            "language",
            "provenance",
            "contamination_risk",
            "indicative",
            "indicative_reasons",
            # scoring.score_item / score_suite
            "failure_reason",
            "failure_counts",
        }
    ),
}


class RowContractError(ValueError):
    """Raised when a row is missing one or more of its kind's required fields."""


def validate_row(kind: RowKind, row: dict[str, Any]) -> None:
    """Raise `RowContractError` naming every field `kind` requires but `row` lacks.

    A key present with value `None` satisfies the contract; only an absent key
    counts as missing.
    """
    missing = REQUIRED_FIELDS[kind] - row.keys()
    if missing:
        raise RowContractError(
            f"row of kind {kind!r} is missing required field(s): "
            f"{', '.join(sorted(missing))}"
        )

    endpoint = row["endpoint"]
    prompt_template_id = row["prompt_template_id"]
    if not prompt_provenance.is_consistent(endpoint, prompt_template_id):
        raise RowContractError(
            f"row of kind {kind!r} pairs endpoint {endpoint!r} with "
            f"prompt_template_id {prompt_template_id!r}: an endpoint that "
            f"applies a template cannot declare 'none'"
        )

    if kind == "runtime":
        _validate_runtime_repetition_structure(row)


def _validate_runtime_repetition_structure(row: dict[str, Any]) -> None:
    """Raise on a repetition set that cannot back the aggregates it publishes."""
    repetitions_n = row["repetitions_n"]
    if repetitions_n < 2:
        raise RowContractError(
            f"row of kind 'runtime' has repetitions_n={repetitions_n!r}: "
            "the sample sd is undefined below N=2"
        )

    repetitions = row["repetitions"]
    if len(repetitions) != repetitions_n:
        raise RowContractError(
            f"row of kind 'runtime' has {len(repetitions)} repetitions but "
            f"repetitions_n={repetitions_n!r}"
        )
    indices = [rep["index"] for rep in repetitions]
    if indices != list(range(1, repetitions_n + 1)):
        raise RowContractError(
            f"row of kind 'runtime' has non-contiguous repetition indices: "
            f"{indices!r}, expected 1..{repetitions_n}"
        )

    # This catches the declaration drifting from the declared field set. That
    # every name in MEASUREMENT_FIELDS is also a REQUIRED_FIELDS entry -- so a
    # row reaching here already carries all of them, checked above -- is a
    # static invariant between two hand-maintained sets, guarded by
    # tests/test_row_contract.py's
    # test_every_declared_measurement_is_a_required_runtime_field rather than
    # re-derived per row.
    declared = set(row["aggregation"])
    if declared != aggregation.MEASUREMENT_FIELDS:
        raise RowContractError(
            "row of kind 'runtime' has an aggregation map that does not "
            f"match the declared measurement set: {declared!r} != "
            f"{set(aggregation.MEASUREMENT_FIELDS)!r}"
        )
