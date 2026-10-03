"""Shared store fixtures: a self-contained bundle on disk, and the rows in it.

Rows are built from `row_contract.REQUIRED_FIELDS` itself rather than
hand-listed, so a fixture cannot silently drift from the shape a real row is
validated against. Lives beside the tests rather than inside one of them
because `test_read_model` and `test_service` need the same bundle -- the
service's job is to answer the read model's views over exactly it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import (
    machines,
    preflight,
    row_contract,
    score_interval,
    suite_snapshot,
)

# The declared minimums a constructed roster entry carries (`roster.load_roster`
# requires them): tiny enough that the pre-flight passes on any machine. Every
# one is declared, so a run prints no "not checked" line; the laptop's VRAM is
# read from its declared allocatable value, so no test needs a GPU.
ROSTER_REQUIREMENTS: dict[str, Any] = {
    "gpu": {
        "ram_gb": {"value": 0.001, "source": "declared", "read_from": "test"},
        "vram_gb": {"value": 0.001, "source": "declared", "read_from": "test"},
        "disk_gb": {"value": 0.001, "source": "declared", "read_from": "test"},
    },
    "cpu_only": {
        "ram_gb": {"value": 0.001, "source": "declared", "read_from": "test"},
        "disk_gb": {"value": 0.001, "source": "declared", "read_from": "test"},
    },
}


def write_raised_roster(roster_file: dict[str, Any], tmp_path: Path) -> Path:
    """`roster_file` with every entry's RAM minimum raised above any machine.

    A writer run under it must refuse at the pre-flight, before the weights
    are looked for or any process starts.
    """
    raised = json.loads(json.dumps(roster_file))
    for entry in raised["entries"].values():
        requirements = json.loads(json.dumps(ROSTER_REQUIREMENTS))
        for mode in requirements.values():
            mode["ram_gb"]["value"] = 10**6
        entry["requirements"] = requirements
    path = tmp_path / "raised-roster.json"
    path.write_text(json.dumps(raised), encoding="utf-8")
    return path


def single_refusal(machine_results_root: Path, machine_id: str) -> dict[str, Any]:
    """The one refusal record a refused run wrote for `machine_id`."""
    path = preflight.refusal_path(machine_results_root, machine_id)
    lines = path.read_text("utf-8").splitlines()
    assert len(lines) == 1, lines
    record: dict[str, Any] = json.loads(lines[0])
    assert record.keys() == row_contract.REFUSAL_FIELDS
    return record


FLOOR = "7"
RUN_ID = "run-under-test"
ROSTER_ENTRY_ID = "qwen3.6-35b-a3b-ud-iq4xs"
FICHE_HASH = "b" * 64
SUITE_ID = "classification-support-routing"
SUITE_VERSION = "1"

# Values that make a fixture row readable as a row rather than as a blob of
# placeholders. Everything else in the contract's required set gets a marker
# string naming the field, so a test that finds one knows where it came from.
NAMED_VALUES: dict[str, Any] = {
    "schema_version": "12",
    "run_id": RUN_ID,
    "captured_at": "2026-09-01T00:00:00+00:00",
    "roster_entry_id": ROSTER_ENTRY_ID,
    "fiche_hash": FICHE_HASH,
    "machine_id": "laptop-mobile-gpu",
    "compute_mode": "gpu",
    "suite_id": SUITE_ID,
    "suite_version": SUITE_VERSION,
    "prompt_variant_id": "baseline",
    "prompt_variant_version": "1",
    "suite_level": "development",
    "cpu_energy_kwh": 0.0003,
    "cpu_energy_method": "estimated_tdp",
    "gpu_energy_kwh": 0.0009,
    "gpu_energy_method": "nvml_sampled",
    "ram_energy_kwh": 0.00012,
    "ram_energy_method": "estimated_constant",
    "energy_kwh": 0.00132,
    "emissions_kg": 0.000074,
    "active_window_s": 12.5,
    "idle_window_s": 40.0,
    "energy_window_method": "per_repetition_tasks",
    "correct": True,
    "suite_accuracy": 1.0,
    "language_breakdown": {
        "en": {"accuracy": 1.0, "n": 1, "indicative": True},
        "fr": {"accuracy": 0.0, "n": 0, "indicative": True},
        "de": {"accuracy": 0.0, "n": 0, "indicative": True},
    },
    "verdict": {
        "verdict": "not_comparable",
        "reference_run_id": None,
        "differing_fields": [],
    },
    "retry_budget": {},
    "partial_failure": None,
    "item_tokens_in": 57,
    "item_tokens_in_null_reason": None,
    "item_tokens_out": 2,
    "item_tokens_out_null_reason": None,
    "item_ttft_ms": 13.7,
    "item_ttft_ms_null_reason": None,
    "item_ttft_source": "server_reported",
    "item_prompt_tokens_cached": 0,
    "item_prompt_tokens_cached_null_reason": None,
    "item_measurement_kind": "single_generation",
    "item_first_in_batch": True,
    # The fixture's provider is a placeholder, not `local`, so the row is read
    # as a cloud subject's: a family and no size class.
    "family": "qwen",
    "size_class": None,
    # The reference harness, measured: the engine received the item's own
    # prompt and nothing around it.
    "harness_id": "direct",
    "harness_version": "2.32.5",
    "harness_prompt_overhead": {"tokens": 0, "null_reason": None},
    # The batch's interval over its one item: constant, so zero_width; the
    # two empty language cells name no_items.
    "score_interval": score_interval.interval_block(
        [{"item_id": "billing-01", "language": "en"}], [1.0]
    ),
}

GRADED_VALUES: dict[str, Any] = {
    "metric_id": "chrf",
    "metric_version": "1",
    "metric_params": {"char_order": 6},
    "item_score": 0.62,
    "suite_score": 0.58,
    "score_breakdown": {
        "en": {"score": 0.62, "n": 1, "indicative": True},
        "fr": {"score": 0.0, "n": 0, "indicative": True},
        "de": {"score": 0.0, "n": 0, "indicative": True},
    },
    "reference_output": "une reference",
}


def make_row(kind: row_contract.RowKind, **overrides: Any) -> dict[str, Any]:
    """A complete row of `kind`, built from the contract's own required set."""
    row = {
        field: NAMED_VALUES.get(field, f"value-of-{field}")
        for field in sorted(row_contract.REQUIRED_FIELDS[kind])
    }
    row.update(overrides)
    return row


