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

from wave_local_ai_v2 import roster, server
from wave_local_ai_v2.settings import Settings

REAL_ROSTER_PATH = Path("aidd_docs/roster/models.json")
REAL_ROSTER_ENTRY_ID = "qwen3.6-35b-a3b-ud-iq4xs"


def _default_settings() -> Settings:
    """`Settings` with only its three required paths given: everything else default.

    The three paths are irrelevant here; what matters is that
    `host_n_cpu_moe` / `host_threads` come from the shipped defaults
    (`settings.DEFAULT_HOST_N_CPU_MOE` / `DEFAULT_HOST_THREADS`, the same
    constants `load_settings` falls back to) rather than from literals
    written into this test, so editing a default fails it.
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


def test_shipped_roster_entry_reproduces_the_baseline_command() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, REAL_ROSTER_ENTRY_ID)
    settings = _default_settings()

    placeholder_path = Path("<gguf>")
    flags = server.build_flags(
        entry,
        settings.host_n_cpu_moe,
        settings.host_threads,
        model_path=placeholder_path,
    )

    assert flags == BASELINE_FLAGS


def test_host_defaults_equal_the_shipped_entrys_validated_host() -> None:
    """The other half of the claim: the defaults are the values it was validated under.

    `test_shipped_roster_entry_reproduces_the_baseline_command` proves the
    defaults reproduce the source document's command; this proves they are
    the same values the roster entry itself records as its validated host,
    so the two can't drift apart silently either.
    """
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, REAL_ROSTER_ENTRY_ID)
    settings = _default_settings()

    assert settings.host_n_cpu_moe == entry.validated_host["n_cpu_moe"]
    assert settings.host_threads == entry.validated_host["threads"]
