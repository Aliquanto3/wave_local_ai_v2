from wave_local_ai_v2.fiche_registry import read_fiche, write_fiche
from wave_local_ai_v2.hardware import fiche_hash

FIXTURE_FICHE = {
    "cpu": "x",
    "ram_gb": 32.0,
    "gpu_name": "y",
    "gpu_driver_version": "1.2.3",
    "os": "z",
    "cuda_ceiling": "12.4",
    "llama_cpp_build": "b10537",
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
