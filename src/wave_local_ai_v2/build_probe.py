"""Read the llama.cpp build id a running server binary actually reports.

`probe_build` never raises: any subprocess failure or unparseable version
banner yields `None`, an explicit null rather than an assumed value
(plan.md's Decisions table: "a build that cannot be read is an explicit
null, never an assumed value").
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# A few seconds is generous for a local `--version` invocation; long enough to
# absorb a slow disk/AV scan on first launch, short enough that a hung binary
# does not stall the run.
VERSION_PROBE_TIMEOUT_S = 5.0

_BUILD_PATTERN = re.compile(r"build (\d+)")


def probe_build(server_path: Path) -> str | None:
    """Run `server_path --version` and extract its build id from stderr.

    Verified live on this machine (plan.md's Resources table): the b10537
    binary prints its version banner to stderr with exit code 0 and empty
    stdout, e.g. "version: 0.1.2-dev (build 10537, commit bf0040e15)".
    Returns `f"b{n}"` on a match (the `LLAMA_CPP_BUILD` convention this
    replaces), `None` on an unparseable banner or any subprocess failure --
    never raises.
    """
    try:
        result = subprocess.run(
            [str(server_path), "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    match = _BUILD_PATTERN.search(result.stderr)
    if match is None:
        return None
    return f"b{match.group(1)}"
