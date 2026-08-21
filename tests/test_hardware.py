from wave_local_ai_v2.hardware import capture_fiche


def test_capture_fiche_returns_all_documented_keys() -> None:
    fiche = capture_fiche()

    assert set(fiche.keys()) == {
        "cpu",
        "ram_gb",
        "gpu_name",
        "gpu_driver_version",
        "cuda_ceiling",
        "os",
    }
    assert fiche["cpu"]
    assert fiche["os"]


def test_capture_fiche_degrades_gracefully_when_nvml_unavailable(monkeypatch) -> None:
    from wave_local_ai_v2 import hardware

    monkeypatch.setattr(hardware, "_capture_gpu_fields", lambda: (None, None, None))

    fiche = hardware.capture_fiche()

    assert fiche["gpu_name"] is None
    assert fiche["gpu_driver_version"] is None
    assert fiche["cuda_ceiling"] is None
