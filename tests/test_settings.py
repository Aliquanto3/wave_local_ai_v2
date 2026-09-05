from pathlib import Path

import pytest

import wave_local_ai_v2.settings as settings_module
from wave_local_ai_v2.settings import (
    DEFAULT_CLOUD_RETRY_MAX_ATTEMPTS,
    DEFAULT_EMISSION_COUNTRY_ISO_CODE,
    DEFAULT_EMISSION_FACTOR_KG_PER_KWH,
    DEFAULT_EMISSION_REGION,
    DEFAULT_FICHE_REGISTRY_DIR,
    DEFAULT_GOOGLE_REQUEST_PACING_S,
    DEFAULT_KWH_PRICE_EUR,
    DEFAULT_KWH_PRICE_RECORDED_AT,
    DEFAULT_MISTRAL_REQUEST_PACING_S,
    DEFAULT_QUALITY_REFERENCE_PATH,
    DEFAULT_QUALITY_RESULTS_PATH,
    DEFAULT_RUNTIME_REFERENCE_PATH,
    DEFAULT_SCOPE3_WH_PER_TOKEN,
    KNOWN_QUALITY_PROVIDERS,
    Settings,
    SettingsError,
    load_settings,
)


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
    monkeypatch.setenv("QUALITY_RESULTS_PATH", str(tmp_path / "quality.jsonl"))
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    settings = load_settings()

    assert settings.slm_models_dir == models_dir
    assert settings.llama_server_path == server_path
    assert settings.results_path == tmp_path / "runtime.jsonl"
    assert settings.quality_results_path == tmp_path / "quality.jsonl"
    assert settings.mistral_api_key == "fake-key"  # pragma: allowlist secret
    assert settings.google_api_key == ""
    assert settings.runtime_repetitions == 5
    assert settings.runtime_cooldown_s == 10.0
    assert settings.runtime_warmup_count == 1
    assert settings.runtime_spread_threshold == 0.10


