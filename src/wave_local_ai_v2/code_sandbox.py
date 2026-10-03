"""The sandbox generated code runs in, or the refusal to run it at all.

A code-generation item is scored by executing its tests against the code a
model wrote. That code is untrusted, so it only ever runs inside a container
started from the runtime the published image already uses (Docker): no
network, no host mount, a read-only root file system with a small scratch
`tmpfs` as the working directory, an unprivileged user, every capability
dropped, a memory cap, a process cap and a wall-clock cap enforced from the
host. `--pull never` makes an image that is not already present a refusal,
never a download.

There is no host execution path in this module or anywhere else. Where the
runtime is absent, its daemon unreachable or a sandbox image missing,
`check_available` raises `SandboxUnavailable` with one line naming why, and
the suite refuses to start (`scoring_rules.PREFLIGHTS`). A container that
cannot be started mid-batch raises the same error rather than scoring the
item, so a broken sandbox never publishes a zero that is really a refusal.

The runner is a seam (`SandboxRunner`): the scoring rule asks
`active_runner()` for it, so tests substitute a fake and never need Docker.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from functools import cache
from typing import Any, Protocol

RUNTIME = "docker"
PYTHON = "python"
JAVASCRIPT = "javascript"
PROGRAMMING_LANGUAGES = (PYTHON, JAVASCRIPT)

# The caps every sandboxed run is held to, published on every row.
WALL_CLOCK_CAP_S = 20
MEMORY_CAP_MIB = 256
PIDS_CAP = 64
SCRATCH_SIZE_MIB = 16

# Python: the published image's own base. JavaScript: Node, whose built-in
# test runner (`node --test`) needs no compile step and no dependency.
DEFAULT_IMAGES = {PYTHON: "python:3.12-slim", JAVASCRIPT: "node:22-slim"}
IMAGE_ENV = {
    PYTHON: "CODE_SANDBOX_PYTHON_IMAGE",
    JAVASCRIPT: "CODE_SANDBOX_NODE_IMAGE",
}

STATUS_PASSED = "passed"
STATUS_TESTS_FAILED = "tests_failed"
STATUS_COMPILE_ERROR = "compile_error"
STATUS_TIMEOUT = "timeout"

# The host's own deadline: the in-container watchdog stops the tests at
# `WALL_CLOCK_CAP_S`; this grace covers container start and teardown, and the
# host kills and removes the container only if the watchdog did not end it.
_HOST_GRACE_S = 15

# Docker's own exit status when it could not create or start the container.
_DOCKER_RUN_ERROR = 125
_PROBE_TIMEOUT_S = 30
_DETAIL_CHARS = 500

# Runs inside the container only. Reads the payload from stdin, writes the
# solution and its tests into the scratch working directory, refuses code
# that does not compile, then runs the tests in a child process under the
# in-container watchdog (`timeout_s`), so the verdict line is printed by the
# harness, never by the solution.
#
# The child's exit status alone is not a pass: a solution that exits 0 on
# import (`sys.exit(0)`, `os._exit(0)`, Node's `process.exit(0)`) ends the
# child before any test ran. A pass therefore also requires the host's
# one-run `nonce` as proof that the last test was reached: the Python runner
# prints it only after the whole test loop, and Node runs it as a last
# registered test whose `ok` line must appear. The nonce guards against an
# early exit, not against a solution written to read and forge it.
_PYTHON_HARNESS = r"""
import json, subprocess, sys
p = json.load(sys.stdin)
open("solution.py", "w", encoding="utf-8").write(p["solution"])
open("test_solution.py", "w", encoding="utf-8").write(p["tests"])
def out(status, detail=""):
    print(json.dumps({"status": status, "detail": detail[-500:]}))
try:
    compile(p["solution"], "solution.py", "exec")
except (SyntaxError, ValueError) as exc:
    out("compile_error", repr(exc))
    sys.exit(0)
runner = (
    "import sys, test_solution as t\n"
    "names = sorted(n for n in dir(t) if n.startswith('test_'))\n"
    "assert names, 'no test function'\n"
    "for n in names: getattr(t, n)()\n"
    "print(sys.argv[1])\n"
)
try:
    r = subprocess.run(
        [sys.executable, "-c", runner, p["nonce"]],
        capture_output=True, text=True, timeout=p["timeout_s"],
    )
