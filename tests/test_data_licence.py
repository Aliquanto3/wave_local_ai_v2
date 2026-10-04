"""The licence split: the code stays MIT under LICENSE, the data is CC-BY 4.0
under LICENSE-DATA, and each covered part says so where it lives.

The covered list is read from LICENSE-DATA itself, the file a reader reads,
so there is no second list to drift: a covered path renamed or removed, a
covered directory without its NOTICE.md, or a data directory, reference file
or item-literal module added without entering the scope fails here.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NOTICE = "NOTICE.md"
COVERED_HEADING = "### 1.1 Covered"
LEGAL_CODE_MARKER = "-----BEGIN CC-BY 4.0 LEGAL CODE-----\n"
# sha256 of https://creativecommons.org/licenses/by/4.0/legalcode.txt as
# fetched on 2026-10-02: the legal code is carried verbatim, never edited.
LEGAL_CODE_SHA256 = "9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411"  # pragma: allowlist secret
OUTPUT_SPIKE = (
    "aidd_docs/backlog/spikes/"
    "may-the-model-outputs-in-the-published-rows-be-redistributed-and-on-what-terms.md"
)
COVERED_ENTRY = re.compile(r"^- `([^`]+)`: ")
# A module-level list literal bound to a name ending in ITEMS is a module
# holding item literals (today `judge_probe.JUDGE_PROBE_ITEMS`).
ITEMS_NAME = re.compile(r"ITEMS$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def covered_paths(licence_data: str) -> list[str]:
    """The paths LICENSE-DATA's "1.1 Covered" list names, in order."""
    section = licence_data.split(COVERED_HEADING, 1)[1].split("\n### ", 1)[0]
    return [
        match.group(1)
        for line in section.splitlines()
        if (match := COVERED_ENTRY.match(line))
    ]


def item_literal_modules(package: Path) -> set[str]:
    """Modules under `package` binding a non-empty list literal to an *ITEMS name."""
    found = set()
    for module in sorted(package.glob("*.py")):
        tree = ast.parse(_read(module))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            if (
                isinstance(value, ast.List)
                and value.elts
                and any(
                    isinstance(target, ast.Name) and ITEMS_NAME.search(target.id)
                    for target in targets
                )
            ):
                found.add(module.relative_to(package.parents[1]).as_posix())
    return found


def scope_problems(root: Path) -> list[str]:
    """Every way the tree under `root` and LICENSE-DATA's scope disagree."""
    covered = covered_paths(_read(root / "LICENSE-DATA"))
    problems = []
    for entry in covered:
        path = root / entry
        if not path.exists():
            problems.append(f"{entry}: named as covered but does not exist")
        elif entry.endswith("/"):
            if not path.is_dir():
                problems.append(f"{entry}: named as a directory but is not one")
            elif not (path / NOTICE).is_file():
                problems.append(f"{entry}: covered directory has no {NOTICE}")
            else:
                notice = _read(path / NOTICE)
                for needle in ("CC-BY 4.0", "LICENSE-DATA", "MIT"):
                    if needle not in notice:
                        problems.append(f"{entry}{NOTICE}: does not name {needle}")
        elif entry.endswith(".py"):
            header = _read(path).split('"""', 1)[0]
            for needle in ("CC-BY 4.0", "LICENSE-DATA", "MIT", "LICENSE"):
                if needle not in header:
                    problems.append(f"{entry}: header notice does not name {needle}")

    for parent in ("aidd_docs/results", "aidd_docs/roster"):
        if not (root / parent).is_dir():
            continue
        for child in sorted((root / parent).iterdir()):
            if child.is_dir() and not child.name.startswith((".", "__")):
                entry = f"{parent}/{child.name}/"
                if entry not in covered:
                    problems.append(f"{entry}: data directory not in the scope")
    for reference in sorted((root / "aidd_docs/results").glob("*-reference*.jsonl")):
        entry = f"aidd_docs/results/{reference.name}"
        if entry not in covered:
            problems.append(f"{entry}: reference file not in the scope")
    for module in item_literal_modules(root / "src/wave_local_ai_v2"):
        if module not in covered:
            problems.append(f"{module}: holds item literals but is not in the scope")
    return problems


def test_license_still_names_mit_and_the_code() -> None:
    licence = _read(REPO / "LICENSE")

    assert licence.startswith("MIT License\n")
    assert "Copyright (c) 2026 Aliquanto3" in licence
    assert (
        "copies of the Software, and to permit persons to whom the Software is"
        in licence
    )


