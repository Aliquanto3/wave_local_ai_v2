import copy
import dataclasses
import json
import re
from datetime import date
from pathlib import Path

import pytest
from store_fixtures import ROSTER_REQUIREMENTS

from wave_local_ai_v2 import engines, profiles, roster, server
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
    "requirements": ROSTER_REQUIREMENTS,
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
}

DENSE_ENTRY = {
    "repo": "fake/dense-repo",
    "revision": "main",
    "display_id": "Fake Dense",
    "file": "dense.gguf",
    "quant": "Q4_K_M",
    "sha256": "b" * 64,
    "requirements": ROSTER_REQUIREMENTS,
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
    # The host-fitted values are run profile data, not roster data.
    assert not hasattr(entry, "validated_host")


def _profile(
    entry: roster.RosterEntry, n_cpu_moe: int | None, mode: str
) -> profiles.ResolvedProfile:
    """A resolved profile carrying `n_cpu_moe` under `mode`, for the host-fit check."""
    return profiles.ResolvedProfile(
        profile_id=profiles.profile_id_for(entry.entry_id, "test-machine", mode),
        entry_id=entry.entry_id,
        machine_id="test-machine",
        compute_mode=mode,
        n_gpu_layers=0 if mode == "cpu_only" else 99,
        n_cpu_moe=n_cpu_moe,
        threads=8,
    )


def test_validate_host_fit_passes_at_or_below_the_expert_ceiling(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    # 37 <= expert_count (40)
    roster.validate_host_fit(entry, _profile(entry, 37, "gpu"))


def test_validate_host_fit_passes_when_moe_entry_gets_no_n_cpu_moe(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    roster.validate_host_fit(entry, _profile(entry, None, "gpu"))


def test_validate_host_fit_refuses_a_dense_entry_given_any_n_cpu_moe(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, DENSE_ENTRY_ID)

    with pytest.raises(RosterError, match=DENSE_ENTRY_ID):
        roster.validate_host_fit(entry, _profile(entry, 1, "gpu"))


def test_validate_host_fit_refuses_an_moe_entry_over_its_expert_ceiling(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    with pytest.raises(RosterError, match="40"):
        roster.validate_host_fit(entry, _profile(entry, 41, "gpu"))


def test_validate_host_fit_refuses_any_n_cpu_moe_under_cpu_only_naming_the_mode(
    roster_path: Path,
) -> None:
    loaded = roster.load_roster(roster_path)
    entry = roster.resolve_entry(loaded, MOE_ENTRY_ID)

    roster.validate_host_fit(entry, _profile(entry, None, "cpu_only"))
    for value in (0, 37):
        with pytest.raises(RosterError, match="cpu_only"):
            roster.validate_host_fit(entry, _profile(entry, value, "cpu_only"))


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
        ("server_flags", "sampler", "server_flags.sampler"),
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


@pytest.mark.parametrize("block", ["architecture", "server_flags"])
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

    # server.build_flags's validated command under the laptop gpu run
    # profile, with the flags that are run profile or host settings rather
    # than roster data stripped out: the model path (-m), --n-cpu-moe,
    # -t/threads, and --host/--port.
    dummy_model_path = Path("dummy.gguf")
    profile = profiles.resolve_for_run(
        entry,
        "laptop-mobile-gpu",
        "gpu",
        operator_n_cpu_moe=None,
        operator_threads=None,
    )
    host_n_cpu_moe = profile.n_cpu_moe
    host_threads = profile.threads
    full_flags = server.build_flags(entry, profile, dummy_model_path)
    host_or_model_flag_pairs = {
        ("-m", str(dummy_model_path)),
        ("--n-cpu-moe", str(host_n_cpu_moe)),
        ("-t", str(host_threads)),
        ("--host", engines.tracked_reference_engine().host),
        ("--port", str(engines.tracked_reference_engine().default_port)),
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
    assert not hasattr(entry, "validated_host")


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
    # a version the file has moved past. 5: `validated_host` moved into the
    # run profile registry. 6: the per-mode `requirements`. 7: Granite 4.0 H
    # 350M entered the ~0.5B class from its candidate-gate pass record. 8:
    # LFM2.5-1.2B-Instruct and Granite 3.1 1B-A400M entered the ~2B class. 9:
    # Granite 3.1 3B-A800M entered the ~4B class.
    assert loaded.roster_version == 9
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

    assert len(loaded.entries) == 8
    for entry in loaded.entries.values():
        assert entry.licence is not None, entry.entry_id
        assert entry.language_claim is not None, entry.entry_id
        # Each term is read at the entry's own pinned revision (the flagship's
        # is `main`, its read date standing in for the sha), except a claim
        # the GGUF repository's card does not state: that one is read off the
        # base model's card, pinned at its own sha.
        claim_root = LANGUAGE_CLAIM_FROM_BASE_CARD.get(
            entry.entry_id,
            f"https://huggingface.co/{entry.repo}/blob/{entry.revision}/",
        )
        assert entry.licence.source_url.startswith(
            f"https://huggingface.co/{entry.repo}/blob/{entry.revision}/"
        ), entry.entry_id
        assert entry.language_claim.source_url.startswith(claim_root), entry.entry_id


def test_every_shipped_qwen_entry_declares_the_qwen_thinking_control() -> None:
    # The control these four entries already ran under, now declared rather
    # than assumed: every published row's rendered prompt stays reproducible.
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    qwen = [
        entry
        for entry in loaded.entries.values()
        if roster.family_of(entry.display_id, entry) == "qwen"
    ]

    assert len(qwen) == 4
    for entry in qwen:
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


# The non-Qwen families of the ~0.5B, ~2B and ~4B classes, entered from their
# candidate-gate pass records; written out for the same reason as the Qwen
# ladder above.
SHIPPED_SECOND_FAMILY_ENTRIES: dict[str, dict[str, object]] = {
    "granite-4.0-h-350m-q8": {
        "repo": "ibm-granite/granite-4.0-h-350m-GGUF",
        "revision": "a864f823cce6e6048b5752e2816fe7a23987d790",  # pragma: allowlist secret
        "file": "granite-4.0-h-350m/granite-4.0-h-350m-Q8_0.gguf",
        "display_id": "Granite-4.0-H-350M",
        "quant": "Q8_0",
        "sha256": "c7d9873640dc303b6773dcc44e72e5bdf533e1c95ca8421e6191fbff5c94c942",  # pragma: allowlist secret
        "active_params_b": 0.34,
        "family": "ibm",
        "kind": "dense",
        "expert_count": 0,
    },
    "lfm2.5-1.2b-instruct-q8": {
        "repo": "LiquidAI/LFM2.5-1.2B-Instruct-GGUF",
        "revision": "8ed288026e23958ad9dfa92d53ed773a8eee7125",  # pragma: allowlist secret
        "file": "LFM2.5-1.2B-Instruct/LFM2.5-1.2B-Instruct-Q8_0.gguf",
        "display_id": "LFM2.5-1.2B-Instruct",
        "quant": "Q8_0",
        "sha256": "f6b981dcb86917fa463f78a362320bd5e2dc45445df147287eedb85e5a30d26a",  # pragma: allowlist secret
        "active_params_b": 1.17,
        "family": "liquid",
        "kind": "dense",
        "expert_count": 0,
    },
    "granite-3.1-1b-a400m-instruct-q8": {
        "repo": "bartowski/granite-3.1-1b-a400m-instruct-GGUF",
        "revision": "940d2e1f9f65330615c7c8e980e6c5ac73d3360c",  # pragma: allowlist secret
        "file": "granite-3.1-1b-a400m-instruct/granite-3.1-1b-a400m-instruct-Q8_0.gguf",
        "display_id": "Granite-3.1-1B-A400M-Instruct",
        "quant": "Q8_0",
        "sha256": "724302357c718bbfb4574e4c99b27d8814c8338b0873b062bf410111d1417650",  # pragma: allowlist secret
        "active_params_b": 0.4,
        "family": "ibm",
        "kind": "moe",
        "expert_count": 32,
    },
    "granite-3.1-3b-a800m-instruct-q4km": {
        "repo": "bartowski/granite-3.1-3b-a800m-instruct-GGUF",
        "revision": "be9a36f042806cb586bc65556c527079782b78e0",  # pragma: allowlist secret
        "file": "granite-3.1-3b-a800m-instruct/granite-3.1-3b-a800m-instruct-Q4_K_M.gguf",
        "display_id": "Granite-3.1-3B-A800M-Instruct",
        "quant": "Q4_K_M",
        "sha256": "48e0edcd578fd4462f26127f04c651d0e650741110185297741089aea01a82b3",  # pragma: allowlist secret
        "active_params_b": 0.8,
        "family": "ibm",
        "kind": "moe",
        "expert_count": 40,
    },
}

# The GGUF repository's card states no languages, so the claim is read off the
# base model's card at its own pinned sha.
LANGUAGE_CLAIM_FROM_BASE_CARD = {
    "granite-4.0-h-350m-q8": (
        "https://huggingface.co/ibm-granite/granite-4.0-h-350m/blob/"
        "3b17b717b8f2f5d305b0a92c1491e239aeda19c8/"  # pragma: allowlist secret
    ),
    "lfm2.5-1.2b-instruct-q8": (
        "https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct/blob/"
        "0f604ada3f766f9f257460c4c9f0b5d6f69d431b/"  # pragma: allowlist secret
    ),
    "granite-3.1-1b-a400m-instruct-q8": (
        "https://huggingface.co/ibm-granite/granite-3.1-1b-a400m-instruct/blob/"
        "0da7a48b0276d500ce5922fd2b33944091fc6c09/"  # pragma: allowlist secret
    ),
    "granite-3.1-3b-a800m-instruct-q4km": (
        "https://huggingface.co/ibm-granite/granite-3.1-3b-a800m-instruct/blob/"
        "a02780686e08a03fe0d2679a293b5c74a90efa89/"  # pragma: allowlist secret
    ),
}


def test_the_shipped_roster_holds_the_qwen_ladder_and_the_second_family() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)

    assert set(loaded.entries) == {
        "qwen3.6-35b-a3b-ud-iq4xs",
        *SHIPPED_DENSE_ENTRIES,
        *SHIPPED_SECOND_FAMILY_ENTRIES,
    }


@pytest.mark.parametrize("entry_id", sorted(SHIPPED_SECOND_FAMILY_ENTRIES))
def test_each_second_family_entry_matches_docs_setup_and_its_gguf_kind(
    entry_id: str,
) -> None:
    expected = SHIPPED_SECOND_FAMILY_ENTRIES[entry_id]
    entry = roster.resolve_entry(roster.load_roster(REAL_ROSTER_PATH), entry_id)
    setup = Path("docs/setup.md").read_text(encoding="utf-8")

    for field in ("repo", "revision", "file", "display_id", "quant", "sha256"):
        assert getattr(entry, field) == expected[field], field
    assert entry.architecture.active_params_b == expected["active_params_b"]
    # Declared in the file, so it resolves without the in-code fallback.
    assert entry.family == expected["family"]
    assert roster.family_of(entry.display_id, entry) == expected["family"]
    # A model that does not reason: verified by the gate's one generation.
    assert entry.thinking_control == roster.THINKING_CONTROL_NONE
    # The kind and expert count the gate read off the GGUF header.
    assert entry.architecture.kind == expected["kind"]
    assert entry.architecture.expert_count == expected["expert_count"]
    assert entry.entry_id not in profiles.tracked_registry().entries
    assert entry.server_flags["load_mode"] == "auto"
    assert entry.server_flags["context_size"] == 32768
    # `docs/setup.md` publishes the download at the pinned sha and the hash.
    assert f"--revision {entry.revision}" in setup
    assert entry.sha256 in setup


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
    # No profile declares an expert offload for a dense entry.
    assert entry.entry_id not in profiles.tracked_registry().entries
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
    "granite-4.0-h-350m-q8": ("~0.5B", 340_332_224, 366_195_616),
    "lfm2.5-1.2b-instruct-q8": ("~2B", 1_170_340_608, 1_246_253_888),
    "granite-3.1-1b-a400m-instruct-q8": ("~2B", 1_334_628_352, 1_422_239_776),
    "granite-3.1-3b-a800m-instruct-q4km": ("~4B", 3_298_793_472, 2_016_888_384),
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
    # No class is a labelled ladder. The ~0.5B class spans two families and
    # records its MoE search, the ~2B and ~4B classes hold their MoE; the top
    # class's search belongs to its own per-class story (order 8).
    loaded = roster.load_roster(REAL_ROSTER_PATH)

    assert tuple(loaded.size_classes) == roster.SIZE_CLASSES
    for size_class, declaration in loaded.size_classes.items():
        assert declaration.single_family_ladder is False
        if size_class != "~0.5B":
            assert declaration.moe_absent_reason is None
    assert loaded.size_classes["~8B-and-up"].moe_entry == "qwen3.6-35b-a3b-ud-iq4xs"


def test_the_half_billion_class_records_its_moe_search_and_spans_two_families() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    declaration = loaded.size_classes["~0.5B"]
    families = {
        roster.family_of(entry.display_id, entry)
        for entry in loaded.entries.values()
        if entry.size_class == "~0.5B"
    }

    assert families == {"ibm", "qwen"}
    assert declaration.moe_sought is True
    assert declaration.moe_entry is None
    assert declaration.moe_absent_reason is not None
    assert declaration.moe_absent_reason.startswith("sought, none found")


def test_the_two_billion_class_spans_three_families_and_holds_its_moe() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    declaration = loaded.size_classes["~2B"]
    members = [entry for entry in loaded.entries.values() if entry.size_class == "~2B"]

    assert {roster.family_of(entry.display_id, entry) for entry in members} == {
        "ibm",
        "liquid",
        "qwen",
    }
    # Granite 3.1 1B-A400M entered as `moe` off its GGUF header, so the
    # declaration names it rather than an absence reason.
    assert declaration.moe_sought is True
    assert declaration.moe_entry == "granite-3.1-1b-a400m-instruct-q8"
    assert declaration.moe_absent_reason is None
    assert {entry.architecture.kind for entry in members} == {"dense", "moe"}


def test_the_four_billion_class_spans_two_families_and_holds_its_moe() -> None:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    declaration = loaded.size_classes["~4B"]
    members = [entry for entry in loaded.entries.values() if entry.size_class == "~4B"]

    assert {roster.family_of(entry.display_id, entry) for entry in members} == {
        "ibm",
        "qwen",
    }
    # Granite 3.1 3B-A800M entered as `moe` off its GGUF header, at the Qwen
    # entry's quant, so the declaration names it rather than an absence reason.
    assert declaration.moe_sought is True
    assert declaration.moe_entry == "granite-3.1-3b-a800m-instruct-q4km"
    assert declaration.moe_absent_reason is None
    assert {entry.architecture.kind for entry in members} == {"dense", "moe"}
    assert {entry.quant for entry in members} == {"Q4_K_M"}