except subprocess.TimeoutExpired:
    out("timeout", "over %ss in the container" % p["timeout_s"])
    sys.exit(0)
lines = r.stdout.strip().splitlines()
reached = bool(lines) and lines[-1] == p["nonce"]
out("passed" if r.returncode == 0 and reached else "tests_failed", r.stdout + r.stderr)
"""

_NODE_HARNESS = r"""
const fs = require("fs"), cp = require("child_process");
const out = (status, detail) =>
  console.log(JSON.stringify({ status, detail: String(detail || "").slice(-500) }));
let raw = "";
process.stdin.on("data", (d) => (raw += d)).on("end", () => {
  const p = JSON.parse(raw);
  const ms = p.timeout_s * 1000;
  const late = () => out("timeout", "over " + p.timeout_s + "s in the container");
  fs.writeFileSync("solution.mjs", p.solution);
  fs.writeFileSync("solution.test.mjs", p.tests +
    '\nimport { test as waveNonceTest } from "node:test";\n' +
    "waveNonceTest(" + JSON.stringify(p.nonce) + ", () => {});\n");
  const c = cp.spawnSync(process.execPath, ["--check", "solution.mjs"],
    { encoding: "utf8", timeout: ms });
  if (c.error) return late();
  if (c.status !== 0) return out("compile_error", c.stderr);
  const t = cp.spawnSync(process.execPath,
    ["--test", "--test-reporter=tap", "solution.test.mjs"],
    { encoding: "utf8", timeout: ms });
  if (t.error) return late();
  const reached = t.stdout.split("\n").some((line) => line === "ok " +
    line.slice(3).split(" ")[0] + " - " + p.nonce);
  out(t.status === 0 && reached ? "passed" : "tests_failed", t.stdout + t.stderr);
});
"""

# The interpreter is the container's entrypoint, set explicitly so an image
# whose own entrypoint is something else (the project's published image runs
# the benchmark CLI) still runs only the harness.
_INTERPRETER = {
    PYTHON: ("python", ("-c", _PYTHON_HARNESS)),
    JAVASCRIPT: ("node", ("-e", _NODE_HARNESS)),
}


class SandboxUnavailable(RuntimeError):
    """The sandbox cannot run: generated code is refused, never run elsewhere."""


@dataclass(frozen=True)
class SandboxOutcome:
    """What one sandboxed run of an item's tests decided."""

    status: str
    detail: str = ""


class SandboxRunner(Protocol):
    def check_available(self, languages: tuple[str, ...]) -> None:
        """Raise `SandboxUnavailable` unless every language can be run."""

    def describe(self, language: str) -> dict[str, Any]:
        """The sandbox and caps a row of `language` records."""

    def run(self, language: str, solution: str, tests: str) -> SandboxOutcome:
        """Run `tests` against `solution` inside the sandbox."""


def _one_line(text: str) -> str:
    return " ".join(text.split())[:_DETAIL_CHARS]