def write_store(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("".join(f"{json.dumps(row)}\n" for row in rows), encoding="utf-8")
    return path


def build_bundle(tmp_path: Path) -> dict[str, Path]:
    """A self-contained store + fiche registry + roster + suite dir on disk."""
    fiches = tmp_path / "fiches"
    fiches.mkdir()
    (fiches / f"{FICHE_HASH}.json").write_text(
        json.dumps({"cpu": "a cpu", "gpu": "a gpu"}), encoding="utf-8"
    )

    roster_path = tmp_path / "models.json"
    roster_path.write_text(
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
                        "requirements": ROSTER_REQUIREMENTS,
                        "architecture": {
                            "kind": "moe",
                            "expert_count": 48,
                            "active_params_b": 3.0,
                        },
                        "server_flags": {
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
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    suites = tmp_path / "suite-definitions"
    suites.mkdir()
    (suites / suite_snapshot.snapshot_filename(SUITE_ID, SUITE_VERSION)).write_text(
        json.dumps(
            {
                "suite_id": SUITE_ID,
                "suite_version": SUITE_VERSION,
                "prompt_set_hash": "deadbeef",
                "max_output_tokens": 32,
                "stop_sequences": [],
                "thinking_policy": "disabled",
                "context_length": 32768,
                "items": [{"item_id": "billing-01"}],
            }
        ),
        encoding="utf-8",
    )

    # The tracked machine registry, copied so a test can edit its own bundle's.
    machines_path = tmp_path / "machines.json"
    machines_path.write_text(
        Path(machines.DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return {
        "runtime": tmp_path / "runtime.jsonl",
        "quality": tmp_path / "quality.jsonl",
        "fiches": fiches,
        "roster": roster_path,
        "machines": machines_path,
        "suites": suites,
        "leader_sets": tmp_path / "leader-sets",
    }
