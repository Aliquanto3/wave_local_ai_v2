"""Second, independent byte-identical check: the shipped roster file's
content, and `server.build_flags`'s output built from it, against the
original validated source document (`context_input/baseline_qwen36.md`), not
against `test_server.py`'s own prior assertion.

`test_server.py::test_build_flags_matches_baseline` guards `server.py`'s
behavior against its own prior test. This file guards the roster file's
shipped content against the hand-written baseline command in
`context_input/baseline_qwen36.md`'s "Commande retenue" section, transcribed
below as a literal constant -- not imported from `server.py` -- so this test
cannot pass by construction.
"""

from __future__ import annotations

from pathlib import Path

from wave_local_ai_v2 import profiles, roster, server
from wave_local_ai_v2.settings import Settings

REAL_ROSTER_PATH = Path("aidd_docs/roster/models.json")
REAL_PROFILES_PATH = Path("aidd_docs/roster/profiles.json")
REAL_ROSTER_ENTRY_ID = "qwen3.6-35b-a3b-ud-iq4xs"
# The flagship's validated launch is its laptop `gpu` run profile.
REAL_MACHINE_ID = "laptop-mobile-gpu"
REAL_COMPUTE_MODE = "gpu"


def _default_settings() -> Settings:
    """`Settings` with only its three required paths given: everything else default.

    The three paths are irrelevant here; what matters is that the operator
    overrides `host_n_cpu_moe` / `host_threads` are in their shipped default
    (unset) state, so the launch values come from the resolved run profile
    rather than from literals written into this test.
    """
    placeholder = Path("unused")
    return Settings(
        slm_models_dir=placeholder,
        llama_server_path=placeholder,
        results_path=placeholder,
    )


# Hand-transcribed, field for field, from context_input/baseline_qwen36.md's
# "Commande retenue" section:
#
#   llama-server -m <gguf> -ngl 99 --n-cpu-moe 37 -c 32768 -fa on -t 8 --jinja -np 1
#     --load-mode none --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0
#     --presence-penalty 1.5 --host 127.0.0.1 --port 8080
#
# `<gguf>` is a placeholder in the source document; the test substitutes its
# own placeholder path for `-m`'s value below.
BASELINE_FLAGS = [
    "-m",
    "<gguf>",
    "-ngl",
    "99",
    "--n-cpu-moe",
    "37",
    "-c",
    "32768",
    "-fa",
    "on",
    "-t",
    "8",
    "--jinja",
    "-np",
    "1",
    "--load-mode",
    "none",
    "--temp",
    "1.0",
    "--top-p",
    "0.95",
    "--top-k",
    "20",
    "--min-p",
    "0",
    "--presence-penalty",
    "1.5",
    "--host",
    "127.0.0.1",
    "--port",
    "8080",
]


def _resolved_profile(
    entry: roster.RosterEntry, settings: Settings
) -> profiles.ResolvedProfile:
    """The shipped (flagship, laptop, gpu) profile, under the default settings."""
    return profiles.resolve(
        profiles.load_registry(REAL_PROFILES_PATH),
        entry,
        REAL_MACHINE_ID,
        REAL_COMPUTE_MODE,
        operator_n_cpu_moe=settings.host_n_cpu_moe,
        operator_threads=settings.host_threads,
    )


def test_shipped_roster_entry_reproduces_the_baseline_command() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, REAL_ROSTER_ENTRY_ID)
    settings = _default_settings()

    placeholder_path = Path("<gguf>")
    flags = server.build_flags(
        entry,
        _resolved_profile(entry, settings),
        model_path=placeholder_path,
    )

    assert flags == BASELINE_FLAGS


def test_host_defaults_equal_the_shipped_entrys_validated_host() -> None:
    """The other half of the claim: the defaults are the values it was validated under.

    `test_shipped_roster_entry_reproduces_the_baseline_command` proves the
    defaults reproduce the source document's command; this proves the
    default settings override nothing, so the values launched are the
    resolved profile's own, and those are the baseline's `--n-cpu-moe 37`
    and `-t 8` -- the two can't drift apart silently either.
    """
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, REAL_ROSTER_ENTRY_ID)
    settings = _default_settings()
    profile = _resolved_profile(entry, settings)

    assert settings.host_n_cpu_moe is None
    assert settings.host_threads is None
    assert profile.overrides == {}
    assert profile.n_cpu_moe == int(
        BASELINE_FLAGS[BASELINE_FLAGS.index("--n-cpu-moe") + 1]
    )
    assert profile.threads == int(BASELINE_FLAGS[BASELINE_FLAGS.index("-t") + 1])