class DockerSandbox:
    """The Docker-backed runner: every run is a fresh, capped container."""

    def __init__(self, images: dict[str, str] | None = None) -> None:
        self.images = dict(images or _images_from_env())
        self._image_ids: dict[str, str] = {}

    def image_id(self, language: str) -> str:
        """The local id the language's image resolves to; never pulled.

        A container runs from this id, and a row records it beside the tag,
        so a retagged image can never stand in for the one that ran.
        """
        if language not in self._image_ids:
            image = self.images[language]
            inspect = subprocess.run(
                [self._docker(), "image", "inspect", "--format", "{{.Id}}", image],
                capture_output=True,
                check=False,
                text=True,
                timeout=_PROBE_TIMEOUT_S,
            )
            if inspect.returncode != 0 or not inspect.stdout.strip():
                raise SandboxUnavailable(
                    f"code-generation suite refused: sandbox image {image!r} for "
                    f"{language} is not present locally and is never pulled "
                    f"(set {IMAGE_ENV[language]} to a local image)"
                )
            self._image_ids[language] = inspect.stdout.strip()
        return self._image_ids[language]

    def _docker(self) -> str:
        docker = shutil.which(RUNTIME)
        if docker is None:
            raise SandboxUnavailable(
                "code-generation suite refused: no container runtime (docker is "
                "not on PATH); generated code is never run on the host"
            )
        return docker

    def check_available(self, languages: tuple[str, ...]) -> None:
        docker = self._docker()
        info = subprocess.run(
            [docker, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            check=False,
            text=True,
            timeout=_PROBE_TIMEOUT_S,
        )
        if info.returncode != 0:
            raise SandboxUnavailable(
                "code-generation suite refused: the docker daemon is not "
                f"reachable ({_one_line(info.stderr)}); generated code is never "
                "run on the host"
            )
        for language in languages:
            self.image_id(language)

    def describe(self, language: str) -> dict[str, Any]:
        return {
            "runtime": RUNTIME,
            "image": self.images[language],
            "image_id": self.image_id(language),
            "network": "none",
            "host_mount": False,
            "wall_clock_cap_s": WALL_CLOCK_CAP_S,
            "memory_cap_mib": MEMORY_CAP_MIB,
            "pids_cap": PIDS_CAP,
        }

    def command(self, language: str, name: str) -> list[str]:
        """The `docker run` argument list for one item: no mount, no network."""
        scratch = f"rw,size={SCRATCH_SIZE_MIB}m,mode=1777"
        entrypoint, arguments = _INTERPRETER[language]
        return [
            self._docker(),
            "run",
            "--rm",
            "-i",
            "--name",
            name,
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            f"/work:{scratch}",
            "--tmpfs",
            f"/tmp:{scratch}",
            "--workdir",
            "/work",
            "--user",
            "65534:65534",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            f"{MEMORY_CAP_MIB}m",
            "--memory-swap",
            f"{MEMORY_CAP_MIB}m",
            "--pids-limit",
            str(PIDS_CAP),
            "--cpus",
            "1",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--entrypoint",
            entrypoint,
            self.image_id(language),
            *arguments,
        ]

    def run(self, language: str, solution: str, tests: str) -> SandboxOutcome:
        name = f"wave-sandbox-{uuid.uuid4().hex[:12]}"
        command = self.command(language, name)
        payload = json.dumps(
            {
                "solution": solution,
                "tests": tests,
                "nonce": uuid.uuid4().hex,
                "timeout_s": WALL_CLOCK_CAP_S,
            }
        )
        try:
            completed = subprocess.run(
                command,
                input=payload,
                capture_output=True,
                check=False,
                text=True,
                encoding="utf-8",
                timeout=WALL_CLOCK_CAP_S + _HOST_GRACE_S,
            )
        except subprocess.TimeoutExpired:
            # The watchdog did not end it and the client is gone; the
            # container may not be. Kill it by name, then remove it.
            for action in (["kill", name], ["rm", "-f", name]):
                subprocess.run(
                    [command[0], *action],
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=_PROBE_TIMEOUT_S,
                )
            return SandboxOutcome(STATUS_TIMEOUT, f"over {WALL_CLOCK_CAP_S}s")
        if completed.returncode == _DOCKER_RUN_ERROR:
            raise SandboxUnavailable(
                "code-generation scoring stopped: the sandbox container could "
                f"not start ({_one_line(completed.stderr)}); the item is not "
                "run anywhere else"
            )
        return _verdict(completed.stdout, completed.stderr, completed.returncode)


def _verdict(stdout: str, stderr: str, returncode: int) -> SandboxOutcome:
    """The harness's last JSON line; anything else is a failed run."""
    lines = stdout.strip().splitlines()
    try:
        verdict = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        verdict = None
    if isinstance(verdict, dict) and verdict.get("status") in {
        STATUS_PASSED,
        STATUS_TESTS_FAILED,
        STATUS_COMPILE_ERROR,
        STATUS_TIMEOUT,
    }:
        return SandboxOutcome(verdict["status"], str(verdict.get("detail", "")))
    # Killed by the memory cap (137) or crashed before the verdict line.
    return SandboxOutcome(
        STATUS_TESTS_FAILED, f"exit {returncode}: {_one_line(stderr)}"
    )


def _images_from_env() -> dict[str, str]:
    return {
        language: os.environ.get(IMAGE_ENV[language]) or DEFAULT_IMAGES[language]
        for language in PROGRAMMING_LANGUAGES
    }


@cache
def active_runner() -> SandboxRunner:
    """The one runner a process scores with; tests substitute a fake."""
    return DockerSandbox()
