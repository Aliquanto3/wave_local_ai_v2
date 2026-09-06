"""Fixtures every test module may use."""

from __future__ import annotations

from pathlib import Path

import pytest
from store_fixtures import build_bundle


@pytest.fixture
def bundle(tmp_path: Path) -> dict[str, Path]:
    """A self-contained store + fiche registry + roster + suite dir on disk."""
    return build_bundle(tmp_path)
