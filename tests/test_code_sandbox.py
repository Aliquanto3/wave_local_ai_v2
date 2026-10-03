"""The code sandbox: Docker only, capped and offline, or a refusal.

The Docker binary is never run by the unit tests here: `subprocess.run`
and `shutil.which` are substituted, so they prove the command the runner
would launch and every refusal path without a container runtime.

The harness tests run the in-container harness itself, unchanged, on
test-authored planted solutions only (never a model's output), to prove a
solution that exits 0 before its tests ran is not a pass. The planted runs
inside a real container are `test_planted_generations_in_the_real_sandbox`,
which runs only when `CODE_SANDBOX_IT=1` and a local Python image is named.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import code_sandbox, row_contract

# Captured at import, before the autouse fixture substitutes the fake.
_REAL_ACTIVE_RUNNER = code_sandbox.active_runner

_IMAGES = {"python": "py-image", "javascript": "node-image"}
_IMAGE_ID = "sha256:feed"


class _Docker:
    """A stand-in for the docker CLI: records calls, answers by subcommand."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.inputs: list[str | None] = []
        self.answers: dict[str, Any] = {"image": (0, f"{_IMAGE_ID}\n", "")}

    def __call__(self, args: list[str], **kwargs: Any) -> Any:
        self.calls.append(args)
        self.inputs.append(kwargs.get("input"))
        answer = self.answers.get(args[1], (0, "", ""))
        if isinstance(answer, BaseException):
            raise answer
        returncode, stdout, stderr = answer
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    def run_call(self) -> list[str]:
        return next(call for call in self.calls if call[1] == "run")


@pytest.fixture
def docker(monkeypatch: pytest.MonkeyPatch) -> _Docker:
    fake = _Docker()
    monkeypatch.setattr(code_sandbox.shutil, "which", lambda name: "/bin/docker")
    monkeypatch.setattr(code_sandbox.subprocess, "run", fake)
    return fake


def test_no_container_runtime_refuses_in_one_line_and_runs_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(code_sandbox.shutil, "which", lambda name: None)
    monkeypatch.setattr(code_sandbox.subprocess, "run", lambda *a, **k: calls.append(a))
    runner = code_sandbox.DockerSandbox(_IMAGES)

    with pytest.raises(code_sandbox.SandboxUnavailable) as refusal:
        runner.check_available(("python", "javascript"))
    with pytest.raises(code_sandbox.SandboxUnavailable):
        runner.run("python", "print('planted')", "def test_x(): pass")

    assert "no container runtime" in str(refusal.value)
    assert "never run on the host" in str(refusal.value)
    assert "\n" not in str(refusal.value)
    assert calls == []


def test_an_unreachable_daemon_refuses(docker: _Docker) -> None:
    docker.answers["info"] = (1, "", "Cannot connect to the Docker daemon\n")

    with pytest.raises(code_sandbox.SandboxUnavailable, match="not reachable"):
        code_sandbox.DockerSandbox(_IMAGES).check_available(("python",))


@pytest.mark.parametrize("answer", [(1, "", "No such image"), (0, "\n", "")])
def test_a_missing_image_refuses_and_is_never_pulled(
    docker: _Docker, answer: tuple[int, str, str]
) -> None:
    docker.answers["image"] = answer

    with pytest.raises(code_sandbox.SandboxUnavailable, match="never pulled"):
        code_sandbox.DockerSandbox(_IMAGES).check_available(("javascript",))

    assert not any("pull" in call for call in docker.calls)


def test_an_available_sandbox_resolves_every_tagged_image_once(
    docker: _Docker,
) -> None:
    runner = code_sandbox.DockerSandbox(_IMAGES)
    runner.check_available(("python", "javascript"))
    runner.describe("python")

    inspected = [call[-1] for call in docker.calls if call[1] == "image"]
    assert inspected == ["py-image", "node-image"]


def test_the_container_runs_the_resolved_id_offline_unmounted_and_capped(
    docker: _Docker,
) -> None:
    command = code_sandbox.DockerSandbox(_IMAGES).command("javascript", "n")

    def value(flag: str) -> str:
        return command[command.index(flag) + 1]

    assert value("--network") == "none"
    assert value("--pull") == "never"
    assert value("--memory") == value("--memory-swap") == "256m"
    assert value("--pids-limit") == "64"
    assert value("--user") == "65534:65534"
    assert value("--entrypoint") == "node"
    assert "--read-only" in command and "--rm" in command
    assert not {"-v", "--volume", "--mount", "--privileged"} & set(command)
    assert command[command.index(_IMAGE_ID) + 1] == "-e"


def test_describe_is_the_sandbox_block_a_row_records(docker: _Docker) -> None:
    block = code_sandbox.DockerSandbox(_IMAGES).describe("python")

    assert set(block) == row_contract.SANDBOX_FIELDS
    assert block["network"] == "none" and block["host_mount"] is False
    assert (block["image"], block["image_id"]) == ("py-image", _IMAGE_ID)


@pytest.mark.parametrize(
    ("stdout", "returncode", "status"),
    [
        ('noise\n{"status": "passed", "detail": ""}\n', 0, "passed"),
        ('{"status": "compile_error", "detail": "SyntaxError"}', 0, "compile_error"),
        ('{"status": "tests_failed", "detail": "x"}', 0, "tests_failed"),
        ('{"status": "timeout", "detail": "x"}', 0, "timeout"),
        ('{"status": "forged"}', 0, "tests_failed"),
        ("not json", 1, "tests_failed"),
        ("", 137, "tests_failed"),
    ],
)
def test_the_run_reads_only_the_harness_verdict(
    docker: _Docker, stdout: str, returncode: int, status: str
) -> None:
    docker.answers["run"] = (returncode, stdout, "killed")

    outcome = code_sandbox.DockerSandbox(_IMAGES).run("python", "x = 1", "t")

    assert outcome.status == status
    sent = docker.run_call()
    assert sent[-2:] == ["-c", sent[-1]] and sent[-3] == _IMAGE_ID


