"""`CITATION.cff` against the packaged version, the README and a release tag.

The citation and the CC-BY 4.0 attribution are one string, stated once: the
README's attribution is derived from `CITATION.cff` by `attribution()` below,
so a hand edit to either side fails here. The citation's `version` must equal
the packaged version; `verify-tag` already refuses a tag that disagrees with
the packaged version, so a tag that disagrees with the citation cannot publish.

The author identity is the owner's to supply. Until it is, the file carries
`PLACEHOLDER-` markers: off a tag the release check skips and names them, on
a tag (the CI build `publish` needs) it fails, so a release cannot ship them.
"""

import os
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from wave_local_ai_v2 import build_info

REPO = Path(__file__).resolve().parents[1]
CITATION = REPO / "CITATION.cff"
README = REPO / "README.md"
CHANGELOG = REPO / "CHANGELOG.md"
START = "<!-- attribution:start -->"
END = "<!-- attribution:end -->"
PLACEHOLDER = re.compile(r"PLACEHOLDER-[A-Z0-9-]*[A-Z0-9]")
REQUIRED_KEYS = (
    "cff-version",
    "message",
    "title",
    "version",
    "date-released",
    "authors",
    "repository-code",
    "license",
)
# How each SPDX id the citation lists reads in the attribution: the part it
# covers, its name, and the link CC-BY 4.0 asks an attribution to carry.
LICENCE_PHRASES = {
    "MIT": "code: MIT",
    "CC-BY-4.0": "data: CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/)",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load(text: str) -> dict[str, Any]:
    loaded = yaml.safe_load(text)
    assert isinstance(loaded, dict)
    return loaded


def _author_name(author: dict[str, Any]) -> str:
    """An entity's or pseudonym's name as given, a person as `family, given`."""
    if "name" in author:
        return str(author["name"])
    if "family-names" in author:
        given = author.get("given-names")
        family = str(author["family-names"])
        return f"{family}, {given}" if given else family
    return str(author["alias"])


def attribution(citation: dict[str, Any]) -> str:
    """The one attribution and citation string a reuser copies."""
    authors = "; ".join(_author_name(author) for author in citation["authors"])
    year = str(citation["date-released"])[:4]
    licences = "; ".join(LICENCE_PHRASES[spdx] for spdx in citation["license"])
    return (
        f"{authors} ({year}). {citation['title']}, version {citation['version']}. "
        f"{citation['repository-code']}. Licences: {licences}."
    )


def readme_attribution(readme: str) -> str:
    """The single string the README marks as the attribution."""
    assert readme.count(START) == 1, "the README marks exactly one attribution"
    assert readme.count(END) == 1, "the README marks exactly one attribution"
    marked = readme.split(START, 1)[1].split(END, 1)[0]
    return " ".join(marked.split())


def version_mismatch(citation: dict[str, Any], packaged: str) -> str | None:
    """Why the citation's version disagrees with the package, or None."""
    cited = str(citation["version"])
    if cited == packaged:
        return None
    return f"CITATION.cff names version {cited!r}, but the package is {packaged!r}"


def release_date_mismatch(citation: dict[str, Any], changelog: str) -> str | None:
    """Why `date-released` is not the CHANGELOG date of the cited version, or None."""
    version = str(citation["version"])
    heading = re.search(
        rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$",
        changelog,
        re.MULTILINE,
    )
    if heading is None:
        return f"CHANGELOG.md has no dated heading for version {version!r}"
    released = str(citation["date-released"])
    if released != heading.group(1):
        return (
            f"CITATION.cff dates version {version!r} {released}, "
            f"CHANGELOG.md dates it {heading.group(1)}"
        )
    return None


def unresolved(text: str) -> list[str]:
    """The placeholder markers still standing in for the owner's identity."""
    return sorted(set(PLACEHOLDER.findall(text)))


def release_gate_failure(text: str, env: dict[str, str]) -> str | None:
    """Why a release build must stop on `text`, or None when it may proceed."""
    if not env.get("GITHUB_REF", "").startswith("refs/tags/"):
        return None
    markers = unresolved(text)
    if not markers:
        return None
    return f"{env['GITHUB_REF']} cannot publish with unresolved {', '.join(markers)}"


@pytest.fixture
def citation() -> dict[str, Any]:
    return _load(_read(CITATION))


def test_the_citation_version_is_the_packaged_version(
    citation: dict[str, Any],
) -> None:
    assert version_mismatch(citation, build_info.version()) is None


def test_a_mismatched_version_is_reported(citation: dict[str, Any]) -> None:
    drifted = {**citation, "version": "9.9.9"}

    reason = version_mismatch(drifted, build_info.version())

    assert reason is not None
    assert "'9.9.9'" in reason


def test_the_release_date_is_the_changelog_date_of_the_version(
    citation: dict[str, Any],
) -> None:
    assert release_date_mismatch(citation, _read(CHANGELOG)) is None


def test_a_version_bumped_without_its_release_date_is_reported(
    citation: dict[str, Any],
) -> None:
    changelog = "## [0.3.0] - 2026-11-02\n\n## [0.2.0] - 2026-09-22\n"
    bumped = {**citation, "version": "0.3.0", "date-released": "2026-09-22"}

    stale = release_date_mismatch(bumped, changelog)
    undated = release_date_mismatch({**citation, "version": "0.4.0"}, changelog)

    assert stale is not None
    assert "2026-11-02" in stale
    assert undated is not None
    assert "'0.4.0'" in undated


def test_the_citation_names_the_work_its_author_link_and_both_licences(
    citation: dict[str, Any],
) -> None:
    for key in REQUIRED_KEYS:
        assert citation.get(key), key
    assert citation["cff-version"] == "1.2.0"
    assert citation["title"] == "wave-local-ai-v2"
    assert citation["repository-code"].startswith("https://github.com/")
    assert citation["license"] == ["MIT", "CC-BY-4.0"]
    assert all(_author_name(author) for author in citation["authors"])


def test_the_repository_copy_names_no_commit_and_says_why(
    citation: dict[str, Any],
) -> None:
    assert "commit" not in citation
    assert "names no commit" in _read(CITATION)


def test_the_readme_attribution_is_derived_from_the_citation(
    citation: dict[str, Any],
) -> None:
    assert readme_attribution(_read(README)) == attribution(citation)


def test_an_edited_readme_attribution_disagrees(citation: dict[str, Any]) -> None:
    edited = _read(README).replace(f"version {citation['version']}", "version 0.0.1")

    assert readme_attribution(edited) != attribution(citation)


def test_the_readme_attribution_sits_in_the_licence_section() -> None:
    section = _read(README).split("\n## Licence\n", 1)[1].split("\n## ", 1)[0]

    assert START in section
    assert "](CITATION.cff)" in section


@pytest.mark.parametrize(
    ("author", "expected"),
    [
        ({"name": "Benchmark Lab"}, "Benchmark Lab"),
        ({"family-names": "Doe", "given-names": "Jane"}, "Doe, Jane"),
        ({"family-names": "Doe"}, "Doe"),
        ({"alias": "quanto"}, "quanto"),
    ],
)
def test_each_author_form_reads_as_one_name(
    author: dict[str, Any], expected: str
) -> None:
    assert _author_name(author) == expected


def test_a_placeholder_stops_a_tag_build_only() -> None:
    text = "given-names: PLACEHOLDER-OWNER-GIVEN-NAMES\n# PLACEHOLDER-OWNER-ORCID ("
    tag = {"GITHUB_REF": "refs/tags/v0.3.0"}

    failure = release_gate_failure(text, tag)

    assert failure is not None
    assert "PLACEHOLDER-OWNER-GIVEN-NAMES, PLACEHOLDER-OWNER-ORCID" in failure
    assert release_gate_failure(text, {"GITHUB_REF": "refs/heads/main"}) is None
    assert release_gate_failure(text, {}) is None
    assert release_gate_failure("given-names: Jane", tag) is None


def test_a_release_names_the_owner_not_a_placeholder() -> None:
    text = _read(CITATION) + readme_attribution(_read(README))
    failure = release_gate_failure(text, dict(os.environ))
    if failure is not None:
        pytest.fail(failure)
    markers = unresolved(text)
    if markers:
        pytest.skip(f"awaiting the owner's identity: {', '.join(markers)}")
