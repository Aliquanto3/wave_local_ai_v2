from wave_local_ai_v2.fiche_registry import read_fiche, write_fiche
from wave_local_ai_v2.hardware import fiche_hash

FIXTURE_FICHE = {
    "cpu": "x",
    "ram_gb": 32.0,
    "gpu_name": "y",
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


def test_write_fiche_twice_leaves_exactly_one_file(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"

    hash_1 = write_fiche(FIXTURE_FICHE, registry_dir)
    hash_2 = write_fiche(FIXTURE_FICHE, registry_dir)

    assert hash_1 == hash_2 == fiche_hash(FIXTURE_FICHE)  # type: ignore[arg-type]
    assert list(registry_dir.glob("*.json")) == [registry_dir / f"{hash_1}.json"]


def test_read_fiche_on_an_unwritten_hash_returns_none(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"

    assert read_fiche("deadbeef" * 8, registry_dir) is None


def test_read_fiche_after_write_fiche_returns_the_fiche_including_flags(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"

    written_hash = write_fiche(FIXTURE_FICHE, registry_dir)
    stored = read_fiche(written_hash, registry_dir)

    assert stored == FIXTURE_FICHE
    assert stored["flags"] == ["-ngl", "99"]


def test_a_fiche_hash_carrying_traversal_resolves_to_none_never_reads_outside(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    escaped = tmp_path / "escaped.json"
    escaped.write_text('{"secret": true}', encoding="utf-8")

    assert read_fiche("../escaped", registry_dir) is None


def test_a_gpu_and_a_cpu_only_fiche_are_both_stored_each_with_its_own_flags(
    tmp_path,
) -> None:
    """Epic success check 1 at the registry: write-once by hash no longer lets
    the `gpu` fiche stand in for the `cpu_only` run's own."""
    registry_dir = tmp_path / "fiches"
    cpu_only = {
        **FIXTURE_FICHE,
        "compute_mode": "cpu_only",
        "flags": ["-ngl", "0", "--device", "none"],
    }

    gpu_hash = write_fiche(FIXTURE_FICHE, registry_dir)
    cpu_hash = write_fiche(cpu_only, registry_dir)

    assert gpu_hash != cpu_hash
    assert len(list(registry_dir.glob("*.json"))) == 2
    assert read_fiche(gpu_hash, registry_dir)["flags"] == ["-ngl", "99"]  # type: ignore[index]
    assert read_fiche(cpu_hash, registry_dir)["flags"] == [  # type: ignore[index]
        "-ngl",
        "0",
        "--device",
        "none",
    ]


def test_each_projection_verifies_under_its_citing_rows_schema_version(
    tmp_path,
) -> None:
    """A projection-2 fiche cited by a schema-22 row still verifies; the same
    fiche cited by a schema-23 row lacks the machine fields and is `edited`."""
    from wave_local_ai_v2.fiche_registry import verify_fiche

    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    legacy = {
        key: value
        for key, value in FIXTURE_FICHE.items()
        if key not in {"machine_id", "compute_mode"}
    }
    legacy_hash = fiche_hash(legacy, "2")  # type: ignore[arg-type]
    (registry_dir / f"{legacy_hash}.json").write_text(
        __import__("json").dumps(legacy, sort_keys=True), encoding="utf-8"
    )

    assert verify_fiche(legacy_hash, registry_dir, schema_version="22")["status"] == (
        "ok"
    )
    refused = verify_fiche(legacy_hash, registry_dir, schema_version="23")
    assert refused["status"] == "edited"
    assert "machine_id" in refused["changed_fields"][0]
