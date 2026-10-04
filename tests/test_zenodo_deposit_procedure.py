"""The Zenodo deposit stays a manual, optional procedure.

`docs/zenodo-deposit.md` is the procedure. What the repository can hold
without an account: no workflow names Zenodo (so no token, no automated
deposit, and no release waits on one), no sandbox DOI ever reaches the
citation or the README, and the README points at the procedure. The
GitHub-to-Zenodo toggle lives in the owner's Zenodo account; the procedure
states the manual check for it.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"
PROCEDURE = REPO / "docs" / "zenodo-deposit.md"
README = REPO / "README.md"
CITATION = REPO / "CITATION.cff"
ZENODO = re.compile(r"zenodo", re.IGNORECASE)
# The Zenodo sandbox issues test DOIs under this prefix; zenodo.org uses 10.5281.
SANDBOX_DOI = re.compile(r"10\.5072/\S+")


def zenodo_mentions(text: str) -> list[str]:
    """The lines of a workflow that name Zenodo, a Zenodo token included."""
    return [line.strip() for line in text.splitlines() if ZENODO.search(line)]


def sandbox_dois(text: str) -> list[str]:
    """Every sandbox DOI a file holds."""
    return SANDBOX_DOI.findall(text)


def _workflow_files() -> list[Path]:
    return sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


def test_no_workflow_names_zenodo() -> None:
    files = _workflow_files()

    assert files, "the workflows directory holds no workflow"
    for path in files:
        assert zenodo_mentions(path.read_text(encoding="utf-8")) == [], path.name


def test_a_workflow_naming_a_zenodo_token_is_reported() -> None:
    text = "env:\n  TOKEN: ${{ secrets.ZENODO_TOKEN }}\n  OTHER: x\n"

    assert zenodo_mentions(text) == ["TOKEN: ${{ secrets.ZENODO_TOKEN }}"]


def test_the_citation_and_readme_hold_no_sandbox_doi() -> None:
    for path in (CITATION, README):
        assert sandbox_dois(path.read_text(encoding="utf-8")) == [], path.name


def test_a_sandbox_doi_is_reported() -> None:
    text = "identifiers:\n  - type: doi\n    value: 10.5072/zenodo.123456\n"

    assert sandbox_dois(text) == ["10.5072/zenodo.123456"]
    assert sandbox_dois("value: 10.5281/zenodo.123456") == []


def test_the_readme_points_at_the_procedure() -> None:
    assert PROCEDURE.is_file()
    assert "(docs/zenodo-deposit.md)" in README.read_text(encoding="utf-8")
