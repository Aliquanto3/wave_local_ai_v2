import copy
import json
import re
from pathlib import Path

import pytest

from wave_local_ai_v2 import roster, server
from wave_local_ai_v2.roster import RosterError

MOE_ENTRY_ID = "fake-moe-model"
DENSE_ENTRY_ID = "fake-dense-model"

MOE_ENTRY = {
    "repo": "fake/moe-repo",
    "revision": "main",
    "display_id": "Fake MoE",
    "file": "moe.gguf",
    "quant": "UD-IQ4_XS",
    "sha256": "a" * 64,
    "architecture": {
        "kind": "moe",
        "expert_count": 40,
        "active_params_b": 3.1,
    },
    "server_flags": {
        "n_gpu_layers": 99,
        "context_size": 32768,
        "flash_attention": "on",
        "jinja": True,
        "parallel_slots": 1,
        "load_mode": "none",
        "sampler": {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0,
            "presence_penalty": 1.5,
        },
    },
    "validated_host": {
        "n_cpu_moe": 37,
        "threads": 8,
        "fiche_summary": "fake fiche",
    },
}

DENSE_ENTRY = {
    "repo": "fake/dense-repo",
    "revision": "main",
    "display_id": "Fake Dense",
    "file": "dense.gguf",
    "quant": "Q4_K_M",
    "sha256": "b" * 64,
    "architecture": {
        "kind": "dense",
        "expert_count": 0,
        "active_params_b": 7.0,
    },
    "server_flags": {
        "n_gpu_layers": 99,
        "context_size": 8192,
        "flash_attention": "on",
        "jinja": True,
        "parallel_slots": 1,
        "load_mode": "none",
        "sampler": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "min_p": 0.05,
            "presence_penalty": 0.0,
        },
    },
    "validated_host": {
        "n_cpu_moe": None,
        "threads": 8,
        "fiche_summary": "fake fiche",
    },
}


def _write_roster(path: Path, entries: dict) -> Path:
    path.write_text(json.dumps({"roster_version": 3, "entries": entries}))
    return path


@pytest.fixture
def roster_path(tmp_path) -> Path:
    return _write_roster(
        tmp_path / "roster.json",
        {MOE_ENTRY_ID: MOE_ENTRY, DENSE_ENTRY_ID: DENSE_ENTRY},
    )


def test_load_roster_reads_a_well_formed_file(roster_path: Path) -> None:
    loaded = roster.load_roster(roster_path)

    assert loaded.roster_version == 3
    assert set(loaded.entries) == {MOE_ENTRY_ID, DENSE_ENTRY_ID}


def test_resolve_entry_returns_the_entry_whose_fields_match_the_file(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)

    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    assert entry.repo == MOE_ENTRY["repo"]
    assert entry.revision == MOE_ENTRY["revision"]
    assert entry.file == MOE_ENTRY["file"]
    assert entry.quant == MOE_ENTRY["quant"]
    assert entry.sha256 == MOE_ENTRY["sha256"]
    assert entry.architecture.kind == "moe"
    assert entry.architecture.expert_count == 40
    assert entry.architecture.active_params_b == 3.1
    assert entry.server_flags == MOE_ENTRY["server_flags"]
    assert entry.validated_host == MOE_ENTRY["validated_host"]


def test_validate_host_fit_passes_at_or_below_the_expert_ceiling(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    roster.validate_host_fit(entry, n_cpu_moe=37)  # 37 <= expert_count (40)


def test_validate_host_fit_passes_when_moe_entry_gets_no_n_cpu_moe(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    roster.validate_host_fit(entry, n_cpu_moe=None)


def test_validate_host_fit_refuses_a_dense_entry_given_any_n_cpu_moe(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, DENSE_ENTRY_ID)

    with pytest.raises(RosterError, match=DENSE_ENTRY_ID):
        roster.validate_host_fit(entry, n_cpu_moe=1)


def test_validate_host_fit_refuses_an_moe_entry_over_its_expert_ceiling(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    with pytest.raises(RosterError, match="40"):
        roster.validate_host_fit(entry, n_cpu_moe=41)


def test_resolve_entry_raises_on_an_unknown_id(roster_path: Path) -> None:
    loaded = roster.load_roster(roster_path)

    with pytest.raises(RosterError, match="does-not-exist"):
        roster.resolve_entry(loaded, "does-not-exist")


def test_load_roster_refuses_a_checksum_less_entry(tmp_path) -> None:
    broken_entry = {k: v for k, v in MOE_ENTRY.items() if k != "sha256"}
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: broken_entry})

    with pytest.raises(RosterError, match="sha256"):
        roster.load_roster(path)


def test_load_roster_refuses_an_entry_missing_any_other_required_field(
    tmp_path,
) -> None:
    broken_entry = {k: v for k, v in MOE_ENTRY.items() if k != "architecture"}
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: broken_entry})

    with pytest.raises(RosterError, match="architecture"):
        roster.load_roster(path)


