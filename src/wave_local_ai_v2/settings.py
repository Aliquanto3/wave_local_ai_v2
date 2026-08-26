"""Environment-backed configuration for the runtime measurement harness."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_RESULTS_PATH = "aidd_docs/results/runtime.jsonl"
DEFAULT_QUALITY_RESULTS_PATH = "aidd_docs/results/quality.jsonl"
DEFAULT_ROSTER_PATH = "aidd_docs/roster/models.json"
DEFAULT_ROSTER_ENTRY_ID = "qwen3.6-35b-a3b-ud-iq4xs"
# The two host-fitted launch flags, defaulted to the values the shipped roster
# entry records in its `validated_host` block. Named constants, not literals
# repeated in the dataclass and in `load_settings`: the byte-identical
# guarantee is "the defaults reproduce the baseline command", so the defaults
# must have exactly one definition for a test to bind.
DEFAULT_HOST_N_CPU_MOE = 37
DEFAULT_HOST_THREADS = 8
DEFAULT_FICHE_REGISTRY_DIR = "aidd_docs/results/fiches"
DEFAULT_RUNTIME_REFERENCE_PATH = "aidd_docs/results/runtime-reference.jsonl"
DEFAULT_QUALITY_REFERENCE_PATH = "aidd_docs/results/quality-reference.jsonl"
# Distinct from runtime_spread_threshold (criterion 7) even though both
# default to the same value: the spread threshold gates whether one run's own
# repetitions agree with each other, this gates whether two separate runs'
# medians agree -- a future PRD revision can move one without the other.
DEFAULT_RUNTIME_REPRODUCTION_TOLERANCE = 0.10
# Offline CodeCarbon grid mix + emissions factor (Story 15, plan.md's
# Resources): "FRA" selects the static country mix with no live geolocation
# call. The factor is CodeCarbon's own "FRA" carbon_intensity, 56.039
# gCO2eq/kWh (year 2023), from
# .venv/Lib/site-packages/codecarbon/data/private_infra/global_energy_mix.json.
DEFAULT_EMISSION_COUNTRY_ISO_CODE = "FRA"
DEFAULT_EMISSION_REGION = "FR"
DEFAULT_EMISSION_FACTOR_KG_PER_KWH = 0.056039
# Scope-3 cloud-inference estimate: median energy per output token reported
# for GPT-4o-scale frontier models, ~3e-4 Wh/token (0.3 Wh/query median),
# Joule (2026) "Energy use of AI inference, efficiency pathways, and
# test-time scaling" (https://www.cell.com/joule/fulltext/S2542-4351(26)00114-5),
# confirmed 2026-08-26. Chosen as the project's one Scope-3 estimate per
# plan.md's Decisions -- not model-specific, an order-of-magnitude figure for
# a comparably-sized commercial cloud model.
DEFAULT_SCOPE3_WH_PER_TOKEN = 0.0003


class SettingsError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one harness run."""

    slm_models_dir: Path
    llama_server_path: Path
    results_path: Path
    quality_results_path: Path = Path(DEFAULT_QUALITY_RESULTS_PATH)
    # No existence check at settings-load time, unlike slm_models_dir /
    # llama_server_path: a missing roster file is roster.py's failure to
    # raise, not settings'.
    roster_path: Path = Path(DEFAULT_ROSTER_PATH)
    roster_entry_id: str = DEFAULT_ROSTER_ENTRY_ID
    # repr=False: a traceback frame, a pytest assertion diff or a logged
    # Settings must not carry the credential. Attribute access is unaffected.
    mistral_api_key: str = field(default="", repr=False)
    # The repetition protocol: N counted repetitions, a cooldown between them,
    # a warm-up count excluded from N. Defaults are the PRD's published values.
    runtime_repetitions: int = 5
    runtime_cooldown_s: float = 10.0
    runtime_warmup_count: int = 1
    runtime_spread_threshold: float = 0.10
    # Host-fitted flags (plan.md's Decisions table): the only two launch flags
    # that are not roster data, defaulted to today's validated baseline
    # (`aidd_docs/roster/models.json`'s `validated_host` block) so a
    # byte-identical launch needs no `.env` override on this machine.
    host_n_cpu_moe: int = DEFAULT_HOST_N_CPU_MOE
    host_threads: int = DEFAULT_HOST_THREADS
    # No existence check at load time, mirrors roster_path: fiche_registry.write_fiche
    # creates it via mkdir(parents=True, exist_ok=True), matching results.append_row's
    # own pattern.
    fiche_registry_dir: Path = Path(DEFAULT_FICHE_REGISTRY_DIR)
    # Reference files a candidate row's verdict is computed against (story 16).
    # No existence check at load time: an absent reference is zero rows, i.e.
    # `not_comparable`, not a load failure.
    runtime_reference_path: Path = Path(DEFAULT_RUNTIME_REFERENCE_PATH)
    quality_reference_path: Path = Path(DEFAULT_QUALITY_REFERENCE_PATH)
    runtime_reproduction_tolerance: float = DEFAULT_RUNTIME_REPRODUCTION_TOLERANCE
    # Emissions configuration (Story 15, plan.md's Resources): the offline
    # grid mix, the published region label, and the local Scope-2 factor. See
    # the DEFAULT_* constants above for sources.
    emission_country_iso_code: str = DEFAULT_EMISSION_COUNTRY_ISO_CODE
    emission_region: str = DEFAULT_EMISSION_REGION
    emission_factor_kg_per_kwh: float = DEFAULT_EMISSION_FACTOR_KG_PER_KWH
    scope3_wh_per_token: float = DEFAULT_SCOPE3_WH_PER_TOKEN