def test_every_covered_path_exists_and_says_so_where_it_lives() -> None:
    assert scope_problems(REPO) == []


def test_the_scope_names_what_the_story_requires() -> None:
    covered = covered_paths(_read(REPO / "LICENSE-DATA"))

    assert {
        "aidd_docs/results/",
        "aidd_docs/results/fiches/",
        "aidd_docs/results/suite-definitions/",
        "aidd_docs/results/comparisons/",
        "aidd_docs/roster/",
        "aidd_docs/roster/models.json",
        "aidd_docs/results/runtime-reference.jsonl",
        "aidd_docs/results/quality-reference.jsonl",
        "aidd_docs/results/runtime-reference.schema-1.jsonl",
        "aidd_docs/results/quality-reference.schema-1.jsonl",
        "aidd_docs/results/client-sessions.jsonl",
        "src/wave_local_ai_v2/suite_data/",
        "src/wave_local_ai_v2/judge_probe.py",
    } <= set(covered)
    assert len(covered) == len(set(covered))


def test_the_parts_not_granted_are_named_and_the_output_part_cites_its_spike() -> None:
    licence_data = _read(REPO / "LICENSE-DATA")
    head = licence_data.split(LEGAL_CODE_MARKER, 1)[0]

    for needle in (
        "aidd_docs/results/runtime.jsonl",
        "aidd_docs/results/quality.jsonl",
        "Model weights",
        "third-party licences the roster records",
        "`predicted_label`",
        "## 2. Drawn items",
        "## 3. Assumptions",
        "employment or client agreement",
        OUTPUT_SPIKE,
    ):
        assert needle in head, needle
    assert (REPO / OUTPUT_SPIKE).is_file()


def test_the_legal_code_is_the_official_text_verbatim() -> None:
    legal_code = _read(REPO / "LICENSE-DATA").split(LEGAL_CODE_MARKER, 1)[1]

    assert hashlib.sha256(legal_code.encode("utf-8")).hexdigest() == LEGAL_CODE_SHA256


def test_the_readme_states_the_split_and_links_both_files() -> None:
    readme = _read(REPO / "README.md")
    section = readme.split("\n## Licence\n", 1)[1].split("\n## ", 1)[0]

    assert "](LICENSE)" in section
    assert "](LICENSE-DATA)" in section
    for needle in ("MIT", "CC-BY 4.0", "`predicted_label`", "weights"):
        assert needle in section, needle


