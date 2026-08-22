"""Environment-backed configuration for the runtime measurement harness."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_RESULTS_PATH = "aidd_docs/results/runtime.jsonl"
DEFAULT_QUALITY_RESULTS_PATH = "aidd_docs/results/quality.jsonl"


class SettingsError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one harness run."""

    slm_models_dir: Path
    llama_server_path: Path
    results_path: Path
    quality_results_path: Path = Path(DEFAULT_QUALITY_RESULTS_PATH)
    # repr=False: a traceback frame, a pytest assertion diff or a logged
    # Settings must not carry the credential. Attribute access is unaffected.
    mistral_api_key: str = field(default="", repr=False)
    # The repetition protocol: N counted repetitions, a cooldown between them,
    # a warm-up count excluded from N. Defaults are the PRD's published values.
    runtime_repetitions: int = 5
    runtime_cooldown_s: float = 10.0
    runtime_warmup_count: int = 1


def load_settings() -> Settings:
    """Load settings from the environment (`.env` included), validating paths exist.

    `MISTRAL_API_KEY` is read but not required here: the runtime-only harness
    (`__init__.py`) must keep working with no cloud credential configured at
    all. The quality CLI validates it's non-empty at its own point of use.
    """
    load_dotenv()

    slm_models_dir = _require_existing_path("SLM_MODELS_DIR")
    llama_server_path = _require_existing_path("LLAMA_SERVER_PATH")
    results_path = Path(os.environ.get("RUNTIME_RESULTS_PATH", DEFAULT_RESULTS_PATH))
    quality_results_path = Path(
        os.environ.get("QUALITY_RESULTS_PATH", DEFAULT_QUALITY_RESULTS_PATH)
    )
    mistral_api_key = os.environ.get("MISTRAL_API_KEY", "")

    runtime_repetitions = _require_numeric(
        "RUNTIME_REPETITIONS",
        5,
        int,
        minimum=2,
        minimum_reason="the sample sd is undefined below it",
    )
    runtime_cooldown_s = _require_numeric(
        "RUNTIME_COOLDOWN_S",
        10.0,
        float,
        minimum=0.0,
        minimum_reason="a cooldown cannot be negative",
    )
    runtime_warmup_count = _require_numeric(
        "RUNTIME_WARMUP_COUNT",
        1,
        int,
        minimum=0,
        minimum_reason="a warm-up count cannot be negative",
    )

    return Settings(
        slm_models_dir=slm_models_dir,
        llama_server_path=llama_server_path,
        results_path=results_path,
        quality_results_path=quality_results_path,
        mistral_api_key=mistral_api_key,
        runtime_repetitions=runtime_repetitions,
        runtime_cooldown_s=runtime_cooldown_s,
        runtime_warmup_count=runtime_warmup_count,
    )


def _require_existing_path(env_var: str) -> Path:
    raw = os.environ.get(env_var)
    if not raw:
        raise SettingsError(f"{env_var} is not set")
    path = Path(raw)
    if not path.exists():
        raise SettingsError(f"{env_var}={raw} does not exist on disk")
    return path


def _require_numeric[T: (int, float)](
    env_var: str,
    default: T,
    cast: type[T],
    *,
    minimum: T,
    minimum_reason: str,
) -> T:
    """Read `env_var` as `cast`, falling back to `default` when unset.

    Raises `SettingsError` naming `env_var` when the value is non-numeric or
    below `minimum` -- never silently clamped or accepted.
    """
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        value = cast(raw)
    except ValueError as exc:
        raise SettingsError(f"{env_var}={raw!r} is not a valid number") from exc
    if value < minimum:
        raise SettingsError(
            f"{env_var}={raw!r} is below the minimum of {minimum}: {minimum_reason}"
        )
    return value
