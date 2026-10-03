"""Environment-backed configuration for the runtime measurement harness."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from wave_local_ai_v2 import machines

DEFAULT_RESULTS_PATH = "aidd_docs/results/runtime.jsonl"
DEFAULT_QUALITY_RESULTS_PATH = "aidd_docs/results/quality.jsonl"
DEFAULT_ROSTER_PATH = "aidd_docs/roster/models.json"
DEFAULT_ROSTER_ENTRY_ID = "qwen3.6-35b-a3b-ud-iq4xs"
DEFAULT_FICHE_REGISTRY_DIR = "aidd_docs/results/fiches"
# Where `suite_snapshot` exports each suite definition a published row cites.
# A constant here rather than a literal in that module, for the reason
# `fiche_registry.py` states about its own directory: an artifact path is
# configuration, never hardcoded in the module that writes it.
DEFAULT_SUITE_DEFINITIONS_DIR = "aidd_docs/results/suite-definitions"
DEFAULT_COMPARISONS_DIR = "aidd_docs/results/comparisons"
DEFAULT_LEADER_SETS_DIR = "aidd_docs/results/leader-sets"
# Where campaign declarations live, one `<campaign_id>.json` each: beside the
# results, outside the committed stores (`campaigns.py`).
DEFAULT_CAMPAIGNS_DIR = "aidd_docs/campaigns"
# The per-machine results root: one tracked location `<root>/<machine_id>/`
# per declared machine (`machine_results.py`), holding the runtime and quality
# rows promoted from that machine's live stores and the refusal records the
# pre-flight appends there directly (`preflight.refusal_path`). Tracked,
# unlike the live stores: the ignore rule covers only the top-level
# `aidd_docs/results/*.jsonl`. The published bundle is merged from it
# (`bundle_merge.py`).
DEFAULT_MACHINE_RESULTS_ROOT = "aidd_docs/results/machines"
# The bundle's third file: every location's refusal records, never a row.
DEFAULT_REFUSALS_REFERENCE_PATH = "aidd_docs/results/refusals-reference.jsonl"
# Where `use_case_coverage` publishes the coverage record, and only once every
# PRD use case in it carries a resolvable state.
DEFAULT_USE_CASE_COVERAGE_PATH = "aidd_docs/results/use-case-coverage.json"
DEFAULT_RUNTIME_REFERENCE_PATH = "aidd_docs/results/runtime-reference.jsonl"
DEFAULT_QUALITY_REFERENCE_PATH = "aidd_docs/results/quality-reference.jsonl"
# The judge probe's own store. Unlike its two neighbours above -- curated
# snapshots no CLI ever writes to -- this reference-named file is written
# directly by `wave-local-ai-v2-judge-probe`: the probe is a deliberate
# one-off proof that the judged machinery runs end to end, not a per-machine
# benchmark that reruns, so a curated hand-copy would add a step and no
# evidence. A re-run under a fresh run_id appends a second generation of rows
# beside the first; the operator's reset is `git checkout --` on this file.
DEFAULT_JUDGE_PROBE_REFERENCE_PATH = "aidd_docs/results/judge-probe-reference.jsonl"
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
# French residential regulated tariff (EDF Tarif Bleu, Base option),
# 0.1940 EUR/kWh, effective February 2026 per the CRE's semiannual review
# (https://en.selectra.info/energy-france/suppliers/edf/tarif-bleu),
# confirmed 2026-08-26. A configured value, not a live retrieval --
# kwh_price_recorded_at is the tariff's own effective date, not computed at
# run time.
DEFAULT_KWH_PRICE_EUR = 0.1940
DEFAULT_KWH_PRICE_RECORDED_AT = "2026-02-01"
# The quality CLI's cloud provider set is configuration, not a hard-wired
# pair: an operator can run with only one cloud subject enabled (or none),
# without editing code. `local` names the on-machine SLM batch; it stays
# unconditional (quality_cli always attempts it) -- only membership of
# `mistral`/`google` in this set is checked. Listed anyway for a reader
# scanning .env to see the whole picture, not just the two that can be
# individually disabled.
DEFAULT_QUALITY_PROVIDERS = "local,mistral,google"
KNOWN_QUALITY_PROVIDERS = frozenset({"local", "mistral", "google"})
# Per-provider request pacing (a rate-limited run persists, resumes and never
# re-pays): a suite item costs one Mistral request but two Google ones
# (check_context_fits, then complete_prompt), which is why Google's interval
# sits closer to the free tier's 15 RPM ceiling. 4.1s narrows the 4.5s a
# live run confirmed safe (see this story's plan.md Decisions/Risks) -- a
# margin miss now degrades to a paced retry instead of a hard failure, which
# is the whole point of this story existing.
DEFAULT_MISTRAL_REQUEST_PACING_S = 1.1
DEFAULT_GOOGLE_REQUEST_PACING_S = 4.1
# The retry budget a cloud batch runs under grows with its item count (a
# publication-size cloud batch survives its rate limits and resumes per
# item): max(minimum, ceil(items * per_item)). A fixed batch total gave a
# 100-item Google batch -- 200 paced requests -- the same 4 retries as a
# 20-item one. The two defaults keep that 20-item batch at exactly the 4 the
# development-size story validated live, and hand a 100-item batch 20 and a
# 300-item one 60: the budget per item is held constant instead of shrinking
# as the suite grows. Every row records the budget it ran under.
DEFAULT_CLOUD_RETRY_MIN_RETRIES = 4
DEFAULT_CLOUD_RETRY_RETRIES_PER_ITEM = 0.2
# When two judges' scores on one item count as a disagreement worth marking
# (this increment's decision): more than 1 point apart on a 1-5 ordinal
# rubric, or any category mismatch on a categorical one. A per-suite override
# is the named seam -- a judged suite that declares its own threshold beats
# this default; until one exists, this is the only value in play.
DEFAULT_CONTESTED_ORDINAL_MAX_DELTA = 1

# The read-only results service (`service.py`). Loopback by default: this
# story ships plain HTTP, and a default that binds every interface would put
# an unencrypted service on the network the moment someone runs it.
DEFAULT_SERVICE_HOST = "127.0.0.1"
DEFAULT_SERVICE_PORT = 8000
# The schema version at or above which a stored row is rendered rather than
# counted. "7" is the published bundle's own version
# (`tests/test_reference_bundle.PUBLISHED_BUNDLE_SCHEMA_VERSION`), so one
# unchanged service serves the committed bundle at "7" and the live stores at
# "11" with no code change, while the superseded `*.schema-1.jsonl` rows fall
# below it and are counted rather than rendered. Compared as an integer, never
# as a string -- see `results.read_rows_from_floor`.
DEFAULT_SERVICE_SCHEMA_FLOOR = "7"
# No default certificate/key path ships, mirroring SERVICE_API_KEY: an unset
# or non-existent SERVICE_TLS_CERTFILE/SERVICE_TLS_KEYFILE is a SettingsError
# naming the variable, not a plain-HTTP fallback.

# Where the built dashboard bundle lives. Never committed (plan.md's
# Decisions): the fresh-machine command (`cd frontend && npm ci && npm run
# build`) produces this directory, matching `uv sync`'s own posture for the
# Python half.
DEFAULT_DASHBOARD_BUNDLE_DIR = "frontend/dist"
# `DASHBOARD_ORIGIN` unset resolves from the bound host/port rather than a
# separate hardcoded default: the shipped topology is single-origin, so the
# dashboard's own origin and the service's bound address are the same fact
# and must not be able to drift apart.

# The demo run console (`/api/console/*`) is off unless explicitly, exactly
# turned on: it is the one surface through which a browser can start a CLI
# run on this machine. Only these two literals are read; anything else
# (`True`, `1`, `yes`, an empty value) is a SettingsError naming the
# variable, never a guess in either direction.
DEFAULT_SERVICE_DEMO_MODE = False
_DEMO_MODE_VALUES = {"true": True, "false": False}

# The playground's caps: a pasted document cannot hold the demo machine. The
# prompt is capped in characters (checked before anything is sent), the answer
# in generated tokens (sent as the request's `max_tokens`).
DEFAULT_PLAYGROUND_MAX_PROMPT_CHARS = 4000
DEFAULT_PLAYGROUND_MAX_TOKENS = 512


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
    # Same reasoning and same repr=False as mistral_api_key above.
    google_api_key: str = field(default="", repr=False)
    # Which quality-CLI providers to attempt this run, drawn from
    # KNOWN_QUALITY_PROVIDERS. A cloud provider (mistral/google) not in this
    # set is skipped the same way a missing key or a pre-flight failure is:
    # one stderr line naming it, zero rows, run continues.
    quality_providers: frozenset[str] = frozenset({"local", "mistral", "google"})
    # The repetition protocol: N counted repetitions, a cooldown between them,
    # a warm-up count excluded from N. Defaults are the PRD's published values.
    runtime_repetitions: int = 5
    runtime_cooldown_s: float = 10.0
    runtime_warmup_count: int = 1
    runtime_spread_threshold: float = 0.10
    # The operator's explicit overrides of the run profile (`profiles.py`),
    # applied last in the resolution order (entry default, profile, operator).
    # `None` is the unset state and means "the run profile decides"; a set
    # value is recorded on every row as a deviation from the profile. `0` is
    # an explicit instruction to offload no experts, which a dense entry and a
    # `cpu_only` run refuse, never the absence of an instruction.
    host_n_cpu_moe: int | None = None
    host_threads: int | None = None
    # The declared machine and the compute mode a run is executed under, as
    # `MACHINE_ID` / `COMPUTE_MODE` named them, or `None` when unset. They are
    # never defaulted: `load_settings` reads them with no fallback, and every
    # row-writing CLI calls `require_run_profile` before anything else, which
    # refuses an absent or undeclared value. `None` here only lets a command
    # that writes no row (the candidate gate, the validator) load settings.
    machine_id: str | None = None
    compute_mode: str | None = None
    # The campaign a run belongs to, as `CAMPAIGN_ID` named it, or `None`: a
    # run under no campaign stays possible and its rows record that they
    # belong to none. A named campaign is loaded from `campaigns_dir` and the
    # run checked against it by `campaigns.require_run_campaign`.
    campaign_id: str | None = None
    campaigns_dir: Path = Path(DEFAULT_CAMPAIGNS_DIR)
    # No existence check at load time: `results.append_refusal` creates it.
    machine_results_root: Path = Path(DEFAULT_MACHINE_RESULTS_ROOT)
    # No existence check at load time, mirrors roster_path: fiche_registry.write_fiche
    # creates it via mkdir(parents=True, exist_ok=True), matching results.append_row's
    # own pattern.
    fiche_registry_dir: Path = Path(DEFAULT_FICHE_REGISTRY_DIR)
    # Reference files a candidate row's verdict is computed against (story 16).
    # No existence check at load time: an absent reference is zero rows, i.e.
    # `not_comparable`, not a load failure.
    runtime_reference_path: Path = Path(DEFAULT_RUNTIME_REFERENCE_PATH)
    quality_reference_path: Path = Path(DEFAULT_QUALITY_REFERENCE_PATH)
    # Where the judge probe writes its own rows. Same no-existence-check rule
    # as the two paths above; see the DEFAULT_* constant for why this one is
    # written by a CLI and they are not.
    judge_probe_reference_path: Path = Path(DEFAULT_JUDGE_PROBE_REFERENCE_PATH)
    runtime_reproduction_tolerance: float = DEFAULT_RUNTIME_REPRODUCTION_TOLERANCE
    # Emissions configuration (Story 15, plan.md's Resources): the offline
    # grid mix, the published region label, and the local Scope-2 factor. See
    # the DEFAULT_* constants above for sources.
    emission_country_iso_code: str = DEFAULT_EMISSION_COUNTRY_ISO_CODE
    emission_region: str = DEFAULT_EMISSION_REGION
    emission_factor_kg_per_kwh: float = DEFAULT_EMISSION_FACTOR_KG_PER_KWH
    scope3_wh_per_token: float = DEFAULT_SCOPE3_WH_PER_TOKEN
    # Cost configuration (Story 16): the local kWh price local_cost derives
    # cost_total from, and the date it was recorded. See the DEFAULT_* above.
    kwh_price_eur: float = DEFAULT_KWH_PRICE_EUR
    kwh_price_recorded_at: str = DEFAULT_KWH_PRICE_RECORDED_AT
    # Pacing/retry configuration (a rate-limited run persists, resumes and
    # never re-pays): see the DEFAULT_* constants above for sources.
    mistral_request_pacing_s: float = DEFAULT_MISTRAL_REQUEST_PACING_S
    google_request_pacing_s: float = DEFAULT_GOOGLE_REQUEST_PACING_S
    cloud_retry_min_retries: int = DEFAULT_CLOUD_RETRY_MIN_RETRIES
    cloud_retry_retries_per_item: float = DEFAULT_CLOUD_RETRY_RETRIES_PER_ITEM
    # Judge agreement (a judged score carries two judges or an honest flag):
    # the ordinal delta above which one item's two judge scores are contested.
    contested_ordinal_max_delta: int = DEFAULT_CONTESTED_ORDINAL_MAX_DELTA


@dataclass(frozen=True)
class ServiceSettings:
    """Resolved configuration for one run of the read-only results service.

    Everything the service needs to read published artifacts and nothing that
    would require a local model install: `Settings` refuses to load without
    `SLM_MODELS_DIR` and `LLAMA_SERVER_PATH` on disk, which a reader of
    committed results has no reason to have.
    """

    # repr=False for the same reason `Settings.mistral_api_key` carries it: a
    # traceback frame, a pytest assertion diff or a logged settings object
    # must not carry the credential. Attribute access is unaffected.
    api_key: str = field(repr=False)
    host: str
    port: int
    schema_floor: str
    runtime_results_path: Path
    quality_results_path: Path
    fiche_registry_dir: Path
    roster_path: Path
    suite_definitions_dir: Path
    leader_sets_dir: Path
    dashboard_bundle_dir: Path
    dashboard_origin: str
    tls_certfile: Path
    tls_keyfile: Path
    # The declared machine registry a runtime row's `machine_id` resolves
    # against: the tracked file, the same one the run CLIs check rows against.
    machine_registry_path: Path = Path(machines.DEFAULT_REGISTRY_PATH)
    demo_mode: bool = DEFAULT_SERVICE_DEMO_MODE
    # The machine this service runs on, as `MACHINE_ID` names it, or `None`.
    # Read raw and never required: the read routes need no machine. The demo
    # console offers only this machine's run profiles and checks it against
    # the registry itself, so a run is never launched under another machine.
    machine_id: str | None = None
    # The playground's local install, read raw from the same variables the run
    # CLIs require and never required here: the read routes need no model.
    llama_server_path: Path | None = None
    slm_models_dir: Path | None = None
    playground_max_prompt_chars: int = DEFAULT_PLAYGROUND_MAX_PROMPT_CHARS
    playground_max_tokens: int = DEFAULT_PLAYGROUND_MAX_TOKENS


def load_service_settings() -> ServiceSettings:
    """Load the service's settings from the environment (`.env` included).

    Refuses an unset or empty `SERVICE_API_KEY` unconditionally: the PRD's
    criterion ("the service refuses to start without one") is stated without
    exception, and it is taken literally rather than relaxed for a loopback
    bind. A development default would be the key that ships to production.

    `SERVICE_TLS_CERTFILE`/`SERVICE_TLS_KEYFILE` are required and
    existence-checked the same way: the service binds only over TLS, on
    loopback included, so an unset or missing pair is refused before the app
    is built rather than silently served over plain HTTP.

    The store, roster and registry paths are read from the *same* environment
    variables and `DEFAULT_*` constants `load_settings` uses -- the registry
    through `fiche_registry_dir_from_env()` itself -- so the two forms can
    never resolve a path differently. None of them is checked for existence:
    a missing store is zero rows to a reader, exactly as a missing roster file
    is `roster.py`'s failure to raise rather than this module's.
    """
    load_dotenv()

    api_key = os.environ.get("SERVICE_API_KEY", "")
    if not api_key:
        raise SettingsError("SERVICE_API_KEY is not set")

    host = os.environ.get("SERVICE_HOST", DEFAULT_SERVICE_HOST)
    port = _require_numeric(
        "SERVICE_PORT",
        DEFAULT_SERVICE_PORT,
        int,
        minimum=1,
        minimum_reason="port 0 asks the OS to pick, which no client could find",
    )
    schema_floor = os.environ.get("SERVICE_SCHEMA_FLOOR", DEFAULT_SERVICE_SCHEMA_FLOOR)
    try:
        int(schema_floor)
    except ValueError as exc:
        raise SettingsError(
            f"SERVICE_SCHEMA_FLOOR={schema_floor!r} is not an integer: schema "
            "versions are compared numerically, never as strings"
        ) from exc

    return ServiceSettings(
        api_key=api_key,
        host=host,
        port=port,
        schema_floor=schema_floor,
        runtime_results_path=Path(
            os.environ.get("RUNTIME_RESULTS_PATH", DEFAULT_RESULTS_PATH)
        ),
        quality_results_path=Path(
            os.environ.get("QUALITY_RESULTS_PATH", DEFAULT_QUALITY_RESULTS_PATH)
        ),
        fiche_registry_dir=fiche_registry_dir_from_env(),
        roster_path=Path(os.environ.get("ROSTER_PATH", DEFAULT_ROSTER_PATH)),
        suite_definitions_dir=Path(
            os.environ.get("SUITE_DEFINITIONS_DIR", DEFAULT_SUITE_DEFINITIONS_DIR)
        ),
        leader_sets_dir=Path(
            os.environ.get("LEADER_SETS_DIR", DEFAULT_LEADER_SETS_DIR)
        ),
        dashboard_bundle_dir=Path(
            os.environ.get("DASHBOARD_BUNDLE_DIR", DEFAULT_DASHBOARD_BUNDLE_DIR)
        ),
        dashboard_origin=os.environ.get("DASHBOARD_ORIGIN", f"https://{host}:{port}"),
        tls_certfile=_require_existing_path("SERVICE_TLS_CERTFILE"),
        tls_keyfile=_require_existing_path("SERVICE_TLS_KEYFILE"),
        demo_mode=_parse_demo_mode(os.environ.get("SERVICE_DEMO_MODE")),
        machine_id=os.environ.get("MACHINE_ID") or None,
        llama_server_path=_optional_path("LLAMA_SERVER_PATH"),
        slm_models_dir=_optional_path("SLM_MODELS_DIR"),
        playground_max_prompt_chars=_require_numeric(
            "PLAYGROUND_MAX_PROMPT_CHARS",
            DEFAULT_PLAYGROUND_MAX_PROMPT_CHARS,
            int,
            minimum=1,
            minimum_reason="a playground prompt needs at least one character",
        ),
        playground_max_tokens=_require_numeric(
            "PLAYGROUND_MAX_TOKENS",
            DEFAULT_PLAYGROUND_MAX_TOKENS,
            int,
            minimum=1,
            minimum_reason="a playground answer needs at least one token",
        ),
    )


def _optional_path(env_var: str) -> Path | None:
    """`env_var` as a path, or `None` when unset or empty; never checked here."""
    raw = os.environ.get(env_var)
    return Path(raw) if raw else None


def _parse_demo_mode(raw: str | None) -> bool:
    """Read `SERVICE_DEMO_MODE`: unset is off, and only `true`/`false` parse.

    Case-sensitive on purpose: a strict parser accepting one spelling cannot
    read a typo as either state.
    """
    if raw is None:
        return DEFAULT_SERVICE_DEMO_MODE
    if raw not in _DEMO_MODE_VALUES:
        raise SettingsError(
            f"SERVICE_DEMO_MODE={raw!r} is not recognised: must be exactly "
            "'true' or 'false', or unset (off)"
        )
    return _DEMO_MODE_VALUES[raw]


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


def machine_results_root_from_env() -> Path:
    """Resolve `MACHINE_RESULTS_ROOT` alone, without a full settings load.

    Promotion and the bundle merge touch tracked files only, never a model or
    a server, so they must not refuse on a machine with no local install.
    """
    load_dotenv()
    return Path(os.environ.get("MACHINE_RESULTS_ROOT", DEFAULT_MACHINE_RESULTS_ROOT))


def tracked_fiche_registry_dir_from_env() -> Path:
    """The tracked fiche registry promotion copies cited fiches into.

    `FICHE_REGISTRY_DIR` is where a run writes them; by default the two are
    the same directory and the copy finds every file already there.
    """
    load_dotenv()
    return Path(
        os.environ.get("TRACKED_FICHE_REGISTRY_DIR", DEFAULT_FICHE_REGISTRY_DIR)
    )


def load_settings() -> Settings:
    """Load settings from the environment (`.env` included), validating paths exist.

    `MISTRAL_API_KEY` and `GOOGLE_API_KEY` are read but not required here: the
    runtime-only harness (`__init__.py`) must keep working with no cloud
    credential configured at all. The quality CLI validates each at its own
    point of use: a missing key, or a provider absent from
    `QUALITY_PROVIDERS`, skips that provider's batch rather than aborting.
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
    judge_probe_reference_path = Path(
        os.environ.get("JUDGE_PROBE_REFERENCE_PATH", DEFAULT_JUDGE_PROBE_REFERENCE_PATH)
    )
    roster_entry_id = os.environ.get("ROSTER_ENTRY_ID", DEFAULT_ROSTER_ENTRY_ID)
    mistral_api_key = os.environ.get("MISTRAL_API_KEY", "")
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    quality_providers = _parse_quality_providers(
        os.environ.get("QUALITY_PROVIDERS", DEFAULT_QUALITY_PROVIDERS)
    )

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
    # Absent means `None`: the run profile decides. Present is an operator
    # override, validated so an out-of-range value names its reason.
    host_n_cpu_moe = (
        None
        if os.environ.get("SERVER_N_CPU_MOE") is None
        else _require_numeric(
            "SERVER_N_CPU_MOE",
            0,
            int,
            minimum=0,
            minimum_reason="--n-cpu-moe cannot offload a negative number of experts",
        )
    )
    # Required run inputs with no default (Methodology 21: "never as a
    # fallback"); validated by `require_run_profile`, not here, so a command
    # that writes no row still loads.
    machine_id = os.environ.get("MACHINE_ID") or None
    compute_mode = os.environ.get("COMPUTE_MODE") or None
    campaign_id = os.environ.get("CAMPAIGN_ID") or None
    campaigns_dir = Path(os.environ.get("CAMPAIGNS_DIR", DEFAULT_CAMPAIGNS_DIR))
    machine_results_root = machine_results_root_from_env()
    host_threads = (
        None
        if os.environ.get("SERVER_THREADS") is None
        else _require_numeric(
            "SERVER_THREADS",
            1,
            int,
            minimum=1,
            minimum_reason="-t needs at least one thread",
        )
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
    kwh_price_eur = _require_numeric(
        "KWH_PRICE_EUR",
        DEFAULT_KWH_PRICE_EUR,
        float,
        minimum=0.0,
        minimum_reason="a kWh price cannot be negative",
    )
    kwh_price_recorded_at = os.environ.get(
        "KWH_PRICE_RECORDED_AT", DEFAULT_KWH_PRICE_RECORDED_AT
    )
    mistral_request_pacing_s = _require_numeric(
        "MISTRAL_REQUEST_PACING_S",
        DEFAULT_MISTRAL_REQUEST_PACING_S,
        float,
        minimum=0.0,
        minimum_reason="a pacing interval cannot be negative",
    )
    google_request_pacing_s = _require_numeric(
        "GOOGLE_REQUEST_PACING_S",
        DEFAULT_GOOGLE_REQUEST_PACING_S,
        float,
        minimum=0.0,
        minimum_reason="a pacing interval cannot be negative",
    )
    cloud_retry_min_retries = _require_numeric(
        "CLOUD_RETRY_MIN_RETRIES",
        DEFAULT_CLOUD_RETRY_MIN_RETRIES,
        int,
        # Zero would let a small batch refuse every retry: not "no retry
        # configuration" but a batch that gives up on its first 429.
        minimum=1,
        minimum_reason="every batch must be allowed at least one retry",
    )
    cloud_retry_retries_per_item = _require_numeric(
        "CLOUD_RETRY_RETRIES_PER_ITEM",
        DEFAULT_CLOUD_RETRY_RETRIES_PER_ITEM,
        float,
        minimum=0.0,
        minimum_reason="a per-item retry rate cannot be negative",
    )
    if not math.isfinite(cloud_retry_retries_per_item):
        raise SettingsError(
            f"CLOUD_RETRY_RETRIES_PER_ITEM={cloud_retry_retries_per_item!r} is "
            "not finite: a retry budget is a whole number of retries"
        )
    contested_ordinal_max_delta = _require_numeric(
        "CONTESTED_ORDINAL_MAX_DELTA",
        DEFAULT_CONTESTED_ORDINAL_MAX_DELTA,
        int,
        minimum=0,
        minimum_reason="a contested threshold cannot be negative",
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
        google_api_key=google_api_key,
        quality_providers=quality_providers,
        runtime_repetitions=runtime_repetitions,
        runtime_cooldown_s=runtime_cooldown_s,
        runtime_warmup_count=runtime_warmup_count,
        runtime_spread_threshold=runtime_spread_threshold,
        host_n_cpu_moe=host_n_cpu_moe,
        host_threads=host_threads,
        machine_id=machine_id,
        compute_mode=compute_mode,
        campaign_id=campaign_id,
        campaigns_dir=campaigns_dir,
        machine_results_root=machine_results_root,
        runtime_reference_path=runtime_reference_path,
        quality_reference_path=quality_reference_path,
        judge_probe_reference_path=judge_probe_reference_path,
        runtime_reproduction_tolerance=runtime_reproduction_tolerance,
        emission_country_iso_code=emission_country_iso_code,
        emission_region=emission_region,
        emission_factor_kg_per_kwh=emission_factor_kg_per_kwh,
        scope3_wh_per_token=scope3_wh_per_token,
        kwh_price_eur=kwh_price_eur,
        kwh_price_recorded_at=kwh_price_recorded_at,
        mistral_request_pacing_s=mistral_request_pacing_s,
        google_request_pacing_s=google_request_pacing_s,
        cloud_retry_min_retries=cloud_retry_min_retries,
        cloud_retry_retries_per_item=cloud_retry_retries_per_item,
        contested_ordinal_max_delta=contested_ordinal_max_delta,
    )


@dataclass(frozen=True)
class RunProfile:
    """The declared machine and the compute mode one run is executed under."""

    machine: machines.MachineEntry
    compute_mode: str

    @property
    def machine_id(self) -> str:
        return self.machine.machine_id


def require_run_profile(settings: Settings) -> RunProfile:
    """The run's machine and mode, or `SettingsError` naming what is wrong.

    Called by every row-writing CLI right after `load_settings`, before the
    roster, the build probe, the fiche or any process: a run with no machine
    id, an undeclared one, no compute mode, an unknown one, or `gpu` on a
    machine declared GPU-less never starts a server.
    """
    try:
        registry = machines.tracked_registry()
    except machines.MachineRegistryError as exc:
        raise SettingsError(f"the machine registry cannot be read: {exc}") from exc
    declared = ", ".join(sorted(registry.entries))
    if settings.machine_id is None:
        raise SettingsError(
            f"MACHINE_ID is not set: a run names the declared machine it runs "
            f"on (declared: {declared})"
        )
    if settings.machine_id not in registry.entries:
        raise SettingsError(
            f"MACHINE_ID={settings.machine_id!r} is not a declared machine "
            f"(declared: {declared})"
        )
    modes = " or ".join(machines.COMPUTE_MODES)
    if settings.compute_mode is None:
        raise SettingsError(
            f"COMPUTE_MODE is not set: a run declares {modes}, never a default"
        )
    if settings.compute_mode not in machines.COMPUTE_MODES:
        raise SettingsError(
            f"COMPUTE_MODE={settings.compute_mode!r} is not a compute mode ({modes})"
        )
    machine = registry.entries[settings.machine_id]
    if settings.compute_mode == machines.COMPUTE_MODE_GPU and not machine.gpu_present:
        raise SettingsError(
            f"COMPUTE_MODE=gpu on machine {machine.machine_id!r}, which is "
            "declared to have no GPU: run it as cpu_only"
        )
    return RunProfile(machine=machine, compute_mode=settings.compute_mode)


def _parse_quality_providers(raw: str) -> frozenset[str]:
    """Parse a comma list of provider names, rejecting anything unrecognised.

    Raises `SettingsError` naming the unknown entries rather than silently
    ignoring a typo (`QUALITY_PROVIDERS=locale,mistral` would otherwise run
    with no local batch and no error).
    """
    names = frozenset(name.strip() for name in raw.split(",") if name.strip())
    unknown = names - KNOWN_QUALITY_PROVIDERS
    if unknown:
        raise SettingsError(
            f"QUALITY_PROVIDERS names unrecognised provider(s): "
            f"{', '.join(sorted(unknown))} -- must be drawn from "
            f"{', '.join(sorted(KNOWN_QUALITY_PROVIDERS))}"
        )
    return names


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
