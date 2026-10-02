"""The candidate gate: seven steps, first failure stops, one record per run.

The hub, the download and the server are stubbed, and every stub counts its
calls, so "a refusal stops every later step" is asserted on what was never
called, not on the order the code happens to be written in.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from wave_local_ai_v2 import candidate_gate as gate
from wave_local_ai_v2 import roster, server

SHA = "23749fefcc72300e3a2ad315e1317431b06b590a"  # pragma: allowlist secret
REPO = "Qwen/Qwen3-0.6B-GGUF"
REPO_FILE = "Qwen3-0.6B-Q8_0.gguf"
NOW = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
CONTROL = {"chat_template_kwargs": {"enable_thinking": False}}
APACHE_TEXT = "Apache License Version 2.0. You may reproduce and distribute copies."
FORBIDDING = (
    "Model Terms. You may not publish or disclose the results of any benchmark "
    "of the Model without prior written consent. Other terms apply."
)


def _s(text: str) -> bytes:
    data = text.encode()
    return struct.pack("<Q", len(data)) + data


def _gguf(
    *,
    arch: str | None = "qwen3",
    expert_count: int | None = None,
    tensors: tuple[tuple[int, ...], ...] = ((4, 3), (5,)),
    version: int = 3,
    extra_kv: bytes = b"",
) -> bytes:
    kvs = []
    if arch is not None:
        kvs.append(_s("general.architecture") + struct.pack("<I", 8) + _s(arch))
    kvs.append(_s("general.file_type") + struct.pack("<II", 4, 7))
    kvs.append(
        _s("tokenizer.ggml.tokens")
        + struct.pack("<II", 9, 8)
        + struct.pack("<Q", 2)
        + _s("a")
        + _s("b")
    )
    if expert_count is not None:
        kvs.append(_s(f"{arch}.expert_count") + struct.pack("<II", 4, expert_count))
    body = b"".join(kvs) + extra_kv
    count = len(kvs) + (1 if extra_kv else 0)
    out = b"GGUF" + struct.pack("<IQQ", version, len(tensors), count) + body
    for index, dims in enumerate(tensors):
        out += _s(f"t{index}") + struct.pack("<I", len(dims))
        out += struct.pack(f"<{len(dims)}Q", *dims) + struct.pack("<IQ", 0, 0)
    return out


GGUF_BYTES = _gguf()


def _declaration(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "entry_id": "qwen3-0.6b-q8",
        "repo": REPO,
        "revision": SHA,
        "repo_file": REPO_FILE,
        "file": f"Qwen3-0.6B/{REPO_FILE}",
        "display_id": "Qwen3-0.6B",
        "quant": "Q8_0",
        "family": "qwen",
        "thinking_control": CONTROL,
        "active_params_b": 0.6,
        "client_commercial_use": True,
        "language_claim": {
            "languages": [],
            "source_url": f"https://huggingface.co/{REPO}/blob/{SHA}/README.md",
            "statement": "Support of 100+ languages and dialects.",
        },
        "server_flags": {
            "n_gpu_layers": 99,
            "context_size": 32768,
            "flash_attention": "on",
            "jinja": True,
            "parallel_slots": 1,
            "load_mode": "auto",
            "sampler": {
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0,
                "presence_penalty": 1.5,
            },
        },
        "validated_host": {
            "n_cpu_moe": None,
            "threads": 8,
            "fiche_summary": "Consumer NVIDIA laptop GPU, ~6 GB VRAM, Windows",
        },
    }
    raw.update(overrides)
    return raw


class FakeHub:
    def __init__(
        self,
        *,
        files: dict[str, int | None] | None = None,
        licence_id: str | None = "apache-2.0",
        commit: str = SHA,
        text: str = APACHE_TEXT,
        missing: bool = False,
        text_missing: bool = False,
    ) -> None:
        self.files = (
            files
            if files is not None
            else {REPO_FILE: len(GGUF_BYTES), "LICENSE": 10, "README.md": 5}
        )
        self.licence_id = licence_id
        self.commit = commit
        self.text = text
        self.missing = missing
        self.text_missing = text_missing
        self.listing_calls = 0
        self.text_calls: list[str] = []

    def listing(self, repo: str, revision: str) -> gate.RepoListing:
        self.listing_calls += 1
        if self.missing:
            raise gate.HubNotFound(f"the hub answers 404 for {repo}@{revision}")
        return gate.RepoListing(
            commit=self.commit, files=self.files, licence_id=self.licence_id
        )

    def read_text(self, repo: str, revision: str, path: str) -> str:
        self.text_calls.append(path)
        if self.text_missing:
            raise gate.HubNotFound(f"the hub answers 404 for {path}")
        return self.text


class Stubs:
    """Every seam, each counting its calls."""

    def __init__(self, hub: FakeHub | None = None) -> None:
        self.hub = hub or FakeHub()
        self.payload: bytes | None = GGUF_BYTES
        self.download_error: str | None = None
        self.free = 10**12
        self.build: str | None = "b10537"
        self.port_busy = False
        self.startup_error: str | None = None
        self.download_calls = 0
        self.disk_calls = 0
        self.launch_calls = 0
        self.launched_flags: list[str] = []

    def download(self, repo: str, revision: str, repo_file: str, dest: Path) -> None:
        self.download_calls += 1
        if self.download_error is not None:
            raise gate.DownloadError(self.download_error)
        if self.payload is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(self.payload)

    def disk_free(self, path: Path) -> int:
        self.disk_calls += 1
        return self.free

    @contextmanager
    def launch(self, server_path: Path, flags: list[str]) -> Iterator[object]:
        self.launch_calls += 1
        self.launched_flags = flags
        if self.startup_error is not None:
            raise server.ServerStartupError(self.startup_error)
        yield object()

    def seams(self) -> gate.GateSeams:
        return gate.GateSeams(
            hub=self.hub,
            download=self.download,
            disk_free=self.disk_free,
            probe_build=lambda path: self.build,
            launch=self.launch,
            port_in_use=lambda: self.port_busy,
        )


class Server:
    """The local HTTP stub: `/props`, `/apply-template`, the chat endpoint."""

    def __init__(self) -> None:
        self.template = "{{ messages }} {% if enable_thinking %}{% endif %}"
        self.control_changes_render = True
        self.chat_message: dict[str, Any] = {"role": "assistant", "content": "ready"}
        self.posts: list[str] = []

    def get(self, url: str, timeout: float) -> MagicMock:
        return _response({"chat_template": self.template})

    def post(self, url: str, json: dict[str, Any], timeout: float) -> MagicMock:
        self.posts.append(url)
        if url.endswith("/apply-template"):
            suffix = (
                "<think>\n\n</think>\n\n"
                if "chat_template_kwargs" in json and self.control_changes_render
                else ""
            )
            return _response({"prompt": "<|im_start|>assistant\n" + suffix})
        return _response({"choices": [{"message": self.chat_message}]})


def _response(payload: Any) -> MagicMock:
    return MagicMock(
        status_code=200, json=lambda: payload, raise_for_status=lambda: None
    )


@pytest.fixture
def local() -> Iterator[Server]:
    fake = Server()
    with (
        patch("wave_local_ai_v2.local_client.requests.get", side_effect=fake.get),
        patch("wave_local_ai_v2.local_client.requests.post", side_effect=fake.post),
    ):
        yield fake


def _run(stubs: Stubs, tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    return gate.run_gate(
        gate.parse_candidate(_declaration(**overrides)),
        models_dir=tmp_path,
        server_path=tmp_path / "llama-server.exe",
        host_threads=8,
        seams=stubs.seams(),
        now=NOW,
    )


# --- the pass ---------------------------------------------------------------


def test_a_passing_candidate_carries_every_field_a_roster_entry_requires(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    record = _run(stubs, tmp_path)

    assert record["outcome"] == gate.OUTCOME_PASSED
    assert record["step"] is None and record["evidence"] is None
    entry = record["entry"]
    for key in roster.REQUIRED_FIELDS[""]:
        assert key in entry
    for path, keys in roster.REQUIRED_FIELDS.items():
        block = entry
        for part in filter(None, path.split(".")):
            block = block[part]
        assert all(key in block for key in keys)
    parsed = roster.parse_entry(record["entry_id"], entry)
    assert parsed.family == "qwen"
    assert parsed.thinking_control == CONTROL
    assert parsed.licence is not None and parsed.licence.licence_id == "apache-2.0"
    assert parsed.language_claim is not None
    assert entry["sha256"] == hashlib.sha256(GGUF_BYTES).hexdigest()
    assert entry["architecture"] == {
        "kind": "dense",
        "expert_count": 0,
        "active_params_b": 0.6,
    }
    assert entry["licence"]["source_url"].endswith(f"/blob/{SHA}/LICENSE")
    assert entry["licence"]["read_on"] == "2026-10-02"
    observed = record["observed"]
    assert observed["bytes"] == len(GGUF_BYTES)
    assert observed["total_params"] == 17
    assert observed["llama_cpp_build"] == "b10537"
    assert (
        observed["thinking"]["with_control"] != observed["thinking"]["without_control"]
    )
    assert "--n-cpu-moe" not in stubs.launched_flags
    assert stubs.launch_calls == 1


def test_a_none_declaration_passes_on_a_generation_with_no_reasoning(
    tmp_path: Path, local: Server
) -> None:
    record = _run(Stubs(), tmp_path, thinking_control="none")

    assert record["outcome"] == gate.OUTCOME_PASSED
    assert record["entry"]["thinking_control"] == "none"
    assert any(url.endswith("/v1/chat/completions") for url in local.posts)


def test_an_allowed_declaration_enters_with_no_thinking_control(
    tmp_path: Path, local: Server
) -> None:
    record = _run(Stubs(), tmp_path, thinking_control="allowed")

    assert record["outcome"] == gate.OUTCOME_PASSED
    assert "thinking_control" not in record["entry"]
    assert record["observed"]["thinking"] == {"declared": "allowed", "verified": False}
    assert local.posts == []


def test_a_moe_file_is_classed_from_its_own_metadata(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    stubs.payload = _gguf(arch="qwen3moe", expert_count=128)
    stubs.hub.files[REPO_FILE] = len(stubs.payload)

    record = _run(stubs, tmp_path)

    assert record["entry"]["architecture"]["kind"] == "moe"
    assert record["entry"]["architecture"]["expert_count"] == 128


# --- each step refuses, and nothing after it runs ---------------------------


def _assert_refused(record: dict[str, Any], step: str, *fragments: str) -> None:
    assert record["outcome"] == gate.OUTCOME_REFUSED
    assert record["step"] == step
    assert record["entry"] is None
    assert record["checked_on"] == "2026-10-02"
    for fragment in fragments:
        assert fragment in record["evidence"]


def test_a_branch_revision_is_refused_before_the_hub_is_asked(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    record = _run(stubs, tmp_path, revision="main")

    _assert_refused(record, gate.STEP_REVISION, "'main'", "commit sha")
    assert stubs.hub.listing_calls == 0
    assert stubs.download_calls == 0


@pytest.mark.parametrize(
    ("hub", "fragment"),
    [
        (FakeHub(missing=True), "404"),
        (FakeHub(commit="f" * 40), "resolves"),
        (FakeHub(files={"README.md": 5}), "does not exist"),
    ],
)
def test_a_revision_or_file_the_hub_does_not_hold_is_refused(
    tmp_path: Path, local: Server, hub: FakeHub, fragment: str
) -> None:
    stubs = Stubs(hub)
    record = _run(stubs, tmp_path)

    _assert_refused(record, gate.STEP_REVISION, fragment)
    assert hub.text_calls == []
    assert stubs.disk_calls == 0


def test_a_licence_forbidding_published_benchmarks_refuses_before_any_download(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs(FakeHub(text=FORBIDDING))
    record = _run(stubs, tmp_path)

    _assert_refused(
        record, gate.STEP_LICENCE, "You may not publish or disclose", "/LICENSE"
    )
    assert stubs.disk_calls == 0
    assert stubs.download_calls == 0
    assert stubs.launch_calls == 0


@pytest.mark.parametrize(
    ("hub", "fragment"),
    [
        (FakeHub(licence_id=None), "declares no licence"),
        (FakeHub(files={REPO_FILE: len(GGUF_BYTES)}), "no licence text"),
        (FakeHub(text_missing=True), "404"),
    ],
)
def test_a_licence_that_cannot_be_read_is_refused(
    tmp_path: Path, local: Server, hub: FakeHub, fragment: str
) -> None:
    stubs = Stubs(hub)
    record = _run(stubs, tmp_path)

    _assert_refused(record, gate.STEP_LICENCE, fragment)
    assert stubs.download_calls == 0


def test_the_readme_is_read_when_the_repo_ships_no_licence_file(
    tmp_path: Path, local: Server
) -> None:
    hub = FakeHub(files={REPO_FILE: len(GGUF_BYTES), "README.md": 5})
    record = _run(Stubs(hub), tmp_path)

    assert hub.text_calls == ["README.md"]
    assert record["entry"]["licence"]["source_url"].endswith("/README.md")


def test_too_little_disk_refuses_before_the_download_starts(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    stubs.free = len(GGUF_BYTES) - 1
    record = _run(stubs, tmp_path)

    _assert_refused(record, gate.STEP_DISK, "bytes free", "nothing downloaded")
    assert stubs.download_calls == 0


def test_a_file_the_listing_gives_no_size_for_is_refused_at_the_disk_check(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs(FakeHub(files={REPO_FILE: None, "LICENSE": 1}))
    record = _run(stubs, tmp_path)

    _assert_refused(record, gate.STEP_DISK, "no size")
    assert stubs.disk_calls == 0
    assert stubs.download_calls == 0


def test_a_missing_download_is_refused_and_nothing_is_loaded(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    stubs.payload = None
    record = _run(stubs, tmp_path)

    _assert_refused(record, gate.STEP_DOWNLOAD, "nothing to hash")
    assert "sha256" not in record["observed"]
    assert stubs.launch_calls == 0


@pytest.mark.parametrize(
    ("payload", "error", "fragment"),
    [
        (None, "GET x answered 500", "answered 500"),
        (GGUF_BYTES + b"x", None, "the hub lists"),
        (b"NOPE" + GGUF_BYTES[4:], None, "not a GGUF"),
    ],
)
def test_a_download_that_is_not_the_listed_gguf_is_refused(
    tmp_path: Path,
    local: Server,
    payload: bytes | None,
    error: str | None,
    fragment: str,
) -> None:
    stubs = Stubs()
    stubs.payload = payload
    stubs.download_error = error
    if payload is not None:
        stubs.hub.files[REPO_FILE] = len(GGUF_BYTES)
        if payload.startswith(b"NOPE"):
            stubs.hub.files[REPO_FILE] = len(payload)
    record = _run(stubs, tmp_path)

    _assert_refused(record, gate.STEP_DOWNLOAD, fragment)
    assert stubs.launch_calls == 0


def test_an_architecture_the_build_does_not_implement_is_deferred(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    stubs.payload = _gguf(arch="gemma4")
    stubs.hub.files[REPO_FILE] = len(stubs.payload)
    stubs.startup_error = (
        "llama-server exited early with code 1: main: loading model\n"
        "llama_model_load: error loading model: error loading model "
        "architecture: unknown model architecture: 'gemma4'\n"
        "main: exiting due to model loading error\n"
    )
    record = _run(stubs, tmp_path)

    assert record["outcome"] == gate.OUTCOME_DEFERRED
    assert record["step"] == gate.STEP_LOAD
    assert "'gemma4'" in record["evidence"]
    assert "b10537" in record["evidence"]
    assert "unknown model architecture" in record["evidence"]
    assert local.posts == []


def test_any_other_load_failure_is_refused_naming_architecture_and_build(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    stubs.startup_error = "llama-server exited early with code 1: cudaMalloc failed"
    record = _run(stubs, tmp_path)

    _assert_refused(record, gate.STEP_LOAD, "'qwen3'", "b10537", "cudaMalloc")


def test_a_launch_block_that_does_not_fit_the_file_is_refused_before_a_load(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    host = dict(_declaration()["validated_host"], n_cpu_moe=4)
    record = _run(stubs, tmp_path, validated_host=host)

    _assert_refused(record, gate.STEP_LOAD, "dense")
    assert stubs.launch_calls == 0


def test_an_unreadable_build_or_a_busy_port_records_nothing(
    tmp_path: Path, local: Server
) -> None:
    stubs = Stubs()
    stubs.build = None
    with pytest.raises(gate.GateAborted, match="cannot read the build"):
        _run(stubs, tmp_path)

    stubs = Stubs()
    stubs.port_busy = True
    with pytest.raises(gate.GateAborted, match="already in use"):
        _run(stubs, tmp_path)
    assert stubs.launch_calls == 0


def test_a_control_the_template_ignores_is_refused_and_no_claim_is_recorded(
    tmp_path: Path, local: Server
) -> None:
    local.control_changes_render = False
    # A claim that would itself be refused: step 7 must never be reached.
    record = _run(Stubs(), tmp_path, language_claim={"languages": ["xx"]})

    _assert_refused(record, gate.STEP_THINKING, "byte-identical")
    assert record["observed"]["chat_template_hash"]


@pytest.mark.parametrize(
    "message",
    [
        {"role": "assistant", "content": "ready", "reasoning_content": "Let me think"},
        {"role": "assistant", "content": "<think>hmm</think>ready"},
    ],
)
def test_a_none_declaration_that_reasons_is_refused(
    tmp_path: Path, local: Server, message: dict[str, Any]
) -> None:
    local.chat_message = message
    record = _run(Stubs(), tmp_path, thinking_control="none")

    _assert_refused(record, gate.STEP_THINKING, "returned reasoning")


def test_a_template_the_server_does_not_report_is_refused(
    tmp_path: Path, local: Server
) -> None:
    local.template = ""
    record = _run(Stubs(), tmp_path)

    _assert_refused(record, gate.STEP_THINKING, "chat_template")


@pytest.mark.parametrize(
    ("claim", "fragment"),
    [
        (None, "no language claim"),
        ({"languages": ["en", "en"], "source_url": "u"}, "distinct"),
        ({"languages": ["it"], "source_url": "u"}, "distinct"),
        ({"languages": ["en"], "source_url": " "}, "no source"),
        ({"languages": ["en"], "source_url": "u", "statement": ""}, "empty"),
    ],
)
def test_a_language_claim_without_a_source_or_outside_en_fr_de_is_refused(
    tmp_path: Path, local: Server, claim: Any, fragment: str
) -> None:
    record = _run(Stubs(), tmp_path, language_claim=claim)

    _assert_refused(record, gate.STEP_LANGUAGE, fragment)


def test_a_claim_with_no_statement_records_none(tmp_path: Path, local: Server) -> None:
    claim = {"languages": ["en", "fr"], "source_url": "https://example.org/card"}
    record = _run(Stubs(), tmp_path, language_claim=claim)

    assert record["entry"]["language_claim"] == {
        "languages": ["en", "fr"],
        "source_url": "https://example.org/card",
        "read_on": "2026-10-02",
    }


# --- the declaration, the record file and the command -----------------------


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ([], "JSON object"),
        ({k: v for k, v in _declaration().items() if k != "quant"}, "quant"),
        (_declaration(repo=" "), "'repo'"),
        (_declaration(family="gemma"), "'gemma'"),
        (_declaration(thinking_control={}), "thinking_control"),
        (_declaration(thinking_control="off"), "thinking_control"),
        (_declaration(active_params_b=True), "active_params_b"),
        (_declaration(active_params_b=0), "active_params_b"),
        (_declaration(client_commercial_use="yes"), "client_commercial_use"),
        (_declaration(server_flags={"n_gpu_layers": 99}), "server_flags"),
    ],
)
def test_a_malformed_declaration_is_refused_naming_the_field(
    raw: Any, fragment: str
) -> None:
    with pytest.raises(gate.CandidateError, match=fragment):
        gate.parse_candidate(raw)


def test_a_second_run_on_the_same_candidate_appends(
    tmp_path: Path, local: Server
) -> None:
    records = tmp_path / "roster" / "candidate-records.jsonl"
    stubs = Stubs()
    stubs.free = 0
    gate.append_record(records, _run(stubs, tmp_path))
    gate.append_record(records, _run(Stubs(), tmp_path))

    lines = [json.loads(line) for line in records.read_text("utf-8").splitlines()]
    assert [line["outcome"] for line in lines] == ["refused", "passed"]
    assert {line["entry_id"] for line in lines} == {"qwen3-0.6b-q8"}


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    binary = tmp_path / "llama-server.exe"
    binary.write_bytes(b"")
    monkeypatch.setenv("SLM_MODELS_DIR", str(tmp_path))
    monkeypatch.setenv("LLAMA_SERVER_PATH", str(binary))
    return tmp_path


def _main(tmp_path: Path, declaration: Any, stubs: Stubs) -> tuple[int, Path]:
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(declaration), encoding="utf-8")
    records = tmp_path / "records.jsonl"
    code = gate.main(
        ["--candidate", str(candidate), "--records", str(records)],
        seams=stubs.seams(),
    )
    return code, records


def test_the_command_exits_0_on_a_pass_and_1_on_a_refusal(
    env: Path, local: Server, capsys: pytest.CaptureFixture[str]
) -> None:
    code, records = _main(env, _declaration(), Stubs())
    assert code == 0
    assert "passed" in capsys.readouterr().out

    code, records = _main(env, _declaration(revision="main"), Stubs())
    assert code == 1
    assert "refused at step revision" in capsys.readouterr().out
    assert len(records.read_text("utf-8").splitlines()) == 2


def test_the_gate_never_writes_the_roster_file(env: Path, local: Server) -> None:
    roster_file = Path(roster.__file__).parents[2] / "aidd_docs/roster/models.json"
    before = roster_file.read_bytes()

    _main(env, _declaration(), Stubs())

    assert roster_file.read_bytes() == before


@pytest.mark.parametrize("declaration", [{"repo": "x"}, "not json"])
def test_a_bad_declaration_exits_2_and_records_nothing(
    env: Path, declaration: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    stubs = Stubs()
    if declaration == "not json":
        (env / "candidate.json").write_text("{", encoding="utf-8")
        code = gate.main(
            ["--candidate", str(env / "candidate.json"), "--records", str(env / "r")],
            seams=stubs.seams(),
        )
        records = env / "r"
    else:
        code, records = _main(env, declaration, stubs)

    assert code == 2
    assert not records.exists()
    assert "nothing recorded" in capsys.readouterr().err
    assert stubs.hub.listing_calls == 0


def test_a_missing_server_path_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLM_MODELS_DIR", str(tmp_path))
    monkeypatch.delenv("LLAMA_SERVER_PATH", raising=False)
    code, records = _main(tmp_path, _declaration(), Stubs())

    assert code == 2
    assert not records.exists()


def test_a_host_failure_mid_run_exits_2(env: Path, local: Server) -> None:
    stubs = Stubs()
    stubs.port_busy = True
    code, records = _main(env, _declaration(), stubs)

    assert code == 2
    assert not records.exists()


def test_forbidding_clause_needs_benchmark_publication_and_a_prohibition() -> None:
    assert gate.forbidding_clause(APACHE_TEXT) is None
    assert gate.forbidding_clause("We publish benchmark results. Enjoy.") is None
    assert gate.forbidding_clause(FORBIDDING) == (
        "You may not publish or disclose the results of any benchmark of the "
        "Model without prior written consent."
    )


def test_the_decisive_line_falls_back_to_the_first_line() -> None:
    assert gate._decisive_line("exited early\nsome log") == "exited early"
    assert gate._decisive_line("") == ""


# --- the real seams, HTTP stubbed --------------------------------------------


def _http(status: int, payload: Any = None, text: str = "") -> MagicMock:
    response = MagicMock(status_code=status, text=text)
    response.json.return_value = payload
    return response


def test_the_hub_listing_reads_sizes_commit_and_licence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    payload = {
        "sha": SHA,
        "cardData": {"license": "other", "license_name": "gemma"},
        "siblings": [
            {"rfilename": REPO_FILE, "size": 639446688},
            {"rfilename": "params"},
        ],
    }
    with patch.object(gate.requests, "get", return_value=_http(200, payload)) as get:
        listing = gate.HuggingFaceHub().listing(REPO, SHA)

    assert listing == gate.RepoListing(
        commit=SHA, files={REPO_FILE: 639446688, "params": None}, licence_id="gemma"
    )
    assert get.call_args.kwargs["headers"] == {"Authorization": "Bearer hf_test"}
    assert get.call_args.args[0].endswith(f"/api/models/{REPO}/revision/{SHA}")


def test_the_hub_listing_with_no_licence_reads_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with patch.object(gate.requests, "get", return_value=_http(200, {"sha": SHA})):
        listing = gate.HuggingFaceHub().listing(REPO, SHA)

    assert listing.licence_id is None
    assert listing.files == {}


def test_the_hub_answers_404_as_not_found_and_other_failures_as_aborted() -> None:
    hub = gate.HuggingFaceHub()
    with patch.object(gate.requests, "get", return_value=_http(404)):
        with pytest.raises(gate.HubNotFound):
            hub.listing(REPO, SHA)
        with pytest.raises(gate.HubNotFound):
            hub.read_text(REPO, SHA, "LICENSE")
    with patch.object(gate.requests, "get", return_value=_http(500)):
        with pytest.raises(gate.GateAborted):
            hub.listing(REPO, SHA)
        with pytest.raises(gate.GateAborted):
            hub.read_text(REPO, SHA, "LICENSE")
    with (
        patch.object(gate.requests, "get", side_effect=requests.ConnectionError("x")),
        pytest.raises(gate.GateAborted, match="unreachable"),
    ):
        hub.listing(REPO, SHA)


def test_the_hub_reads_a_text_file_at_the_revision() -> None:
    with patch.object(
        gate.requests, "get", return_value=_http(200, text=APACHE_TEXT)
    ) as get:
        text = gate.HuggingFaceHub().read_text(REPO, SHA, "LICENSE")

    assert text == APACHE_TEXT
    assert get.call_args.args[0].endswith(f"/{REPO}/resolve/{SHA}/LICENSE")


def _streaming(status: int, chunks: list[bytes]) -> MagicMock:
    response = MagicMock(status_code=status)
    response.iter_content.return_value = chunks
    response.__enter__.return_value = response
    return response


def test_a_download_lands_whole_with_no_part_file(tmp_path: Path) -> None:
    dest = tmp_path / "Qwen3-0.6B" / REPO_FILE
    with patch.object(
        gate.requests, "get", return_value=_streaming(200, [b"GG", b"UF"])
    ):
        gate.stream_download(REPO, SHA, REPO_FILE, dest)

    assert dest.read_bytes() == b"GGUF"
    assert list(dest.parent.iterdir()) == [dest]


def test_a_refused_or_broken_download_leaves_nothing(tmp_path: Path) -> None:
    dest = tmp_path / REPO_FILE
    with (
        patch.object(gate.requests, "get", return_value=_streaming(500, [])),
        pytest.raises(gate.DownloadError, match="500"),
    ):
        gate.stream_download(REPO, SHA, REPO_FILE, dest)
    broken = _streaming(200, [])
    broken.iter_content.side_effect = requests.ConnectionError("reset")
    with (
        patch.object(gate.requests, "get", return_value=broken),
        pytest.raises(gate.GateAborted, match="broke off"),
    ):
        gate.stream_download(REPO, SHA, REPO_FILE, dest)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        (b"GGUX" + GGUF_BYTES[4:], "magic"),
        (_gguf(version=1), "version 1"),
        (GGUF_BYTES[:30], "truncated"),
        (_gguf(arch=None), "general.architecture"),
        (_gguf(extra_kv=_s("odd") + struct.pack("<I", 99)), "value type 99"),
    ],
)
def test_an_unreadable_gguf_header_is_named(
    tmp_path: Path, data: bytes, fragment: str
) -> None:
    path = tmp_path / "m.gguf"
    path.write_bytes(data)

    with pytest.raises(gate.GgufError, match=fragment):
        gate.read_gguf_facts(path)


def test_the_default_seams_are_the_real_ones(tmp_path: Path) -> None:
    seams = gate.default_seams()

    assert isinstance(seams.hub, gate.HuggingFaceHub)
    assert seams.download is gate.stream_download
    assert seams.disk_free(tmp_path) > 0
    assert isinstance(seams.port_in_use(), bool)
    context = seams.launch(tmp_path / "llama-server.exe", [])
    assert hasattr(context, "__enter__")


@pytest.mark.parametrize("status", [401, 403])
def test_a_gated_repo_without_a_token_records_nothing(
    tmp_path: Path, status: int
) -> None:
    hub = gate.HuggingFaceHub()
    with patch.object(gate.requests, "get", return_value=_http(status)):
        with pytest.raises(gate.GateAborted, match="HF_TOKEN"):
            hub.listing(REPO, SHA)
        with pytest.raises(gate.GateAborted, match="HF_TOKEN"):
            hub.read_text(REPO, SHA, "LICENSE")
    with (
        patch.object(gate.requests, "get", return_value=_streaming(status, [])),
        pytest.raises(gate.GateAborted, match=f"{status}.*HF_TOKEN"),
    ):
        gate.stream_download(REPO, SHA, REPO_FILE, tmp_path / REPO_FILE)
    assert list(tmp_path.iterdir()) == []


def test_a_gated_download_mid_run_exits_2_and_records_nothing(
    env: Path, local: Server
) -> None:
    stubs = Stubs()
    gated = _streaming(401, [])
    with patch.object(gate.requests, "get", return_value=gated):
        seams = gate.GateSeams(
            hub=stubs.hub,
            download=gate.stream_download,
            disk_free=stubs.disk_free,
            probe_build=lambda path: "b10537",
            launch=stubs.launch,
            port_in_use=lambda: False,
        )
        candidate = env / "candidate.json"
        candidate.write_text(json.dumps(_declaration()), encoding="utf-8")
        records = env / "records.jsonl"
        code = gate.main(
            ["--candidate", str(candidate), "--records", str(records)], seams=seams
        )

    assert code == 2
    assert not records.exists()
    assert stubs.launch_calls == 0
