import copy
import dataclasses
import json
import re
from datetime import date
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


@pytest.mark.parametrize("family", ["acme", "gemma", "", None, ["qwen"]])
def test_load_roster_refuses_an_entry_declaring_an_unknown_family(
    tmp_path: Path, family: object
) -> None:
    # Refused at load rather than when a row first resolves it: an entry the
    # family guard cannot read never becomes a launchable entry. `gemma` is
    # the model line, not the family (Q11: the family is the vendor).
    path = _write_roster(
        tmp_path / "roster.json", {MOE_ENTRY_ID: {**MOE_ENTRY, "family": family}}
    )

    with pytest.raises(
        RosterError, match=f"{MOE_ENTRY_ID}.*'family' {re.escape(repr(family))}"
    ):
        roster.load_roster(path)


@pytest.mark.parametrize(
    "family", ["qwen", "mistral", "google", "ibm", "liquid", "microsoft"]
)
def test_an_entry_declaring_a_candidate_vendor_family_loads_and_resolves(
    tmp_path: Path, family: str
) -> None:
    path = _write_roster(
        tmp_path / "roster.json", {DENSE_ENTRY_ID: {**DENSE_ENTRY, "family": family}}
    )
    entry = roster.resolve_entry(roster.load_roster(path), DENSE_ENTRY_ID)

    assert roster.family_of(entry.display_id, entry) == family


def test_family_of_still_refuses_a_constructed_entry_with_an_unknown_family(
    tmp_path: Path,
) -> None:
    # The load check does not replace this one: an entry built in code never
    # passes through `load_roster`.
    entry = roster.resolve_entry(
        roster.load_roster(
            _write_roster(tmp_path / "r.json", {MOE_ENTRY_ID: MOE_ENTRY})
        ),
        MOE_ENTRY_ID,
    )

    with pytest.raises(RosterError, match="acme"):
        roster.family_of("Qwen3.6-35B-A3B", dataclasses.replace(entry, family="acme"))


def test_the_shipped_moe_entry_still_loads_with_no_family_of_its_own() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    entry = roster.resolve_entry(loaded, "qwen3.6-35b-a3b-ud-iq4xs")

    # roster_version 2 was the dense ladder's arrival, 3 the licence and
    # language-claim blocks, 4 the size classes and their figures: rows
    # already published carry the version they were produced under and are
    # not back-filled, so the assertion follows the file rather than pinning
    # a version the file has moved past.
    assert loaded.roster_version == 4
    assert entry.family is None
    assert roster.family_of(entry.display_id, entry) == "qwen"


@pytest.mark.parametrize(
    "control",
    [{}, None, "off", ["chat_template_kwargs"], 0],
    ids=["empty_object", "null", "other_string", "list", "number"],
)
def test_load_roster_refuses_a_malformed_thinking_control(
    tmp_path: Path, control: object
) -> None:
    path = _write_roster(
        tmp_path / "roster.json",
        {MOE_ENTRY_ID: {**MOE_ENTRY, "thinking_control": control}},
    )

    with pytest.raises(RosterError, match=f"{MOE_ENTRY_ID}.*'thinking_control'"):
        roster.load_roster(path)


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        (
            {"thinking_control": {"reasoning_effort": "none"}},
            {"reasoning_effort": "none"},
        ),
        ({"thinking_control": "none"}, roster.THINKING_CONTROL_NONE),
        ({}, None),
    ],
    ids=["request_arguments", "none", "undeclared"],
)
def test_a_well_formed_or_absent_thinking_control_loads(
    tmp_path: Path, declared: dict, expected: object
) -> None:
    path = _write_roster(
        tmp_path / "roster.json", {MOE_ENTRY_ID: {**MOE_ENTRY, **declared}}
    )

    entry = roster.resolve_entry(roster.load_roster(path), MOE_ENTRY_ID)

    assert entry.thinking_control == expected


