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

from wave_local_ai_v2 import row_contract, suite_snapshot

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
    "schema_version": "11",
    "run_id": RUN_ID,
    "captured_at": "2026-09-01T00:00:00+00:00",
    "roster_entry_id": ROSTER_ENTRY_ID,
    "fiche_hash": FICHE_HASH,
    "suite_id": SUITE_ID,
    "suite_version": SUITE_VERSION,
    "cpu_energy_kwh": 0.0003,
    "cpu_energy_method": "estimated_tdp",
    "gpu_energy_kwh": 0.0009,
    "gpu_energy_method": "nvml_sampled",
    "ram_energy_kwh": 0.00012,
    "ram_energy_method": "estimated_constant",
    "energy_kwh": 0.00132,
    "emissions_kg": 0.000074,
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
                        "validated_host": {
                            "n_cpu_moe": 37,
                            "threads": 8,
                            "fiche_summary": "a laptop",
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

    return {
        "runtime": tmp_path / "runtime.jsonl",
        "quality": tmp_path / "quality.jsonl",
        "fiches": fiches,
        "roster": roster_path,
        "suites": suites,
    }
