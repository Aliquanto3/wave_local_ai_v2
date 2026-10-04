"""The release archive, built over the committed bundle at the checked-out commit.

`scripts/assemble_release_archive.py` is what the `release-build` job in `ci.yml`
runs on a `v*` tag (and on demand); these tests build it into `tmp_path` and tamper with
copies of it, so every refusal the job relies on is exercised here.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import assemble_release_archive as release
import drawn_bundle_fixtures as drawn

from wave_local_ai_v2 import build_info, bundle_export

REPO = release.REPO_ROOT
VERSION = build_info.version()
TAG = f"v{VERSION}"
TOP = release.archive_name(VERSION)


@pytest.fixture(scope="module")
def commit() -> str:
    sha = release.head_commit(REPO)
    if sha is None:
        pytest.skip("git cannot name the checked-out commit")
    return sha


@pytest.fixture(scope="module")
def archive(commit: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return release.build(TAG, commit, tmp_path_factory.mktemp("dist"))[0]


@pytest.fixture(scope="module")
def files(archive: Path) -> dict[str, bytes]:
    return release.read_zip(archive, TOP)


def _tampered(
    files: dict[str, bytes], tmp_path: Path, changes: dict[str, bytes | None]
) -> Path:
    """A copy of the archive with entries replaced, added or (None) removed."""
    edited = dict(files)
    for name, data in changes.items():
        if data is None:
            del edited[name]
        else:
            edited[name] = data
    path = tmp_path / f"{TOP}.zip"
    release.write_zip(path, TOP, edited)
    return path


def _refusal(path: Path, commit: str) -> str:
    with pytest.raises(release.ArchiveError) as error:
        release.verify(path, TAG, commit)
    return str(error.value)


# --------------------------------------------------------------------------
# What a built archive holds.
# --------------------------------------------------------------------------


def test_the_archive_is_one_zip_named_after_the_release(archive: Path) -> None:
    assert archive.name == f"wave-local-ai-v2-{VERSION}.zip"


def test_the_archive_holds_every_listed_file(files: dict[str, bytes]) -> None:
    paths = bundle_export.default_bundle_paths()
    tables = {f"{name}.csv" for name in bundle_export.TABLES}
    assert len(tables) == 5
    expected = tables | {
        bundle_export.DICTIONARY_FILE,
        bundle_export.MANIFEST_FILE,
        "LICENSE",
        "LICENSE-DATA",
        "CITATION.cff",
        "README.md",
        paths.runtime_rows.as_posix(),
        paths.quality_rows.as_posix(),
        paths.roster.as_posix(),
    }
    assert expected <= set(files)
    for directory in (paths.fiche_dir, paths.suite_definitions):
        shipped = {
            name for name in files if name.startswith(f"{directory.as_posix()}/")
        }
        on_disk = {
            f"{directory.as_posix()}/{p.name}" for p in (REPO / directory).iterdir()
        }
        assert shipped == on_disk
    assert files["LICENSE-DATA"] == (REPO / "LICENSE-DATA").read_bytes()


def test_two_builds_of_one_commit_are_byte_identical(
    archive: Path, commit: str, tmp_path: Path
) -> None:
    again, _ = release.build(TAG, commit, tmp_path)
    assert again.read_bytes() == archive.read_bytes()


def test_the_readme_names_release_commit_schema_files_and_citation(
    files: dict[str, bytes], commit: str
) -> None:
    readme = files["README.md"].decode("utf-8")
    assert f"- Release: `{TAG}` (packaged version {VERSION})" in readme
    assert f"- Commit: `{commit}`" in readme
    assert "Bundle schema version read: runtime rows 30, quality rows 30" in readme
    for name in files:
        if name != "README.md":
            assert f"`{name}`" in readme, name
    attribution = release.readme_attribution(
        (REPO / "README.md").read_text(encoding="utf-8")
    )
    assert f"{attribution} Commit {commit}." in readme


def test_the_shipped_citation_is_the_repository_one_stamped_with_the_commit(
    files: dict[str, bytes], commit: str
) -> None:
    shipped = yaml.safe_load(files["CITATION.cff"].decode("utf-8"))
    repository = yaml.safe_load((REPO / "CITATION.cff").read_text(encoding="utf-8"))
    assert shipped.pop("commit") == commit
    assert shipped == repository
    assert shipped["version"] == VERSION


def test_no_file_names_a_path_only_a_clone_holds(files: dict[str, bytes]) -> None:
    assert release.clone_only_references(files) == []


def test_every_reviewed_exception_is_still_named_by_its_files(
    files: dict[str, bytes],
) -> None:
    for path, entry in release.PATHS_NOT_SHIPPED.items():
        named = [n for n in entry.named_by if path.encode() in files.get(n, b"")]
        assert named, f"{path} is no longer named; drop its exception"


def test_the_top_level_split_covers_every_tracked_entry() -> None:
    listed = subprocess.run(
        ["git", "-C", str(REPO), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    top_level = {path.split("/", 1)[0] for path in listed}
    declared = {
        *release.SHIPPED_TOP_LEVEL,
        *release.CLONE_ONLY_DIRS,
        *release.CLONE_ONLY_FILES,
    }
    assert top_level == declared


# --------------------------------------------------------------------------
# What `verify` refuses.
# --------------------------------------------------------------------------


def test_a_hand_edited_table_fails_the_derivation(
    files: dict[str, bytes], commit: str, tmp_path: Path
) -> None:
    table = files["quality_items.csv"].replace(b"0.", b"1.", 1)
    path = _tampered(files, tmp_path, {"quality_items.csv": table})
    assert "table quality_items.csv differs" in _refusal(path, commit)


def test_an_edited_bundle_copy_fails(
    files: dict[str, bytes], commit: str, tmp_path: Path
) -> None:
    name = bundle_export.default_bundle_paths().runtime_rows.as_posix()
    path = _tampered(files, tmp_path, {name: files[name] + b"\n"})
    assert f"file {name} differs" in _refusal(path, commit)


def test_a_missing_and_an_extra_file_fail(
    files: dict[str, bytes], commit: str, tmp_path: Path
) -> None:
    path = _tampered(files, tmp_path, {"LICENSE": None, "extra.txt": b"x"})
    refusal = _refusal(path, commit)
    assert "missing: ['LICENSE']" in refusal
    assert "not expected: ['extra.txt']" in refusal


def test_a_clone_only_path_fails(
    files: dict[str, bytes], commit: str, tmp_path: Path
) -> None:
    readme = files["README.md"] + b"\nSee tests/test_citation.py and CHANGELOG.md.\n"
    path = _tampered(files, tmp_path, {"README.md": readme})
    refusal = _refusal(path, commit)
    assert "only a clone holds: README.md: tests/test_citation.py" in refusal
    assert "only a clone holds: README.md: CHANGELOG.md" in refusal


def test_an_exception_holds_only_in_the_files_it_names() -> None:
    path = "src/wave_local_ai_v2/judge_probe.py"
    assert release.clone_only_references({"LICENSE-DATA": path.encode()}) == []
    assert release.clone_only_references({"README.md": path.encode()}) == [
        f"README.md: {path}"
    ]


def test_a_path_resolves_as_a_file_or_a_directory_prefix() -> None:
    files = {"aidd_docs/results/fiches/a.json": b"", "x.md": b""}
    files["x.md"] = b"`aidd_docs/results/fiches/` and aidd_docs/results/fiches."
    assert release.clone_only_references(files) == []
    files["x.md"] = b"https://example.org/src/x.py and aidd_docs_x/ and docs/y"
    assert release.clone_only_references(files) == ["x.md: docs/y"]


def test_a_readme_or_citation_naming_another_release_fails(
    files: dict[str, bytes], commit: str, tmp_path: Path
) -> None:
    other = "0" * 40
    readme = files["README.md"].replace(commit.encode(), other.encode())
    readme = readme.replace(f"`{TAG}`".encode(), b"`v9.9.9`")
    citation = files["CITATION.cff"].replace(commit.encode(), other.encode())
    citation = citation.replace(f"version: {VERSION}".encode(), b"version: 9.9.9")
    path = _tampered(files, tmp_path, {"README.md": readme, "CITATION.cff": citation})
    refusal = _refusal(path, commit)
    assert f"README does not name release {TAG}" in refusal
    assert f"README does not name commit {commit}" in refusal
    assert f"CITATION.cff does not name version {VERSION}" in refusal
    assert f"CITATION.cff is not stamped with {commit}" in refusal


def test_a_file_outside_the_top_folder_or_not_a_zip_fails(
    files: dict[str, bytes], commit: str, tmp_path: Path
) -> None:
    path = tmp_path / "other.zip"
    release.write_zip(path, "elsewhere", {"README.md": b""})
    with pytest.raises(release.ArchiveError, match="outside the"):
        release.read_zip(path, TOP)
    junk = tmp_path / "junk.zip"
    junk.write_bytes(b"not a zip")
    with pytest.raises(release.ArchiveError, match="not a readable zip"):
        release.read_zip(junk, TOP)


# --------------------------------------------------------------------------
# What `build` refuses before writing anything.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tag", "message"),
    [
        ("0.2.0", "is not a v<major>.<minor>.<patch> tag"),
        ("v9.9.9", "the package is"),
    ],
)
def test_a_tag_that_is_not_the_packaged_version_is_refused(
    tag: str, message: str, commit: str, tmp_path: Path
) -> None:
    with pytest.raises(release.ArchiveError, match=message):
        release.build(tag, commit, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_tag_disagreeing_with_the_citation_is_refused(
    commit: str, tmp_path: Path
) -> None:
    (tmp_path / "CITATION.cff").write_text("version: 9.9.9\n", encoding="utf-8")
    with pytest.raises(release.ArchiveError, match="CITATION.cff names 9.9.9"):
        release.release_version(TAG, commit, tmp_path)


@pytest.mark.parametrize("bad", ["0" * 40, "not-a-sha"])
def test_a_commit_that_is_not_the_checkout_is_refused(bad: str) -> None:
    with pytest.raises(release.ArchiveError, match="not the checked-out commit"):
        release.release_version(TAG, bad, REPO)


def test_head_commit_outside_a_repository_is_none(tmp_path: Path) -> None:
    assert release.head_commit(tmp_path / "missing") is None


def test_the_citation_stamp_refuses_a_committed_or_missing_version() -> None:
    with pytest.raises(release.ArchiveError, match="already names a commit"):
        release.stamp_citation("version: 1\ncommit: abc\n", "f" * 40)
    with pytest.raises(release.ArchiveError, match="exactly one top-level version"):
        release.stamp_citation("# only a comment\ntitle: x\n", "f" * 40)


def test_a_readme_without_its_attribution_or_a_citation_without_a_url() -> None:
    with pytest.raises(release.ArchiveError, match="no attribution block"):
        release.readme_attribution("# README\n")
    with pytest.raises(release.ArchiveError, match="no repository-code"):
        release.repository_url("title: x\n")


def test_a_missing_bundle_part_is_refused(tmp_path: Path) -> None:
    with pytest.raises(release.ArchiveError, match="missing from the checkout"):
        release.bundle_files(tmp_path)


def test_a_refused_export_or_an_undescribed_file_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(_paths: object) -> None:
        raise bundle_export.ExportError("no row file")

    monkeypatch.setattr(bundle_export, "build_export", refuse)
    with pytest.raises(release.ArchiveError, match="export refused: no row file"):
        release.export_files(REPO)
    monkeypatch.setattr(
        bundle_export, "build_export", lambda _paths: {"new_table.csv": [("a",)]}
    )
    with pytest.raises(release.ArchiveError, match="no archive description"):
        release.export_files(REPO)


# --------------------------------------------------------------------------
# The command.
# --------------------------------------------------------------------------


def test_the_command_builds_verifies_and_refuses(
    commit: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "dist"
    assert (
        release.main(
            ["build", "--tag", TAG, "--commit", commit, "--output-dir", str(out)]
        )
        == 0
    )
    built = out / f"{TOP}.zip"
    assert release.main(["verify", "--tag", TAG, "--commit", commit, str(built)]) == 0
    assert (
        release.main(["verify", "--tag", "v9.9.9", "--commit", commit, str(built)]) == 1
    )
    printed = capsys.readouterr()
    assert "built and verified" in printed.out
    assert f"verified {built.as_posix()}" in printed.out
    assert "release archive refused:" in printed.err


def test_an_altered_readme_body_or_citation_fails(
    files: dict[str, bytes], commit: str, tmp_path: Path
) -> None:
    readme = files["README.md"].replace(b"in any spreadsheet", b"in Excel only")
    citation = files["CITATION.cff"] + b"# appended\n"
    path = _tampered(files, tmp_path, {"README.md": readme, "CITATION.cff": citation})
    refusal = _refusal(path, commit)
    assert "file README.md differs" in refusal
    assert "file CITATION.cff differs" in refusal


def test_the_manifest_versions_read_a_quoted_cell() -> None:
    manifest = (
        b"part,path,entries_read,version_field,versions_read\r\n"
        b'runtime_rows,"a,b.jsonl",2,schema_version,"6;7"\r\n'
        b"quality_rows,q.jsonl,1,schema_version,7\r\n"
    )
    assert release.manifest_versions(manifest) == {
        "runtime_rows": "6;7",
        "quality_rows": "7",
    }


# --------------------------------------------------------------------------
# Drawn items: each rung over a constructed bundle (`drawn_bundle_fixtures`).
# --------------------------------------------------------------------------

FAKE_COMMIT = "f" * 40
CLOSED_SNAPSHOT = (
    "aidd_docs/results/suite-definitions/classification-banking-intents-minds14@1.json"
)
Built = dict[str, tuple[drawn.Constructed, dict[str, bytes]]]


def _drawn_section_of(root: Path) -> str:
    return release.drawn_section((root / "LICENSE-DATA").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rung_archives(tmp_path_factory: pytest.TempPathFactory) -> Built:
    """One archive per rung, built and verified from its constructed root."""
    built = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(release, "head_commit", lambda _root: FAKE_COMMIT)
        for rung in (drawn.PERMISSIVE, drawn.SHARE_ALIKE, drawn.NO_REDISTRIBUTION):
            base = tmp_path_factory.mktemp(rung.replace(" ", "-"))
            constructed = drawn.build_repo(base / "repo", rung)
            path, _ = release.build(TAG, FAKE_COMMIT, base / "dist", constructed.root)
            built[rung] = (constructed, release.read_zip(path, TOP))
    return built


def _table(files: dict[str, bytes]) -> list[dict[str, str]]:
    text = files[f"{bundle_export.QUALITY_TABLE}.csv"].decode("utf-8")
    return list(csv.DictReader(io.StringIO(text, newline="")))


def test_the_readme_repeats_licence_data_section_two(
    files: dict[str, bytes], rung_archives: Built
) -> None:
    assert _drawn_section_of(REPO) in files["README.md"].decode("utf-8")
    for constructed, built in rung_archives.values():
        section = _drawn_section_of(constructed.root)
        assert section in built["README.md"].decode("utf-8")


def test_a_permissive_archive_holds_each_source_s_notices(
    rung_archives: Built,
) -> None:
    _, built = rung_archives[drawn.PERMISSIVE]
    paths = bundle_export.default_bundle_paths()
    apache = (REPO / paths.suite_definitions / drawn.APACHE_TEXT).read_bytes()
    for directory in (paths.suite_definitions, paths.quality_rows.parent):
        assert built[f"{directory.as_posix()}/{drawn.APACHE_TEXT}"] == apache
    readme = built["README.md"].decode("utf-8")
    minds = readme.split("### 2.1 MInDS-14", 1)[1].split("### 2.2", 1)[0]
    for element in (
        "Creator: PolyAI",
        "Copyright notice",
        "https://creativecommons.org/licenses/by/4.0/",
        "https://huggingface.co/datasets/PolyAI/minds14",
        "40ce77cb32a384e4d50a568e1ec39ac804019d33",  # pragma: allowlist secret
        "prompt template",
    ):
        assert element in minds, element
    wmt = readme.split("### 2.2 WMT24++", 1)[1]
    assert drawn.APACHE_TEXT in wmt
    assert "Changes made" in wmt
    for row in _table(built):
        if row["provenance"] == "public":
            assert row["item_licence"] in ("CC-BY-4.0", "Apache-2.0")
            assert row["item_source"] in ("PolyAI/minds14", "google/wmt24pp")
            assert len(row["item_content_hash"]) == 64
        assert row["item_redaction"] == bundle_export.NOT_REDACTED
        assert row["item_licence_file"] == ""


def test_a_share_alike_set_ships_apart_under_its_own_licence_file(
    rung_archives: Built,
) -> None:
    _, built = rung_archives[drawn.SHARE_ALIKE]
    paths = bundle_export.default_bundle_paths()
    assert paths.share_alike_dir is not None
    directory = f"{paths.share_alike_dir.as_posix()}/{drawn.SHARE_ALIKE_LICENCE}"
    licence_file = f"{directory}/LICENSE"
    assert built[licence_file] == drawn.SHARE_ALIKE_TEXT.encode("utf-8")
    shipped_rows = built[f"{directory}/quality-reference.jsonl"].decode("utf-8")
    assert drawn.SHARE_ALIKE_SOURCE in shipped_rows
    snapshot = f"{directory}/suite-definitions/translation-mixed-domain-wmt24pp@1.json"
    assert drawn.SHARE_ALIKE_SOURCE in built[snapshot].decode("utf-8")
    # None of it in the CC-BY 4.0 files.
    for name in (
        paths.quality_rows.as_posix(),
        f"{paths.suite_definitions.as_posix()}/translation-mixed-domain-wmt24pp@1.json",
    ):
        assert drawn.SHARE_ALIKE_SOURCE.encode() not in built.get(name, b"")
    rows = _table(built)
    marked = [r for r in rows if r["item_licence_file"]]
    assert {r["item_licence_file"] for r in marked} == {licence_file}
    assert {r["item_source"] for r in marked} == {drawn.SHARE_ALIKE_SOURCE}
    assert all(r["item_licence"] == drawn.SHARE_ALIKE_LICENCE for r in marked)
    assert len(marked) == 2
    assert len(rows) == 5
    readme = built["README.md"].decode("utf-8")
    assert f"- `{licence_file}` governs the items drawn from" in readme
    assert f"`{licence_file}` | The full text of licence" in readme


def _recompute(readme: str, source_row: dict[str, Any], rule: dict[str, Any]) -> str:
    """The content hash, following the recipe the archive README states."""
    assert "SHA-256 hex digest of the UTF-8 bytes of the JSON object" in readme
    assert "NFC-normalised with every whitespace run collapsed" in readme
    (benchmark,) = rule["benchmarks"]
    text = [
        " ".join(unicodedata.normalize("NFC", str(source_row[name])).split())
        for name in rule["content_fields"]
    ]
    payload = {
        "licence": benchmark["licence"],
        "source": benchmark["source"],
        "source_revision": benchmark["source_revision"],
        "text": text,
    }
    serialised = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def test_a_redacted_item_is_a_visible_hole_its_reader_can_fill_by_hand(
    rung_archives: Built,
) -> None:
    constructed, built = rung_archives[drawn.NO_REDISTRIBUTION]
    # No file carries the withheld text, the suite-definition snapshots included.
    assert constructed.withheld_text
    for text in constructed.withheld_text:
        assert all(text.encode("utf-8") not in data for data in built.values())
    rows = [r for r in _table(built) if r["item_source"] == drawn.CLOSED_SOURCE]
    assert len(rows) == 2
    snapshot = json.loads(built[CLOSED_SNAPSHOT])
    readme = built["README.md"].decode("utf-8")
    for row, source_row in zip(rows, constructed.source_rows, strict=True):
        assert row["item_redaction"] == bundle_export.NO_REDISTRIBUTION
        assert row["item_source_revision"] == drawn.CLOSED_REVISION
        assert row["item_source_key"] == source_row["path"]
        assert row["prompt"] == row["expected_label"] == ""
        assert row["item_content_hash"] == _recompute(
            readme, source_row, snapshot["selection_rule"]
        )
    for item in snapshot["items"]:
        assert set(item) <= {
            *bundle_export.REDACTED_ITEM_KEPT,
            "provenance",
            "contamination_risk",
        }
    instructions = readme.split("### Obtaining the text", 1)[1]
    assert instructions.count(f"- `{drawn.CLOSED_SOURCE}` at revision") == 1
    assert "find the source row whose `path` equals `item_source_key`" in instructions


def test_no_archive_ships_code(files: dict[str, bytes], rung_archives: Built) -> None:
    assert release.code_entries(files) == []
    for _, built in rung_archives.values():
        assert release.code_entries(built) == []
    assert release.code_entries({"fetch.py": b"", "a.csv": b""}) == ["fetch.py"]


def test_a_shipped_script_or_an_unredacted_snapshot_fails_verify(
    rung_archives: Built, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    constructed, built = rung_archives[drawn.NO_REDISTRIBUTION]
    snapshot = json.loads(built[CLOSED_SNAPSHOT])
    snapshot["items"][0]["prompt"] = constructed.withheld_text[0]
    path = _tampered(
        built,
        tmp_path,
        {
            CLOSED_SNAPSHOT: json.dumps(snapshot).encode(),
            "fetch_corpus.py": b"import requests\n",
        },
    )
    monkeypatch.setattr(release, "head_commit", lambda _root: FAKE_COMMIT)
    with pytest.raises(release.ArchiveError) as error:
        release.verify(path, TAG, FAKE_COMMIT, constructed.root)
    assert "ships code, not data: fetch_corpus.py" in str(error.value)
    assert "still carries ['prompt'], which may hold its text" in str(error.value)


def test_a_drawn_source_licence_data_does_not_name_at_its_rung_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(release, "head_commit", lambda _root: FAKE_COMMIT)
    constructed = drawn.build_repo(tmp_path / "repo", drawn.NO_REDISTRIBUTION)
    licence = constructed.root / "LICENSE-DATA"
    text = licence.read_text(encoding="utf-8")
    licence.write_text(
        text.replace("- Rung: no redistribution.", "- Rung: permissive."),
        encoding="utf-8",
    )
    with pytest.raises(release.ArchiveError, match="the no redistribution rung"):
        release.build(TAG, FAKE_COMMIT, tmp_path / "dist", constructed.root)
    licence.write_text(
        text.replace(f"- Source: `{drawn.CLOSED_SOURCE}`", "- Source: elsewhere"),
        encoding="utf-8",
    )
    with pytest.raises(release.ArchiveError, match="names no subsection with source"):
        release.build(TAG, FAKE_COMMIT, tmp_path / "dist", constructed.root)
    assert not (tmp_path / "dist").exists()


def test_licence_data_without_section_two_or_a_refused_bundle_is_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(release.ArchiveError, match="no section 2"):
        release.drawn_section("## 1. Scope\n")
    with pytest.raises(release.ArchiveError, match="export refused"):
        release.drawn_sources(tmp_path)


def test_a_snapshot_that_is_not_a_suite_definition_is_named() -> None:
    name = "aidd_docs/results/suite-definitions/x@1.json"
    assert release.redaction_problems({name: b"[]"}) == [
        f"{name} is not a suite definition"
    ]