def test_every_run_sends_a_fresh_nonce_and_the_watchdog_cap(docker: _Docker) -> None:
    runner = code_sandbox.DockerSandbox(_IMAGES)
    runner.run("python", "x = 1", "t")
    runner.run("python", "x = 1", "t")

    payloads = [json.loads(sent) for sent in docker.inputs if sent is not None]
    assert len({payload["nonce"] for payload in payloads}) == 2
    assert {payload["timeout_s"] for payload in payloads} == {
        code_sandbox.WALL_CLOCK_CAP_S
    }


def test_a_run_the_watchdog_did_not_end_is_a_timeout_and_its_container_removed(
    docker: _Docker,
) -> None:
    docker.answers["run"] = subprocess.TimeoutExpired("docker", 35)

    outcome = code_sandbox.DockerSandbox(_IMAGES).run("python", "while 1: pass", "t")

    assert outcome.status == code_sandbox.STATUS_TIMEOUT
    run = docker.run_call()
    name = run[run.index("--name") + 1]
    assert docker.calls[-2:] == [
        ["/bin/docker", "kill", name],
        ["/bin/docker", "rm", "-f", name],
    ]


def test_a_container_that_cannot_start_refuses_rather_than_scores(
    docker: _Docker,
) -> None:
    docker.answers["run"] = (125, "", "docker: error during connect\n")

    with pytest.raises(code_sandbox.SandboxUnavailable, match="not run anywhere"):
        code_sandbox.DockerSandbox(_IMAGES).run("python", "x = 1", "t")


def test_images_come_from_the_environment_or_the_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODE_SANDBOX_NODE_IMAGE", "local-node")
    monkeypatch.delenv("CODE_SANDBOX_PYTHON_IMAGE", raising=False)

    images = code_sandbox.DockerSandbox().images

    assert images == {"python": "python:3.12-slim", "javascript": "local-node"}


def test_the_active_runner_is_the_docker_sandbox() -> None:
    assert isinstance(_REAL_ACTIVE_RUNNER(), code_sandbox.DockerSandbox)


# --- the harness: an early exit 0 is never a pass -------------------------------

_PY_TESTS = "from solution import f\n\n\ndef test_f():\n    assert f() == 1\n"
_PY_CORRECT = "def f():\n    return 1\n"
_PY_WRONG = "def f():\n    return 2\n"
_PY_PLANTED = [
    (_PY_CORRECT, "passed"),
    (_PY_WRONG, "tests_failed"),
    ("def f(:\n", "compile_error"),
    (_PY_WRONG + "import sys\nsys.exit(0)\n", "tests_failed"),
    (_PY_WRONG + "exit()\n", "tests_failed"),
    (_PY_WRONG + "import os\nos._exit(0)\n", "tests_failed"),
]

_JS_TESTS = (
    'import { test } from "node:test";\n'
    'import assert from "node:assert/strict";\n'
    'import { f } from "./solution.mjs";\n\n'
    'test("f", () => {\n  assert.equal(f(), 1);\n});\n'
)
_JS_CORRECT = "export function f() {\n  return 1;\n}\n"
_JS_WRONG = "export function f() {\n  return 2;\n}\n"
_JS_PLANTED = [
    (_JS_CORRECT, "passed"),
    (_JS_WRONG, "tests_failed"),
    ("export function f( {\n", "compile_error"),
    (_JS_WRONG + "process.exit(0);\n", "tests_failed"),
]


def _harness(
    interpreter: list[str], tmp_path: Path, solution: str, tests: str
) -> dict[str, Any]:
    payload = {"solution": solution, "tests": tests, "nonce": "n0nce", "timeout_s": 20}
    completed = subprocess.run(
        interpreter,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
        check=False,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(("solution", "status"), _PY_PLANTED)
def test_the_python_harness_passes_only_when_every_test_ran(
    tmp_path: Path, solution: str, status: str
) -> None:
    command = [sys.executable, "-c", code_sandbox._PYTHON_HARNESS]

    assert _harness(command, tmp_path, solution, _PY_TESTS)["status"] == status


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node on PATH")
@pytest.mark.parametrize(("solution", "status"), _JS_PLANTED)
def test_the_node_harness_passes_only_when_every_test_ran(
    tmp_path: Path, solution: str, status: str
) -> None:
    command = ["node", "-e", code_sandbox._NODE_HARNESS]

    assert _harness(command, tmp_path, solution, _JS_TESTS)["status"] == status


# --- inside a real container ---------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("CODE_SANDBOX_IT") != "1",
    reason="needs a Docker daemon and a local Python image (CODE_SANDBOX_IT=1)",
)
@pytest.mark.parametrize(
    ("solution", "status"),
    [
        *_PY_PLANTED,
        (
            "import socket\nsocket.create_connection(('1.1.1.1', 80), 3)\n"
            + _PY_CORRECT,
            "tests_failed",
        ),
        ("open('/etc/planted', 'w').write('x')\n" + _PY_CORRECT, "tests_failed"),
    ],
)
def test_planted_generations_in_the_real_sandbox(solution: str, status: str) -> None:
    runner = code_sandbox.DockerSandbox()
    runner.check_available(("python",))

    assert runner.run("python", solution, _PY_TESTS).status == status
    left = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=wave-sandbox-", "-q"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert left.stdout.strip() == ""