LICENCE = {
    "id": "Apache-2.0",
    "client_commercial_use": True,
    "read_on": "2026-10-02",
    "source_url": "https://huggingface.co/fake/moe-repo/blob/main/LICENSE",
}
LANGUAGE_CLAIM = {
    "languages": ["en", "fr"],
    "source_url": "https://huggingface.co/fake/moe-repo/blob/main/README.md",
    "read_on": "2026-10-02",
    "statement": "Supports English and French.",
}


def _load_moe_with(tmp_path: Path, **blocks: object) -> roster.RosterEntry:
    path = _write_roster(
        tmp_path / "roster.json", {MOE_ENTRY_ID: {**MOE_ENTRY, **blocks}}
    )
    return roster.resolve_entry(roster.load_roster(path), MOE_ENTRY_ID)


def test_a_well_formed_licence_and_language_claim_load(tmp_path: Path) -> None:
    entry = _load_moe_with(tmp_path, licence=LICENCE, language_claim=LANGUAGE_CLAIM)

    assert entry.licence == roster.Licence(
        licence_id="Apache-2.0",
        client_commercial_use=True,
        read_on=date(2026, 10, 2),
        source_url=LICENCE["source_url"],
    )
    assert entry.language_claim == roster.LanguageClaim(
        languages=("en", "fr"),
        source_url=LANGUAGE_CLAIM["source_url"],
        read_on=date(2026, 10, 2),
        statement="Supports English and French.",
    )


def test_absent_blocks_and_an_absent_statement_load_as_none(tmp_path: Path) -> None:
    claim = {key: value for key, value in LANGUAGE_CLAIM.items() if key != "statement"}

    assert _load_moe_with(tmp_path).licence is None
    assert _load_moe_with(tmp_path).language_claim is None
    assert (
        _load_moe_with(tmp_path, language_claim=claim).language_claim.statement is None
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("client_commercial_use", "yes"),
        ("client_commercial_use", 1),
        ("client_commercial_use", None),
        ("read_on", "2 October 2026"),
        ("read_on", "2026-13-01"),
        ("read_on", 20261002),
        ("id", ""),
        ("id", "   "),
        ("id", None),
        ("source_url", ""),
    ],
)
def test_load_roster_refuses_a_malformed_licence_field_naming_it(
    tmp_path: Path, field: str, value: object
) -> None:
    with pytest.raises(RosterError, match=f"{MOE_ENTRY_ID}.*'licence.{field}'"):
        _load_moe_with(tmp_path, licence={**LICENCE, field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("languages", ["en", "es"]),
        ("languages", ["fr", "fr"]),
        ("languages", "en"),
        ("languages", [{"en": True}]),
        ("read_on", "yesterday"),
        ("source_url", None),
        ("statement", ""),
    ],
)
def test_load_roster_refuses_a_malformed_language_claim_field_naming_it(
    tmp_path: Path, field: str, value: object
) -> None:
    with pytest.raises(RosterError, match=f"{MOE_ENTRY_ID}.*'language_claim.{field}'"):
        _load_moe_with(tmp_path, language_claim={**LANGUAGE_CLAIM, field: value})


@pytest.mark.parametrize(
    ("name", "block", "expected"),
    [
        ("licence", "Apache-2.0", "'licence' must be an object"),
        ("language_claim", ["en"], "'language_claim' must be an object"),
        ("licence", {"id": "MIT"}, "licence.client_commercial_use, licence.read_on"),
        ("language_claim", {"languages": []}, "language_claim.source_url"),
    ],
)
def test_load_roster_refuses_a_block_that_is_not_an_object_or_lacks_a_field(
    tmp_path: Path, name: str, block: object, expected: str
) -> None:
    with pytest.raises(RosterError, match=f"{MOE_ENTRY_ID}.*{re.escape(expected)}"):
        _load_moe_with(tmp_path, **{name: block})


