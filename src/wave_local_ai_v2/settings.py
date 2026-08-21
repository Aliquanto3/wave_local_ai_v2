"""Environment-backed configuration for the runtime measurement harness."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_RESULTS_PATH = "aidd_docs/results/runtime.jsonl"


class SettingsError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one harness run."""

    slm_models_dir: Path
    llama_server_path: Path
    results_path: Path


def load_settings() -> Settings:
    """Load settings from the environment (`.env` included), validating paths exist."""
    load_dotenv()

    slm_models_dir = _require_existing_path("SLM_MODELS_DIR")
    llama_server_path = _require_existing_path("LLAMA_SERVER_PATH")
    results_path = Path(os.environ.get("RUNTIME_RESULTS_PATH", DEFAULT_RESULTS_PATH))

    return Settings(
        slm_models_dir=slm_models_dir,
        llama_server_path=llama_server_path,
        results_path=results_path,
    )


def _require_existing_path(env_var: str) -> Path:
    raw = os.environ.get(env_var)
    if not raw:
        raise SettingsError(f"{env_var} is not set")
    path = Path(raw)
    if not path.exists():
        raise SettingsError(f"{env_var}={raw} does not exist on disk")
    return path
