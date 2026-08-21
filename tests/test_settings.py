from pathlib import Path

import pytest

import wave_local_ai_v2.settings as settings_module
from wave_local_ai_v2.settings import SettingsError, load_settings


@pytest.fixture(autouse=True)
def _no_dotenv_file(monkeypatch) -> None:
    # Prevent the repo's real .env from leaking into these tests.
    monkeypatch.setattr(settings_module, "load_dotenv", lambda: None)


def test_load_settings_returns_populated_settings(monkeypatch, tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("RUNTIME_RESULTS_PATH", str(tmp_path / "runtime.jsonl"))

    settings = load_settings()

    assert settings.slm_models_dir == models_dir
    assert settings.llama_server_path == server_path
    assert settings.results_path == tmp_path / "runtime.jsonl"


def test_load_settings_raises_when_llama_server_path_unset(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.delenv("LLAMA_SERVER_PATH", raising=False)

    with pytest.raises(SettingsError):
        load_settings()


def test_load_settings_raises_when_path_does_not_exist(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SLM_MODELS_DIR", str(tmp_path / "does-not-exist"))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(tmp_path / "does-not-exist.exe"))

    with pytest.raises(SettingsError):
        load_settings()
