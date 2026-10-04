"""Write-once storage and lookup for the hardware fiche: a stored, addressable
artifact a row cites by hash rather than something reconstructed from a row.

`registry_dir` defaults to `aidd_docs/results/fiches/` via
`settings.fiche_registry_dir`, never hardcoded in this module.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, TypedDict

from wave_local_ai_v2 import hardware, path_guard, row_contract

# A local `--version` invocation-scale timeout: `git show` reads one blob from
# the local object database, no network involved.
_GIT_SHOW_TIMEOUT_S = 5.0


class FicheVerification(TypedDict):
    """The outcome of re-hashing one stored fiche's own current content."""

    status: Literal["ok", "edited", "missing"]
    changed_fields: list[str]


def write_fiche(fiche: Mapping[str, Any], registry_dir: Path) -> str:
    """Store `fiche` under its content-addressed hash, write-once.

    Writes the **full** fiche (`flags`, the raw evidence field, included) as
    compact JSON -- a stable, deterministic byte encoding, since phase 2's
    validator re-hashes a stored file's own content and depends on it. If
    `registry_dir/<hash>.json` already exists, does nothing: no re-write, no
    duplicate, no error on a second identical fiche written in the same run.
    """
    fiche_hash_value = hardware.fiche_hash(fiche)
    registry_dir.mkdir(parents=True, exist_ok=True)
    path = registry_dir / f"{fiche_hash_value}.json"
    if not path.exists():
        path.write_text(json.dumps(fiche, sort_keys=True), encoding="utf-8")
    return fiche_hash_value


class FicheCopyError(ValueError):
    """Raised when a fiche cannot be copied into another registry as it is."""


def copy_fiche(fiche_hash: str, source_dir: Path, target_dir: Path) -> bool:
    """Copy the file stored under `fiche_hash` from one registry to another.

    File-for-file, never re-serialised: the copy is the bytes the run wrote.
    Content-addressed, so a target already holding the identical file is left
    alone (returns `False`); one holding other bytes under that name is
    refused, never overwritten, and so is a hash the source does not hold.
    Returns `True` when a file was written.
    """
    source = path_guard.resolve_within_root(source_dir, f"{fiche_hash}.json")
    target = path_guard.resolve_within_root(target_dir, f"{fiche_hash}.json")
    if source is None or target is None or not source.exists():
        raise FicheCopyError(f"fiche {fiche_hash!r} is not in registry {source_dir}")
    content = source.read_bytes()
    if target.exists():
        if target.read_bytes() != content:
            raise FicheCopyError(
                f"fiche {fiche_hash!r} in registry {target_dir} differs from the "
                f"one in {source_dir}; a stored fiche is never overwritten"
            )
        return False
    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return True


def read_fiche(fiche_hash: str, registry_dir: Path) -> dict[str, Any] | None:
    """Return the fiche stored under `fiche_hash`, or `None` if absent.

    Never raises on a missing file: the validator (phase 2) distinguishes
    "missing" from "edited" and needs this to degrade quietly. A `fiche_hash`
    that resolves outside `registry_dir` (e.g. `"../../../../etc/passwd"`)
    degrades the same way, via `path_guard`: an escape is reported as absent,
    never read.
    """
    path = path_guard.resolve_within_root(registry_dir, f"{fiche_hash}.json")
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def verify_fiche(
    fiche_hash: str, registry_dir: Path, *, schema_version: object
) -> FicheVerification:
    """Check whether the stored fiche named `fiche_hash` still hashes to its own name.

    Re-hashed under the projection the citing row's `schema_version` selects
    (`row_contract.fiche_projection_for`), so a committed fiche keeps
    verifying under the projection it was written with and a new fiche
    lacking an engine field is `"edited"`, never passed as an old one.

    `"missing"`: no file is stored under that hash. `"edited"`: the file
    exists but re-hashing its own current content (never the row that cited
    it) no longer matches the name it was stored under. `changed_fields`
    names which fiche keys actually differ, sourced from `git show
    HEAD:<path>` -- the last committed version of the same file, since a
    write-once store has no other original to diff against once its one file
    is edited in place. Degrades to `["unavailable: <reason>"]`, never
    raising, when git can't supply that comparison (no repo, untracked path,
    no `git` on PATH).
    """
    stored = read_fiche(fiche_hash, registry_dir)
    if stored is None:
        return FicheVerification(status="missing", changed_fields=[])

    projection = row_contract.fiche_projection_for(schema_version)
    try:
        rehashed = hardware.fiche_hash(stored, projection)
    except hardware.FicheProjectionError as exc:
        return FicheVerification(status="edited", changed_fields=[str(exc)])
    if rehashed == fiche_hash:
        return FicheVerification(status="ok", changed_fields=[])

    path = registry_dir / f"{fiche_hash}.json"
    return FicheVerification(
        status="edited", changed_fields=_diff_against_committed(stored, path)
    )


def _diff_against_committed(current: dict[str, Any], path: Path) -> list[str]:
    """Name the fields that differ between `current` and `path`'s committed content."""
    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=_GIT_SHOW_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [f"unavailable: git rev-parse failed to run: {exc}"]

    if toplevel.returncode != 0:
        return [f"unavailable: {toplevel.stderr.strip() or 'not a git repository'}"]

    repo_root = Path(toplevel.stdout.strip())
    # HEAD:<path> is always resolved relative to the repository root, never to
    # cwd, so the path handed to `git show` must be repo-root-relative rather
    # than `path` itself (which may be absolute or registry-dir-relative).
    try:
        relative_path = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return ["unavailable: fiche path is not inside its git repository"]

    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{relative_path}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=_GIT_SHOW_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [f"unavailable: git show failed to run: {exc}"]

    if result.returncode != 0:
        return [f"unavailable: {result.stderr.strip() or 'git show failed'}"]

    try:
        committed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ["unavailable: committed fiche content is not valid JSON"]

    if not isinstance(committed, dict):
        return ["unavailable: committed fiche content is not an object"]

    changed = sorted(
        key
        for key in committed.keys() | current.keys()
        if committed.get(key) != current.get(key)
    )
    return changed or ["unavailable: no field-level difference found"]
