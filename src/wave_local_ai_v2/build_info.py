"""Runtime version and commit provenance for the running code.

`version()` reads the version the installed distribution was built with —
the same value `pyproject.toml`'s `[project].version` declares, resolved
through `importlib.metadata` so there is no second hardcoded copy that can
drift.

`commit_sha()` resolves the commit the running code was built from, in
order: an injected `WAVE_BUILD_SHA` environment variable (set by the
container build, where there is no git checkout at runtime), then
`git rev-parse HEAD` asked of the checkout this module itself lives in
(a dev or CI checkout), then `None`. The git query is anchored on this
file's own directory rather than the caller's working directory, so a
non-editable install answers `None` instead of reporting whatever
repository the caller happened to be standing in. The degradation is
deliberate: when neither surface is available, the function returns
`None` rather than a stale or fabricated value.
"""

import os
import shutil
import subprocess
from importlib.metadata import version as _installed_version
from pathlib import Path

_DISTRIBUTION_NAME = "wave-local-ai-v2"
_PACKAGE_DIR = Path(__file__).resolve().parent


def version() -> str:
    """Return the installed distribution's version."""
    return _installed_version(_DISTRIBUTION_NAME)


def commit_sha() -> str | None:
    """Return the commit sha the running code was built from, or None."""
    injected = os.environ.get("WAVE_BUILD_SHA")
    if injected:
        return injected

    git_binary = shutil.which("git")
    if git_binary is None:
        return None

    try:
        result = subprocess.run(
            [git_binary, "-C", str(_PACKAGE_DIR), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None

    sha = result.stdout.strip()
    return sha or None