@pytest.mark.parametrize(
    ("block", "field", "expected_path"),
    [
        ("architecture", "expert_count", "architecture.expert_count"),
        ("server_flags", "context_size", "server_flags.context_size"),
        ("validated_host", "threads", "validated_host.threads"),
    ],
)
def test_load_roster_names_the_dotted_path_of_a_missing_nested_field(
    tmp_path, block: str, field: str, expected_path: str
) -> None:
    broken_entry = copy.deepcopy(MOE_ENTRY)
    del broken_entry[block][field]
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: broken_entry})

    with pytest.raises(RosterError, match=re.escape(expected_path)):
        roster.load_roster(path)


def test_load_roster_names_the_dotted_path_of_a_missing_sampler_field(
    tmp_path,
) -> None:
    broken_entry = copy.deepcopy(MOE_ENTRY)
    del broken_entry["server_flags"]["sampler"]["top_p"]
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: broken_entry})

    with pytest.raises(RosterError, match=re.escape("server_flags.sampler.top_p")):
        roster.load_roster(path)


def test_an_entry_missing_context_size_is_refused_at_load_not_at_flag_build(
    tmp_path,
) -> None:
    """The regression this validation exists for.

    Before nested validation, such an entry passed `load_roster` and failed
    inside `server.build_flags` with a bare `KeyError` that neither CLI's
    `main()` catches -- a traceback where every other roster failure is a
    one-line operator message.
    """
    broken_entry = copy.deepcopy(MOE_ENTRY)
    del broken_entry["server_flags"]["context_size"]
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: broken_entry})

    with pytest.raises(RosterError, match=re.escape("server_flags.context_size")):
        roster.load_roster(path)


@pytest.mark.parametrize(
    "bad_sha256",
    ["", "abc", "A" * 64, "g" * 64, "a" * 63, "a" * 65, 649],
)
def test_load_roster_refuses_a_malformed_checksum(tmp_path, bad_sha256) -> None:
    broken_entry = copy.deepcopy(MOE_ENTRY)
    broken_entry["sha256"] = bad_sha256
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: broken_entry})

    with pytest.raises(RosterError, match="sha256"):
        roster.load_roster(path)


@pytest.mark.parametrize("bad_version", ["1", 1.5, True, None])
def test_load_roster_refuses_a_non_integer_roster_version(
    tmp_path, bad_version
) -> None:
    path = tmp_path / "roster.json"
    path.write_text(
        json.dumps(
            {"roster_version": bad_version, "entries": {MOE_ENTRY_ID: MOE_ENTRY}}
        )
    )

    with pytest.raises(RosterError, match="roster_version"):
        roster.load_roster(path)


@pytest.mark.parametrize("block", ["architecture", "server_flags", "validated_host"])
def test_load_roster_refuses_a_block_that_is_not_an_object(
    tmp_path, block: str
) -> None:
    broken_entry = copy.deepcopy(MOE_ENTRY)
    broken_entry[block] = "not an object"
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: broken_entry})

    with pytest.raises(RosterError, match=block):
        roster.load_roster(path)


REAL_ROSTER_PATH = Path("aidd_docs/roster/models.json")


def test_shipped_roster_entry_matches_the_validated_baseline_flags() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, "qwen3.6-35b-a3b-ud-iq4xs")

    # server.build_flags's validated command, with the flags that are now
    # host settings rather than roster data stripped out: the model path
    # (-m), --n-cpu-moe, -t/threads, and --host/--port.
    dummy_model_path = Path("dummy.gguf")
    host_n_cpu_moe = entry.validated_host["n_cpu_moe"]
    host_threads = entry.validated_host["threads"]
    full_flags = server.build_flags(
        entry, host_n_cpu_moe, host_threads, dummy_model_path
    )
    host_or_model_flag_pairs = {
        ("-m", str(dummy_model_path)),
        ("--n-cpu-moe", str(host_n_cpu_moe)),
        ("-t", str(host_threads)),
        ("--host", server.HOST),
        ("--port", str(server.PORT)),
    }
    stripped_flags: list[str] = []
    i = 0
    while i < len(full_flags):
        flag = full_flags[i]
        if flag == "--jinja":
            stripped_flags.append(flag)
            i += 1
            continue
        pair = (flag, full_flags[i + 1])
        if pair not in host_or_model_flag_pairs:
            stripped_flags.extend(pair)
        i += 2

    assert roster.build_flags_from_entry(entry) == stripped_flags


def test_shipped_roster_entry_matches_docs_setup_step_3() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, "qwen3.6-35b-a3b-ud-iq4xs")

    assert entry.repo == "unsloth/Qwen3.6-35B-A3B-GGUF"
    assert entry.revision == "main"
    assert entry.file == "Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf"
    assert entry.display_id == "Qwen3.6-35B-A3B"
    assert entry.quant == "UD-IQ4_XS"
    assert (
        entry.sha256
        == "649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3"  # pragma: allowlist secret
    )
    assert entry.architecture.kind == "moe"
    assert entry.architecture.expert_count == 40
    assert entry.validated_host == {
        "n_cpu_moe": 37,
        "threads": 8,
        "fiche_summary": entry.validated_host["fiche_summary"],
    }