def test_load_settings_defaults_quality_path_and_mistral_key_when_unset(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.delenv("QUALITY_RESULTS_PATH", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    settings = load_settings()

    assert settings.quality_results_path == Path(DEFAULT_QUALITY_RESULTS_PATH)
    assert settings.mistral_api_key == ""
    assert settings.google_api_key == ""


def test_load_settings_reads_the_repetition_protocol_overrides(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("RUNTIME_REPETITIONS", "2")
    monkeypatch.setenv("RUNTIME_COOLDOWN_S", "0.5")
    monkeypatch.setenv("RUNTIME_WARMUP_COUNT", "0")
    monkeypatch.setenv("RUNTIME_SPREAD_THRESHOLD", "0.20")

    settings = load_settings()

    assert settings.runtime_repetitions == 2
    assert settings.runtime_cooldown_s == 0.5
    assert settings.runtime_warmup_count == 0
    assert settings.runtime_spread_threshold == 0.20


def test_load_settings_defaults_the_fiche_and_reference_paths_when_unset(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    for env_var in (
        "FICHE_REGISTRY_DIR",
        "RUNTIME_REFERENCE_PATH",
        "QUALITY_REFERENCE_PATH",
        "RUNTIME_REPRODUCTION_TOLERANCE",
    ):
        monkeypatch.delenv(env_var, raising=False)

    settings = load_settings()

    assert settings.fiche_registry_dir == Path(DEFAULT_FICHE_REGISTRY_DIR)
    assert settings.runtime_reference_path == Path(DEFAULT_RUNTIME_REFERENCE_PATH)
    assert settings.quality_reference_path == Path(DEFAULT_QUALITY_REFERENCE_PATH)
    assert settings.runtime_reproduction_tolerance == 0.10


def test_load_settings_defaults_the_emission_fields_when_unset(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    for env_var in (
        "EMISSION_COUNTRY_ISO_CODE",
        "EMISSION_REGION",
        "EMISSION_FACTOR_KG_PER_KWH",
        "SCOPE3_WH_PER_TOKEN",
    ):
        monkeypatch.delenv(env_var, raising=False)

    settings = load_settings()

    assert settings.emission_country_iso_code == DEFAULT_EMISSION_COUNTRY_ISO_CODE
    assert settings.emission_region == DEFAULT_EMISSION_REGION
    assert settings.emission_factor_kg_per_kwh == DEFAULT_EMISSION_FACTOR_KG_PER_KWH
    assert settings.scope3_wh_per_token == DEFAULT_SCOPE3_WH_PER_TOKEN


def test_load_settings_reads_the_emission_overrides(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("EMISSION_COUNTRY_ISO_CODE", "USA")
    monkeypatch.setenv("EMISSION_REGION", "US")
    monkeypatch.setenv("EMISSION_FACTOR_KG_PER_KWH", "0.4")
    monkeypatch.setenv("SCOPE3_WH_PER_TOKEN", "0.0005")

    settings = load_settings()

    assert settings.emission_country_iso_code == "USA"
    assert settings.emission_region == "US"
    assert settings.emission_factor_kg_per_kwh == 0.4
    assert settings.scope3_wh_per_token == 0.0005


@pytest.mark.parametrize(
    ("env_var", "value"),
    [
        ("EMISSION_FACTOR_KG_PER_KWH", "-0.1"),
        ("EMISSION_FACTOR_KG_PER_KWH", "not-a-number"),
        ("SCOPE3_WH_PER_TOKEN", "-0.1"),
        ("SCOPE3_WH_PER_TOKEN", "not-a-number"),
    ],
)
def test_load_settings_refuses_invalid_emission_values(
    monkeypatch, tmp_path: Path, env_var: str, value: str
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv(env_var, value)

    with pytest.raises(SettingsError, match=env_var):
        load_settings()


def test_load_settings_defaults_the_kwh_price_fields_when_unset(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.delenv("KWH_PRICE_EUR", raising=False)
    monkeypatch.delenv("KWH_PRICE_RECORDED_AT", raising=False)

    settings = load_settings()

    assert settings.kwh_price_eur == DEFAULT_KWH_PRICE_EUR
    assert settings.kwh_price_recorded_at == DEFAULT_KWH_PRICE_RECORDED_AT


def test_load_settings_reads_the_kwh_price_overrides(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("KWH_PRICE_EUR", "0.25")
    monkeypatch.setenv("KWH_PRICE_RECORDED_AT", "2026-01-01")

    settings = load_settings()

    assert settings.kwh_price_eur == 0.25
    assert settings.kwh_price_recorded_at == "2026-01-01"


@pytest.mark.parametrize("value", ["-0.1", "not-a-number"])
def test_load_settings_refuses_invalid_kwh_price(
    monkeypatch, tmp_path: Path, value: str
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("KWH_PRICE_EUR", value)

    with pytest.raises(SettingsError, match="KWH_PRICE_EUR"):
        load_settings()


def test_load_settings_reads_the_fiche_and_reference_overrides(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("FICHE_REGISTRY_DIR", str(tmp_path / "fiches"))
    monkeypatch.setenv("RUNTIME_REFERENCE_PATH", str(tmp_path / "runtime-ref.jsonl"))
    monkeypatch.setenv("QUALITY_REFERENCE_PATH", str(tmp_path / "quality-ref.jsonl"))
    monkeypatch.setenv("RUNTIME_REPRODUCTION_TOLERANCE", "0.25")

    settings = load_settings()

    assert settings.fiche_registry_dir == tmp_path / "fiches"
    assert settings.runtime_reference_path == tmp_path / "runtime-ref.jsonl"
    assert settings.quality_reference_path == tmp_path / "quality-ref.jsonl"
    assert settings.runtime_reproduction_tolerance == 0.25


@pytest.mark.parametrize(
    ("env_var", "value"),
    [
        ("RUNTIME_REPETITIONS", "1"),
        ("RUNTIME_REPETITIONS", "0"),
        ("RUNTIME_REPETITIONS", "not-a-number"),
        ("RUNTIME_COOLDOWN_S", "-1"),
        ("RUNTIME_COOLDOWN_S", "not-a-number"),
        ("RUNTIME_WARMUP_COUNT", "-1"),
        ("RUNTIME_WARMUP_COUNT", "not-a-number"),
        ("RUNTIME_SPREAD_THRESHOLD", "-0.1"),
        ("RUNTIME_SPREAD_THRESHOLD", "not-a-number"),
        ("RUNTIME_REPRODUCTION_TOLERANCE", "-0.1"),
        ("RUNTIME_REPRODUCTION_TOLERANCE", "not-a-number"),
    ],
)
def test_load_settings_refuses_invalid_repetition_protocol_values(
    monkeypatch, tmp_path: Path, env_var: str, value: str
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv(env_var, value)

    with pytest.raises(SettingsError, match=env_var):
        load_settings()


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


def test_repr_omits_the_mistral_api_key_but_attribute_access_keeps_it(
    tmp_path: Path,
) -> None:
    secret = "secret-value"  # pragma: allowlist secret
    settings = Settings(
        slm_models_dir=tmp_path,
        llama_server_path=tmp_path / "llama-server.exe",
        results_path=tmp_path / "runtime.jsonl",
        mistral_api_key=secret,
    )

    assert secret not in repr(settings)
    assert settings.mistral_api_key == secret


def test_load_settings_defaults_quality_providers_to_all_three(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.delenv("QUALITY_PROVIDERS", raising=False)

    settings = load_settings()

    assert settings.quality_providers == KNOWN_QUALITY_PROVIDERS


def test_load_settings_reads_a_restricted_quality_providers_list(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("QUALITY_PROVIDERS", "local,google")

    settings = load_settings()

    assert settings.quality_providers == {"local", "google"}


def test_load_settings_refuses_an_unrecognised_quality_provider(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("QUALITY_PROVIDERS", "local,anthropic")

    with pytest.raises(SettingsError, match="anthropic"):
        load_settings()


def test_load_settings_defaults_the_pacing_and_retry_fields_when_unset(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.delenv("MISTRAL_REQUEST_PACING_S", raising=False)
    monkeypatch.delenv("GOOGLE_REQUEST_PACING_S", raising=False)
    monkeypatch.delenv("CLOUD_RETRY_MAX_ATTEMPTS", raising=False)

    settings = load_settings()

    assert settings.mistral_request_pacing_s == DEFAULT_MISTRAL_REQUEST_PACING_S
    assert settings.google_request_pacing_s == DEFAULT_GOOGLE_REQUEST_PACING_S
    assert settings.cloud_retry_max_attempts == DEFAULT_CLOUD_RETRY_MAX_ATTEMPTS


def test_load_settings_reads_the_pacing_and_retry_overrides(
    monkeypatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("MISTRAL_REQUEST_PACING_S", "2.5")
    monkeypatch.setenv("GOOGLE_REQUEST_PACING_S", "6")
    monkeypatch.setenv("CLOUD_RETRY_MAX_ATTEMPTS", "9")

    settings = load_settings()

    assert settings.mistral_request_pacing_s == 2.5
    assert settings.google_request_pacing_s == 6.0
    assert settings.cloud_retry_max_attempts == 9


def test_load_settings_accepts_a_zero_pacing_interval(
    monkeypatch, tmp_path: Path
) -> None:
    # Zero is pacing disabled, an operator's choice on a paid tier; only a
    # negative interval is refused.
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv("MISTRAL_REQUEST_PACING_S", "0")
    monkeypatch.setenv("GOOGLE_REQUEST_PACING_S", "0")

    settings = load_settings()

    assert settings.mistral_request_pacing_s == 0.0
    assert settings.google_request_pacing_s == 0.0


@pytest.mark.parametrize(
    ("env_var", "value"),
    [
        ("MISTRAL_REQUEST_PACING_S", "-0.1"),
        ("MISTRAL_REQUEST_PACING_S", "not-a-number"),
        ("GOOGLE_REQUEST_PACING_S", "-0.1"),
        ("GOOGLE_REQUEST_PACING_S", "not-a-number"),
        # Zero attempts would make the budget refuse every retry, which is not
        # "no retry configuration" but a batch that gives up on its first 429.
        ("CLOUD_RETRY_MAX_ATTEMPTS", "0"),
        ("CLOUD_RETRY_MAX_ATTEMPTS", "not-a-number"),
        ("CLOUD_RETRY_MAX_ATTEMPTS", "1.5"),
    ],
)
def test_load_settings_refuses_invalid_pacing_and_retry_values(
    monkeypatch, tmp_path: Path, env_var: str, value: str
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    monkeypatch.setenv("SLM_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(server_path))
    monkeypatch.setenv(env_var, value)

    with pytest.raises(SettingsError, match=env_var):
        load_settings()


def test_repr_omits_the_google_api_key_but_attribute_access_keeps_it(
    tmp_path: Path,
) -> None:
    secret = "secret-value"  # pragma: allowlist secret
    settings = Settings(
        slm_models_dir=tmp_path,
        llama_server_path=tmp_path / "llama-server.exe",
        results_path=tmp_path / "runtime.jsonl",
        google_api_key=secret,
    )

    assert secret not in repr(settings)
    assert settings.google_api_key == secret