def test_every_shipped_entry_carries_a_licence_and_a_language_claim() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)

    assert len(loaded.entries) == 4
    for entry in loaded.entries.values():
        assert entry.licence is not None, entry.entry_id
        assert entry.language_claim is not None, entry.entry_id
        # Each term is read at the entry's own pinned revision (the flagship's
        # is `main`, its read date standing in for the sha).
        for url in (entry.licence.source_url, entry.language_claim.source_url):
            assert url.startswith(
                f"https://huggingface.co/{entry.repo}/blob/{entry.revision}/"
            ), (entry.entry_id, url)


def test_every_shipped_entry_declares_the_qwen_thinking_control() -> None:
    # The control these four entries already ran under, now declared rather
    # than assumed: every published row's rendered prompt stays reproducible.
    loaded = roster.load_roster(REAL_ROSTER_PATH)

    assert loaded.entries
    for entry in loaded.entries.values():
        assert entry.thinking_control == {
            "chat_template_kwargs": {"enable_thinking": False}
        }, entry.entry_id


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


# --------------------------------------------------------------------------
# Size class, its two figures and the per-class declaration (Q10 (a))

DECLARATION = {
    "single_family_ladder": True,
    "moe_sought": True,
    "moe_entry": None,
    "moe_absent_reason": "no MoE GGUF found below 1B",
}


def _load_file(tmp_path: Path, raw: dict) -> roster.RosterFile:
    path = tmp_path / "roster.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return roster.load_roster(path)


@pytest.mark.parametrize(
    ("total_params", "expected"),
    [
        (1, "~0.5B"),
        (999_999_999, "~0.5B"),
        (1_000_000_000, "~2B"),
        (2_999_999_999, "~2B"),
        (3_000_000_000, "~4B"),
        (5_999_999_999, "~4B"),
        (6_000_000_000, "~8B-and-up"),
        (35_000_000_000, "~8B-and-up"),
    ],
)
def test_size_class_for_bands_total_parameters_at_the_q10_edges(
    total_params: int, expected: str
) -> None:
    assert roster.size_class_for(total_params) == expected


def test_size_class_for_refuses_a_negative_count() -> None:
    with pytest.raises(ValueError, match="negative"):
        roster.size_class_for(-1)


def test_the_vocabulary_is_the_bands_names_in_order() -> None:
    assert roster.SIZE_CLASSES == ("~0.5B", "~2B", "~4B", "~8B-and-up")
    edges = [edge for _, edge in roster.SIZE_CLASS_BANDS]
    assert edges == sorted(edges)


def test_a_size_class_and_its_figures_load(tmp_path: Path) -> None:
    architecture = {**MOE_ENTRY["architecture"], "total_params": 34_660_610_688}
    entry = _load_moe_with(
        tmp_path,
        size_class="~8B-and-up",
        bytes_on_disk=17_730_509_792,
        architecture=architecture,
    )

    assert entry.size_class == "~8B-and-up"
    assert entry.bytes_on_disk == 17_730_509_792
    assert entry.architecture.total_params == 34_660_610_688


def test_absent_size_figures_load_as_none(tmp_path: Path) -> None:
    entry = _load_moe_with(tmp_path)

    assert entry.size_class is None
    assert entry.bytes_on_disk is None
    assert entry.architecture.total_params is None


@pytest.mark.parametrize("value", ["8B", "~8b-and-up", None, 4])
def test_load_roster_refuses_a_size_class_outside_the_vocabulary(
    tmp_path: Path, value: object
) -> None:
    with pytest.raises(RosterError, match=f"{MOE_ENTRY_ID}.*'size_class'"):
        _load_moe_with(tmp_path, size_class=value)


@pytest.mark.parametrize("value", [0, -5, 1.5e9, "1000", True, None])
def test_load_roster_refuses_a_figure_that_is_not_a_positive_integer(
    tmp_path: Path, value: object
) -> None:
    with pytest.raises(RosterError, match=f"{MOE_ENTRY_ID}.*'bytes_on_disk'"):
        _load_moe_with(tmp_path, bytes_on_disk=value)
    architecture = {**MOE_ENTRY["architecture"], "total_params": value}
    with pytest.raises(
        RosterError, match=f"{MOE_ENTRY_ID}.*'architecture.total_params'"
    ):
        _load_moe_with(tmp_path, architecture=architecture)