def fiche_registry_dir_from_env() -> Path:
    """Resolve `FICHE_REGISTRY_DIR` alone, without a full settings load.

    `fiche_validator` reads published artifacts only: given explicit result
    paths it needs the registry directory and nothing else, so going through
    `load_settings` would make it refuse on a machine with no local model
    install (`SLM_MODELS_DIR` / `LLAMA_SERVER_PATH` must exist on disk there).
    `load_settings` reads the same value through this function, so the two
    forms can never resolve the directory differently.
    """
    load_dotenv()
    return Path(os.environ.get("FICHE_REGISTRY_DIR", DEFAULT_FICHE_REGISTRY_DIR))


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
    roster_path = Path(os.environ.get("ROSTER_PATH", DEFAULT_ROSTER_PATH))
    fiche_registry_dir = fiche_registry_dir_from_env()
    runtime_reference_path = Path(
        os.environ.get("RUNTIME_REFERENCE_PATH", DEFAULT_RUNTIME_REFERENCE_PATH)
    )
    quality_reference_path = Path(
        os.environ.get("QUALITY_REFERENCE_PATH", DEFAULT_QUALITY_REFERENCE_PATH)
    )
    roster_entry_id = os.environ.get("ROSTER_ENTRY_ID", DEFAULT_ROSTER_ENTRY_ID)
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
    runtime_spread_threshold = _require_numeric(
        "RUNTIME_SPREAD_THRESHOLD",
        0.10,
        float,
        minimum=0.0,
        minimum_reason="a spread threshold cannot be negative",
    )
    host_n_cpu_moe = _require_numeric(
        "SERVER_N_CPU_MOE",
        DEFAULT_HOST_N_CPU_MOE,
        int,
        minimum=0,
        minimum_reason="--n-cpu-moe cannot offload a negative number of experts",
    )
    host_threads = _require_numeric(
        "SERVER_THREADS",
        DEFAULT_HOST_THREADS,
        int,
        minimum=1,
        minimum_reason="-t needs at least one thread",
    )
    runtime_reproduction_tolerance = _require_numeric(
        "RUNTIME_REPRODUCTION_TOLERANCE",
        DEFAULT_RUNTIME_REPRODUCTION_TOLERANCE,
        float,
        minimum=0.0,
        minimum_reason="a reproduction tolerance cannot be negative",
    )
    emission_country_iso_code = os.environ.get(
        "EMISSION_COUNTRY_ISO_CODE", DEFAULT_EMISSION_COUNTRY_ISO_CODE
    )
    emission_region = os.environ.get("EMISSION_REGION", DEFAULT_EMISSION_REGION)
    emission_factor_kg_per_kwh = _require_numeric(
        "EMISSION_FACTOR_KG_PER_KWH",
        DEFAULT_EMISSION_FACTOR_KG_PER_KWH,
        float,
        minimum=0.0,
        minimum_reason="an emission factor cannot be negative",
    )
    scope3_wh_per_token = _require_numeric(
        "SCOPE3_WH_PER_TOKEN",
        DEFAULT_SCOPE3_WH_PER_TOKEN,
        float,
        minimum=0.0,
        minimum_reason="a Wh-per-token rate cannot be negative",
    )

    return Settings(
        slm_models_dir=slm_models_dir,
        llama_server_path=llama_server_path,
        results_path=results_path,
        quality_results_path=quality_results_path,
        roster_path=roster_path,
        fiche_registry_dir=fiche_registry_dir,
        roster_entry_id=roster_entry_id,
        mistral_api_key=mistral_api_key,
        runtime_repetitions=runtime_repetitions,
        runtime_cooldown_s=runtime_cooldown_s,
        runtime_warmup_count=runtime_warmup_count,
        runtime_spread_threshold=runtime_spread_threshold,
        host_n_cpu_moe=host_n_cpu_moe,
        host_threads=host_threads,
        runtime_reference_path=runtime_reference_path,
        quality_reference_path=quality_reference_path,
        runtime_reproduction_tolerance=runtime_reproduction_tolerance,
        emission_country_iso_code=emission_country_iso_code,
        emission_region=emission_region,
        emission_factor_kg_per_kwh=emission_factor_kg_per_kwh,
        scope3_wh_per_token=scope3_wh_per_token,
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
