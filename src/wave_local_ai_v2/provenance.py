"""Run-level code/tree provenance: release version, commit sha, tree dirtiness.

`capture_provenance()` is meant to be called exactly once per CLI invocation,
its result spread into every row that run writes -- so every row of one run
names the exact code and tree state that produced it. Degradation is
deliberate and matches `build_info.py`'s contract: when git is unavailable or
its invocation fails, `commit_sha` and `tree_dirty` resolve to explicit `None`
rather than a stale or fabricated value. `release_version` never degrades to
`None` -- the packaged version is always resolvable once the distribution is
installed, independent of git; the fallback is visible in the value itself
(a `+untagged` suffix) rather than a silent flag a reader has to cross-reference.
"""

from __future__ import annotations

from typing import Any

from wave_local_ai_v2 import build_info


def commit_sha() -> str | None:
    """Return the commit sha the running code was built from, or None."""
    return build_info.commit_sha()


def tree_dirty() -> bool | None:
    """Return whether tracked files differ from HEAD, or None if git is unavailable.

    Untracked files never count: only a `git status --porcelain` line whose
    first two characters are not `??` marks the tree dirty.
    """
    status = build_info._run_git(
        ["-C", str(build_info._PACKAGE_DIR), "status", "--porcelain"]
    )
    if status is None:
        return None
    return any(line[:2] != "??" for line in status.splitlines())


def release_version() -> str:
    """Return the exact tag at HEAD, or the packaged version with a '+untagged' suffix.

    Never returns None: the fallback degrades to a visible marker in the value
    itself rather than a separate flag a reader must cross-reference.
    """
    tag = build_info._run_git(
        [
            "-C",
            str(build_info._PACKAGE_DIR),
            "describe",
            "--tags",
            "--exact-match",
            "HEAD",
        ]
    )
    if tag:
        return tag
    return f"{build_info.version()}+untagged"


def capture_provenance() -> dict[str, Any]:
    """Resolve release_version/commit_sha/tree_dirty once for the whole run."""
    return {
        "release_version": release_version(),
        "commit_sha": commit_sha(),
        "tree_dirty": tree_dirty(),
    }