def test_suite_registry_ignores_the_notice_in_suite_data() -> None:
    from wave_local_ai_v2 import suite_registry

    registered = set(suite_registry.registered_ids())
    suite_data = REPO / "src/wave_local_ai_v2/suite_data"

    assert (suite_data / NOTICE).is_file()
    assert {path.stem for path in suite_data.glob("*.json")} <= registered
    assert not any("NOTICE" in suite_id for suite_id in registered)


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A minimal tree whose scope and directories agree."""
    (tmp_path / "LICENSE-DATA").write_text(
        f"{COVERED_HEADING}: licensed under CC-BY 4.0\n\n"
        "- `aidd_docs/results/`: results.\n"
        "- `aidd_docs/results/fiches/`: fiches.\n"
        "- `aidd_docs/results/q-reference.jsonl`: rows.\n"
        "- `aidd_docs/roster/`: roster.\n"
        "- `src/wave_local_ai_v2/probe.py`: items.\n\n"
        "### 1.2 Not covered\n\n"
        "- `aidd_docs/results/quality.jsonl`: not covered.\n",
        encoding="utf-8",
    )
    notice = "CC-BY 4.0, see LICENSE-DATA; the code is MIT.\n"
    for directory in (
        "aidd_docs/results",
        "aidd_docs/results/fiches",
        "aidd_docs/roster",
    ):
        (tmp_path / directory).mkdir(parents=True)
        (tmp_path / directory / NOTICE).write_text(notice, encoding="utf-8")
    (tmp_path / "aidd_docs/results/q-reference.jsonl").write_text("", encoding="utf-8")
    package = tmp_path / "src/wave_local_ai_v2"
    package.mkdir(parents=True)
    (package / "probe.py").write_text(
        "# Item literals: CC-BY 4.0, see LICENSE-DATA. Code: MIT, see LICENSE.\n"
        '"""Probe."""\n\nPROBE_ITEMS = [1]\n',
        encoding="utf-8",
    )
    (package / "plain.py").write_text(
        "MIN_ITEMS = 3\nNO_ITEMS: list[int] = []\n", encoding="utf-8"
    )
    return tmp_path


def test_a_tree_in_step_with_its_scope_has_no_problem(tree: Path) -> None:
    assert scope_problems(tree) == []


def test_a_covered_directory_without_its_notice_fails(tree: Path) -> None:
    (tree / "aidd_docs/results/fiches" / NOTICE).unlink()

    assert scope_problems(tree) == [
        f"aidd_docs/results/fiches/: covered directory has no {NOTICE}"
    ]


def test_a_notice_that_does_not_point_to_the_terms_fails(tree: Path) -> None:
    (tree / "aidd_docs/roster" / NOTICE).write_text(
        "CC-BY 4.0, code MIT.\n", encoding="utf-8"
    )

    assert scope_problems(tree) == [
        f"aidd_docs/roster/{NOTICE}: does not name LICENSE-DATA"
    ]


def test_a_renamed_covered_path_fails(tree: Path) -> None:
    (tree / "aidd_docs/results/q-reference.jsonl").rename(
        tree / "aidd_docs/results/q-reference.schema-1.jsonl"
    )

    assert scope_problems(tree) == [
        "aidd_docs/results/q-reference.jsonl: named as covered but does not exist",
        "aidd_docs/results/q-reference.schema-1.jsonl: reference file not in the scope",
    ]


def test_a_path_named_as_a_directory_that_is_a_file_fails(tree: Path) -> None:
    (tree / "aidd_docs/roster" / NOTICE).unlink()
    (tree / "aidd_docs/roster").rmdir()
    (tree / "aidd_docs/roster").write_text("", encoding="utf-8")

    problems = scope_problems(tree)

    assert problems[0] == "aidd_docs/roster/: named as a directory but is not one"


def test_a_data_directory_added_without_entering_the_scope_fails(tree: Path) -> None:
    (tree / "aidd_docs/results/intervals").mkdir()

    assert scope_problems(tree) == [
        "aidd_docs/results/intervals/: data directory not in the scope"
    ]


def test_an_item_literal_module_without_its_header_or_scope_entry_fails(
    tree: Path,
) -> None:
    package = tree / "src/wave_local_ai_v2"
    (package / "probe.py").write_text(
        '"""Probe."""\n\nPROBE_ITEMS = [1]\n', encoding="utf-8"
    )
    (package / "other.py").write_text(
        "OTHER_ITEMS: list[int] = [1]\n", encoding="utf-8"
    )

    problems = scope_problems(tree)

    assert (
        "src/wave_local_ai_v2/probe.py: header notice does not name CC-BY 4.0"
        in problems
    )
    assert (
        "src/wave_local_ai_v2/other.py: holds item literals but is not in the scope"
        in (problems)
    )


def test_section_two_names_the_drawn_source_its_terms_and_its_attribution() -> None:
    licence_data = _read(REPO / "LICENSE-DATA")
    section = licence_data.split("## 2. Drawn items", 1)[1].split("\n## 3.", 1)[0]
    covered = licence_data.split(COVERED_HEADING, 1)[1].split("\n### ", 1)[0]

    for needle in (
        "PolyAI/minds14",
        "40ce77cb32a384e4d50a568e1ec39ac804019d33",  # pragma: allowlist secret
        "CC BY 4.0",
        "https://creativecommons.org/licenses/by/4.0/",
        "Rung: permissive",
        "dataset card at the",
        "prompt template",
        "Creator: PolyAI",
        "Copyright notice",
    ):
        assert needle in section, needle
    assert "holds no item drawn" not in licence_data
    # The covered entries holding items cover the hand-written ones only.
    for entry in (
        "`aidd_docs/results/suite-definitions/`",
        "`src/wave_local_ai_v2/suite_data/`",
        "`aidd_docs/results/quality-reference.jsonl`",
    ):
        line = next(
            line for line in covered.splitlines() if line.startswith(f"- {entry}")
        )
        assert "see 2" in line, entry


def test_neither_suite_notice_claims_a_drawn_item_under_cc_by() -> None:
    for notice in (
        REPO / "src/wave_local_ai_v2/suite_data" / NOTICE,
        REPO / "aidd_docs/results/suite-definitions" / NOTICE,
    ):
        text = _read(notice)
        assert "No item here is drawn today" not in text
        assert "carries its\nown source's licence, recorded on the item" in text
        for needle in ("CC-BY 4.0", "LICENSE-DATA", "MIT"):
            assert needle in text
