"""Resolve a pointer value against a configured root without ever escaping it.

`resolve_within_root` is the one place a *configured root* is joined with a
*pointer value read from a stored row* -- neither `fiche_registry.read_fiche`
nor `read_model.resolve_suite_definition` sanitized that join before this
module existed.
"""

from __future__ import annotations

from pathlib import Path


def resolve_within_root(root: Path, *parts: str) -> Path | None:
    """Join `root` with `*parts` and confirm the result stays inside `root`.

    Returns the resolved `Path` when it does, `None` when a part such as
    `"../../etc/passwd"` walks it outside `root`. No filesystem I/O beyond the
    two `.resolve()` calls -- existence is still the caller's own check.
    """
    resolved_root = root.resolve()
    candidate = resolved_root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(resolved_root):
        return None
    return candidate
