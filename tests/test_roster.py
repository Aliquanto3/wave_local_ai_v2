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


def test_family_of_resolves_every_model_this_project_names() -> None:
    assert roster.family_of("mistral-small-2603") == "mistral"
    assert roster.family_of("gemini-3.5-flash-lite") == "google"
    assert roster.family_of("Qwen3.6-35B-A3B") == "qwen"


def test_family_of_prefers_the_roster_entrys_own_declaration(tmp_path) -> None:
    path = _write_roster(
        tmp_path / "roster.json", {MOE_ENTRY_ID: {**MOE_ENTRY, "family": "qwen"}}
    )
    entry = roster.resolve_entry(roster.load_roster(path), MOE_ENTRY_ID)

    assert entry.family == "qwen"
    assert roster.family_of("some-unknown-model", entry) == "qwen"


def test_family_of_falls_back_to_the_declaration_when_the_entry_carries_none(
    tmp_path,
) -> None:
    path = _write_roster(tmp_path / "roster.json", {MOE_ENTRY_ID: MOE_ENTRY})
    entry = roster.resolve_entry(roster.load_roster(path), MOE_ENTRY_ID)

    assert entry.family is None
    assert roster.family_of("Qwen3.6-35B-A3B", entry) == "qwen"


def test_family_of_refuses_an_unknown_model_rather_than_defaulting() -> None:
    with pytest.raises(RosterError, match="some-unknown-model"):
        roster.family_of("some-unknown-model")


def test_family_of_refuses_an_entry_declaring_an_unknown_family(tmp_path) -> None:
    path = _write_roster(
        tmp_path / "roster.json", {MOE_ENTRY_ID: {**MOE_ENTRY, "family": "acme"}}
    )
    entry = roster.resolve_entry(roster.load_roster(path), MOE_ENTRY_ID)

    with pytest.raises(RosterError, match="acme"):
        roster.family_of("Qwen3.6-35B-A3B", entry)


def test_the_shipped_moe_entry_still_loads_with_no_family_of_its_own() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, "qwen3.6-35b-a3b-ud-iq4xs")

    # roster_version 2 is the dense ladder's arrival: rows already published
    # carry 1 and are not back-filled, so the assertion follows the file
    # rather than pinning a version the file has moved past.
    assert loaded.roster_version == 2
    assert entry.family is None
    assert roster.family_of(entry.display_id, entry) == "qwen"


# The three dense entries, keyed by entry id, with the identity fields
# `docs/setup.md` publishes. Written out rather than read from the roster so
# the test can disagree with the file: a checksum or a revision edited by
# accident fails here instead of silently launching a different model.
SHIPPED_DENSE_ENTRIES: dict[str, dict[str, object]] = {
    "qwen3-0.6b-q8": {
        "repo": "Qwen/Qwen3-0.6B-GGUF",
        "revision": "23749fefcc72300e3a2ad315e1317431b06b590a",  # pragma: allowlist secret
        "file": "Qwen3-0.6B/Qwen3-0.6B-Q8_0.gguf",
        "display_id": "Qwen3-0.6B",
        "quant": "Q8_0",
        "sha256": "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031",  # pragma: allowlist secret
        "active_params_b": 0.6,
    },
    "qwen3-1.7b-q8": {
        "repo": "Qwen/Qwen3-1.7B-GGUF",
        "revision": "90862c4b9d2787eaed51d12237eafdfe7c5f6077",  # pragma: allowlist secret
        "file": "Qwen3-1.7B/Qwen3-1.7B-Q8_0.gguf",
        "display_id": "Qwen3-1.7B",
        "quant": "Q8_0",
        "sha256": "061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a",  # pragma: allowlist secret
        "active_params_b": 1.7,
    },
    "qwen3-4b-q4km": {
        "repo": "Qwen/Qwen3-4B-GGUF",
        "revision": "bc640142c66e1fdd12af0bd68f40445458f3869b",  # pragma: allowlist secret
        "file": "Qwen3-4B/Qwen3-4B-Q4_K_M.gguf",
        "display_id": "Qwen3-4B",
        "quant": "Q4_K_M",
        "sha256": "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5",  # pragma: allowlist secret
        "active_params_b": 4.0,
    },
}


def test_the_shipped_roster_holds_the_moe_flagship_and_three_dense_entries() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)

    assert set(loaded.entries) == {
        "qwen3.6-35b-a3b-ud-iq4xs",
        *SHIPPED_DENSE_ENTRIES,
    }


@pytest.mark.parametrize("entry_id", sorted(SHIPPED_DENSE_ENTRIES))
def test_each_shipped_dense_entry_matches_docs_setup_step_3(entry_id: str) -> None:
    expected = SHIPPED_DENSE_ENTRIES[entry_id]
    entry = roster.resolve_entry(roster.load_roster(REAL_ROSTER_PATH), entry_id)

    assert entry.repo == expected["repo"]
    assert entry.revision == expected["revision"]
    assert entry.file == expected["file"]
    assert entry.display_id == expected["display_id"]
    assert entry.quant == expected["quant"]
    assert entry.sha256 == expected["sha256"]
    assert entry.architecture.active_params_b == expected["active_params_b"]


@pytest.mark.parametrize("entry_id", sorted(SHIPPED_DENSE_ENTRIES))
def test_each_shipped_dense_entry_carries_no_moe_offload(entry_id: str) -> None:
    """A dense entry's whole point: nothing in it can produce `--n-cpu-moe`.

    `load_mode` is checked alongside because `none` exists on the MoE entry
    only to stop `--n-cpu-moe` mmapping experts from disk -- a dense entry
    inheriting it would be carrying an MoE workaround it has no MoE to work
    around.
    """
    entry = roster.resolve_entry(roster.load_roster(REAL_ROSTER_PATH), entry_id)

    assert entry.architecture.kind == "dense"
    assert entry.architecture.expert_count == 0
    assert entry.validated_host["n_cpu_moe"] is None
    assert entry.server_flags["load_mode"] == "auto"
    # The declared family is what the judged path resolves, so a dense row
    # never falls back to MODEL_FAMILIES for a model id it does not list.
    assert entry.family == "qwen"
    assert roster.family_of(entry.display_id, entry) == "qwen"


@pytest.mark.parametrize("entry_id", sorted(SHIPPED_DENSE_ENTRIES))
def test_each_shipped_dense_entry_publishes_the_suites_context_cap(
    entry_id: str,
) -> None:
    """32768 is what both live suites publish as their context cap on every row.

    An entry launched below it would make that published cap a lie, so the
    value is asserted here rather than left to the operator's `-ngl` probe to
    trade away when a model does not fit.
    """
    entry = roster.resolve_entry(roster.load_roster(REAL_ROSTER_PATH), entry_id)

    assert entry.server_flags["context_size"] == 32768