def test_a_size_class_declaration_loads(tmp_path: Path) -> None:
    loaded = _load_file(
        tmp_path,
        {"roster_version": 4, "size_classes": {"~0.5B": DECLARATION}, "entries": {}},
    )

    assert loaded.size_classes == {
        "~0.5B": roster.SizeClassDeclaration(
            single_family_ladder=True,
            moe_sought=True,
            moe_entry=None,
            moe_absent_reason="no MoE GGUF found below 1B",
        )
    }


def test_a_roster_without_declarations_loads_with_none(tmp_path: Path) -> None:
    loaded = _load_file(tmp_path, {"roster_version": 4, "entries": {}})

    assert loaded.size_classes == {}


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        ([], "'size_classes' must be an object"),
        ({"~1B": DECLARATION}, "size class '~1B' is not a size class"),
        ({"~2B": "ladder"}, "size class '~2B' must be an object"),
        (
            {"~2B": {"single_family_ladder": True}},
            "missing field(s): moe_sought, moe_entry, moe_absent_reason",
        ),
        (
            {"~2B": {**DECLARATION, "single_family_ladder": "yes"}},
            "'single_family_ladder' must be a boolean",
        ),
        ({"~2B": {**DECLARATION, "moe_sought": 1}}, "'moe_sought' must be a boolean"),
        (
            {"~2B": {**DECLARATION, "moe_entry": ""}},
            "'moe_entry' must be null or a non-empty string",
        ),
        (
            {"~2B": {**DECLARATION, "moe_absent_reason": "  "}},
            "'moe_absent_reason' must be null or a non-empty string",
        ),
    ],
)
def test_load_roster_refuses_a_malformed_declaration_naming_its_class(
    tmp_path: Path, block: object, expected: str
) -> None:
    with pytest.raises(RosterError, match=re.escape(expected)):
        _load_file(
            tmp_path, {"roster_version": 4, "size_classes": block, "entries": {}}
        )


# Read off the four GGUFs on the dev machine: `stat` for the bytes (the three
# dense ones equal `docs/setup.md` step 3.1's table), the tensor sum of
# `candidate_gate.read_gguf_facts` for the totals.
SHIPPED_FIGURES = {
    "qwen3.6-35b-a3b-ud-iq4xs": ("~8B-and-up", 34_660_610_688, 17_730_509_792),
    "qwen3-0.6b-q8": ("~0.5B", 596_049_920, 639_446_688),
    "qwen3-1.7b-q8": ("~2B", 1_720_574_976, 1_834_426_016),
    "qwen3-4b-q4km": ("~4B", 4_022_468_096, 2_497_280_256),
}


@pytest.mark.parametrize("entry_id", sorted(SHIPPED_FIGURES))
def test_each_shipped_entry_carries_its_class_and_the_figures_read_off_its_file(
    entry_id: str,
) -> None:
    entry = roster.resolve_entry(roster.load_roster(REAL_ROSTER_PATH), entry_id)
    size_class, total_params, bytes_on_disk = SHIPPED_FIGURES[entry_id]

    assert entry.size_class == size_class
    assert entry.architecture.total_params == total_params
    assert entry.bytes_on_disk == bytes_on_disk
    assert roster.size_class_for(total_params) == size_class


def test_the_shipped_roster_declares_every_class_and_labels_none() -> None:
    # Not labelled by this story: the search that would justify a ladder
    # label or a MoE absence belongs to the per-class stories (orders 5-8).
    loaded = roster.load_roster(REAL_ROSTER_PATH)

    assert tuple(loaded.size_classes) == roster.SIZE_CLASSES
    for declaration in loaded.size_classes.values():
        assert declaration.single_family_ladder is False
        assert declaration.moe_absent_reason is None
    assert loaded.size_classes["~8B-and-up"].moe_entry == "qwen3.6-35b-a3b-ud-iq4xs"
