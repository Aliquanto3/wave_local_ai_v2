"""The row contract: one required-field list per row kind, extended by every
later story rather than duplicated.

`append_row` (`results.py`) gates on `validate_row` before writing a line, so
an incomplete row can never land on disk. A key present with value `None` is
not missing -- several fields degrade to an explicit `None` on capture failure
(`hardware.py`, `timings.py`, `gpu.py`, `energy.py`) and are still complete.
"""

from __future__ import annotations

from typing import Any, Literal

from wave_local_ai_v2 import prompt_provenance

SCHEMA_VERSION = "1"

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
