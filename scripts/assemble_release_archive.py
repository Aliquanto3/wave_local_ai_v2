"""Assemble and verify the release archive: one zip that needs no clone.

A third party given one release URL downloads one file. This script builds
that file from the checked-out commit and refuses it when it would mislead:

- the five flat tables, `column_dictionary.csv` and `bundle_manifest.csv`,
  regenerated here with `wave-local-ai-v2-export`'s own code from the
  committed reference bundle;
- the bundle they were derived from, every part the export reads, at its
  repository path (so `bundle_manifest.csv`'s paths and `LICENSE-DATA`'s
  covered paths resolve inside the archive), with each shipped directory's
  `NOTICE.md`;
- `LICENSE`, `LICENSE-DATA`, `CITATION.cff` with the commit stamped in, and a
  README naming the release, the commit, the bundle schema version read, what
  each file is and how to cite the release.

`verify` reopens the zip and fails on any of: a missing or extra file, a
bundle file that differs from the repository's, a table that differs from the
export regenerated from the repository (a hand-edited table), a version or
commit that disagrees with the tag, and a file naming a repository path the
archive does not hold. `build` runs `verify` on what it wrote.

With `--parquet` (the `release-build` job always passes it; it needs the `release`
dependency group's `pyarrow`), the archive also holds one typed Parquet copy
per table, and `verify` reads each back and fails unless it equals its CSV
cell by cell under the column dictionary's types (`release_parquet.py`).

    uv run python scripts/assemble_release_archive.py build \\
        --tag v0.2.0 --commit <sha> --output-dir dist [--parquet]
    uv run python scripts/assemble_release_archive.py verify \\
        --tag v0.2.0 --commit <sha> [--parquet] dist/wave-local-ai-v2-0.2.0.zip
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import re
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import release_parquet

from wave_local_ai_v2 import build_info, bundle_export

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "wave-local-ai-v2"
# Fixed entry timestamps: two builds of one commit are byte-identical.
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

CITATION_FILE = "CITATION.cff"
README_FILE = "README.md"
LICENCE_FILES = ("LICENSE", "LICENSE-DATA")
NOTICE_FILE = "NOTICE.md"
# The licence text a directory holding drawn items carries beside them
# (LICENSE-DATA section 2.2): it ships with the directory, as NOTICE.md does.
DRAWN_LICENCE_TEXT = "LICENSE-APACHE-2.0.txt"
ATTRIBUTION_START = "<!-- attribution:start -->"
ATTRIBUTION_END = "<!-- attribution:end -->"

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TAG_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+\S*)$")
CITATION_VERSION_RE = re.compile(
    r"^version: *['\"]?(?P<version>[^'\"\s]+)", re.MULTILINE
)
CITATION_COMMIT_RE = re.compile(r"^commit: *['\"]?(?P<commit>[^'\"\s]+)", re.MULTILINE)
README_RELEASE_RE = re.compile(
    r"^- Release: `v(?P<tag>[^`]+)` \(packaged version (?P<version>[^)]+)\)$",
    re.MULTILINE,
)
README_COMMIT_RE = re.compile(r"^- Commit: `(?P<commit>[^`]+)`$", re.MULTILINE)

# Every top-level entry the repository tracks, split into what the archive
# ships and what exists only in a clone. tests/ holds this equal to
# `git ls-files`, so a new top-level entry must be placed in one or the other.
SHIPPED_TOP_LEVEL = (CITATION_FILE, *LICENCE_FILES, README_FILE)
CLONE_ONLY_DIRS = (
    ".github",
    "aidd_docs",
    "context_input",
    "docs",
    "frontend",
    "scripts",
    "src",
    "tests",
)
CLONE_ONLY_FILES = (
    ".dockerignore",
    ".env.example",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".python-version",
    ".secrets.baseline",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "Dockerfile",
    "compose.build.yaml",
    "compose.yaml",
    "pyproject.toml",
    "uv.lock",
)
_BOUNDARY = r"[\w./@-]"
REPOSITORY_PATH_RE = re.compile(
    rf"(?<!{_BOUNDARY})(?:"
    + "|".join(re.escape(name) for name in CLONE_ONLY_DIRS)
    + rf")/[\w./@-]*|(?<!{_BOUNDARY})(?:"
    + "|".join(re.escape(name) for name in CLONE_ONLY_FILES)
    + r")(?![\w-])"
)


class NotShipped(NamedTuple):
    """A repository path a shipped file names but the archive does not hold."""

    named_by: tuple[str, ...]  # the only shipped files allowed to name it
    reason: str
    tracked: bool = True  # False: no commit holds it, so no link is given


# The archive README links each tracked path at the release's commit, so none
# is reachable only from a clone. Any other file naming them, and any file
# naming any other path the archive does not hold, fails `verify`.
_LICENCE = ("LICENSE-DATA",)
# The roster's free-text `read_from` provenance notes, and their projection.
_ROSTER_NOTES = ("aidd_docs/roster/models.json", "roster.csv")
PATHS_NOT_SHIPPED: Mapping[str, NotShipped] = {
    "aidd_docs/results/runtime-reference.schema-1.jsonl": NotShipped(
        _LICENCE,
        "superseded runtime rows, retained in the repository; no table reads them",
    ),
    "aidd_docs/results/quality-reference.schema-1.jsonl": NotShipped(
        _LICENCE,
        "superseded quality rows, retained in the repository; no table reads them",
    ),
    "aidd_docs/results/runtime-reference.schema-7.jsonl": NotShipped(
        _LICENCE,
        "superseded schema-7 runtime rows, retained in the repository; no table "
        "reads them",
    ),
    "aidd_docs/results/quality-reference.schema-7.jsonl": NotShipped(
        _LICENCE,
        "superseded schema-7 quality rows, retained in the repository; no table "
        "reads them",
    ),
    "aidd_docs/results/comparisons.schema-7/": NotShipped(
        _LICENCE,
        "superseded comparison family records over the schema-7 rows, retained "
        "in the repository; no table reads them",
    ),
    "aidd_docs/results/leader-sets.schema-7/": NotShipped(
        _LICENCE,
        "superseded leader-set records over the schema-7 rows, retained in the "
        "repository; no table reads them",
    ),
    "aidd_docs/results/refusals-reference.jsonl": NotShipped(
        _LICENCE,
        "the bundle's refusal records; no table reads them yet",
    ),
    "aidd_docs/results/machines/": NotShipped(
        _LICENCE,
        "the per-machine locations the bundle is derived from; the bundle rows "
        "beside the tables are the same lines",
    ),
    "aidd_docs/results/client-sessions.jsonl": NotShipped(
        _LICENCE,
        "the client-session reception record, appended by hand after a release "
        "ships; its copy at this commit is already stale, so read the current "
        "version on the repository's main branch",
    ),
    "src/wave_local_ai_v2/suite_data/": NotShipped(
        _LICENCE,
        "the suite definitions as stored in the source tree; their "
        "published snapshots are aidd_docs/results/suite-definitions/",
    ),
    "scripts/minds14_suite.py": NotShipped(
        (
            "aidd_docs/results/suite-definitions/classification-banking-intents-minds14@1.json",
            f"{bundle_export.QUALITY_TABLE}.csv",
        ),
        "the loader that fetches MInDS-14 at its pinned revision and writes "
        "the source table the publication classification suite was drawn "
        "from, named by that suite's source_table record",
    ),
    "scripts/wmt24pp_suite.py": NotShipped(
        (
            "LICENSE-DATA",
            "aidd_docs/results/suite-definitions/translation-mixed-domain-wmt24pp@1.json",
            f"{bundle_export.QUALITY_TABLE}.csv",
        ),
        "the loader that fetches WMT24++ at its pinned revision and writes "
        "the source table the publication translation suite was drawn from, "
        "named by that suite's source_table record",
    ),
    "src/wave_local_ai_v2/use_case_coverage.json": NotShipped(
        _LICENCE,
        "the declared use-case coverage record",
    ),
    "src/wave_local_ai_v2/judge_probe.py": NotShipped(
        _LICENCE,
        "the judge probe, whose hand-written items LICENSE-DATA covers",
    ),
    "aidd_docs/results/runtime.jsonl": NotShipped(
        _LICENCE,
        "an untracked per-machine live store, never published",
        tracked=False,
    ),
    "aidd_docs/results/quality.jsonl": NotShipped(
        _LICENCE,
        "an untracked per-machine live store, never published",
        tracked=False,
    ),
    "aidd_docs/backlog/spikes/may-the-model-outputs-in-the-published-rows-be-"
    "redistributed-and-on-what-terms.md": NotShipped(
        _LICENCE,
        "the open question on redistributing model output (LICENSE-DATA 1.3)",
    ),
    "aidd_docs/results/README.md": NotShipped(
        _ROSTER_NOTES,
        "the repository's results guide, whose runtime table a roster minimum "
        "was read from",
    ),
    "aidd_docs/tasks/2026_10/2026_10_02_gpu-cpu-never-share-a-fiche/evidence/"
    "runtime.jsonl": NotShipped(
        _ROSTER_NOTES,
        "unpublished run evidence a roster minimum was read from",
    ),
    "aidd_docs/tasks/2026_10/2026_10_02_named-run-profiles/evidence/"
    "runtime.jsonl": NotShipped(
        _ROSTER_NOTES,
        "unpublished run evidence a roster minimum was read from",
    ),
}

TABLE_DESCRIPTIONS: Mapping[str, str] = {
    f"{bundle_export.QUALITY_TABLE}.csv": (
        "One row per quality row, every pointer resolved into columns (fiche, "
        "roster entry, suite definition)."
    ),
    f"{bundle_export.RUNTIME_TABLE}.csv": (
        "One row per runtime row, fiche and roster entry resolved into columns."
    ),
    f"{bundle_export.FICHE_TABLE}.csv": "One row per stored hardware fiche.",
    f"{bundle_export.ROSTER_TABLE}.csv": "One row per roster entry.",
    f"{bundle_export.COMPARISON_TABLE}.csv": (
        "One row per comparison-family record, comparison, leader-set record and "
        "leader-set subject, named by record_kind."
    ),
    bundle_export.DICTIONARY_FILE: (
        "Every column of every table: meaning, unit, what an empty cell means."
    ),
    bundle_export.MANIFEST_FILE: (
        "Each bundle part read, its path in this archive, entries read and the "
        "versions it declares."
    ),
}


class ArchiveError(Exception):
    """The archive cannot be built, or the one given does not verify."""


# --------------------------------------------------------------------------
# What the archive holds.
# --------------------------------------------------------------------------


def archive_name(version: str) -> str:
    return f"{DIST_NAME}-{version}"


def _relative(path: Path) -> str:
    return path.as_posix()


def bundle_files(repo_root: Path) -> list[str]:
    """Every bundle part the export reads, plus each shipped directory's
    `NOTICE.md` and drawn-item licence text, as repository-relative paths in
    name order."""
    paths = bundle_export.default_bundle_paths()
    files = {_relative(p) for p in (paths.runtime_rows, paths.quality_rows)}
    files.add(_relative(paths.roster))
    directories = {
        paths.runtime_rows.parent,
        paths.roster.parent,
        paths.fiche_dir,
        paths.suite_definitions,
        paths.comparisons_dir,
        paths.leader_sets_dir,
    }
    for directory in sorted(directories):
        for name in (NOTICE_FILE, DRAWN_LICENCE_TEXT):
            if (repo_root / directory / name).is_file():
                files.add(_relative(directory / name))
    for directory in (
        paths.fiche_dir,
        paths.suite_definitions,
        paths.comparisons_dir,
        paths.leader_sets_dir,
    ):
        for path in (repo_root / directory).glob("*.json"):
            files.add(_relative(directory / path.name))
    missing = [name for name in sorted(files) if not (repo_root / name).is_file()]
    if missing:
        raise ArchiveError(f"bundle part(s) missing from the checkout: {missing}")
    return sorted(files)


def export_files(repo_root: Path) -> dict[str, bytes]:
    """The export regenerated from the committed bundle, file name to bytes.

    Run from the repository root so the manifest records repository-relative
    paths, the same paths the bundle parts take inside the archive.
    """
    try:
        with contextlib.chdir(repo_root):
            files = bundle_export.build_export(bundle_export.default_bundle_paths())
    except bundle_export.ExportError as error:
        raise ArchiveError(f"export refused: {error}") from error
    undescribed = sorted(set(files) - set(TABLE_DESCRIPTIONS))
    if undescribed:
        raise ArchiveError(f"no archive description for export file(s) {undescribed}")
    with tempfile.TemporaryDirectory() as scratch:
        out: dict[str, bytes] = {}
        for name, rows in files.items():
            path = Path(scratch) / name
            bundle_export.write_csv(path, rows)
            out[name] = path.read_bytes()
    return out


# --------------------------------------------------------------------------
# The release identity: tag, packaged version, citation version, commit.
# --------------------------------------------------------------------------


def head_commit(repo_root: Path) -> str | None:
    """The checkout's `HEAD` commit, or None when git cannot answer."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return result.stdout.strip() or None


def citation_version(text: str) -> str | None:
    match = CITATION_VERSION_RE.search(text)
    return match.group("version") if match else None


def release_version(tag: str, commit: str, repo_root: Path) -> str:
    """The version `tag` names, once the tag, the packaged version, the
    repository `CITATION.cff` and the checked-out commit all agree."""
    match = TAG_RE.match(tag)
    if match is None:
        raise ArchiveError(f"tag {tag!r} is not a v<major>.<minor>.<patch> tag")
    version = match.group("version")
    problems = []
    packaged = build_info.version()
    if packaged != version:
        problems.append(f"tag {tag} names {version}, the package is {packaged}")
    cited = citation_version((repo_root / CITATION_FILE).read_text(encoding="utf-8"))
    if cited != version:
        problems.append(f"tag {tag} names {version}, CITATION.cff names {cited}")
    if not COMMIT_RE.match(commit):
        problems.append(f"commit {commit!r} is not a 40-hex sha")
    head = head_commit(repo_root)
    if head != commit:
        problems.append(f"commit {commit} is not the checked-out commit ({head})")
    if problems:
        raise ArchiveError("; ".join(problems))
    return version


# --------------------------------------------------------------------------
# The two files written for the archive: the stamped citation and the README.
# --------------------------------------------------------------------------

_CITATION_HEADER = """\
# How to cite this release. This is the repository's CITATION.cff at the
# commit below, with that commit stamped in; README.md beside it states the
# same citation as one string. LICENSE and LICENSE-DATA, beside it too, are
# the licences the `license` list names.
"""


def stamp_citation(text: str, commit: str) -> str:
    """The repository citation with its header comment replaced and `commit`
    inserted after `version`. The header points at repository files (its
    tests, the repository README), which the archive does not hold."""
    lines = text.splitlines(keepends=True)
    start = 0
    while start < len(lines) and lines[start].startswith("#"):
        start += 1
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("commit:"):
            raise ArchiveError("the repository CITATION.cff already names a commit")
        body.append(line)
        if line.startswith("version:"):
            body.append(f"commit: {commit}\n")
    if sum(line.startswith("version:") for line in body) != 1:
        raise ArchiveError("CITATION.cff must hold exactly one top-level version")
    return _CITATION_HEADER + "".join(body)


def readme_attribution(readme: str) -> str:
    """The repository README's attribution string, between its markers.

    `tests/test_citation.py` holds it equal to what `CITATION.cff` derives,
    so the archive copies it rather than deriving a second form.
    """
    start, end = readme.find(ATTRIBUTION_START), readme.find(ATTRIBUTION_END)
    if start < 0 or end < start:
        raise ArchiveError("the repository README has no attribution block")
    return readme[start + len(ATTRIBUTION_START) : end].strip()


def repository_url(citation: str) -> str:
    match = re.search(r"^repository-code: *(\S+)", citation, re.MULTILINE)
    if match is None:
        raise ArchiveError("CITATION.cff names no repository-code")
    return match.group(1).rstrip("/")


def manifest_versions(manifest: bytes) -> dict[str, str]:
    """`bundle_manifest.csv`'s `versions_read`, keyed by part."""
    rows = csv.DictReader(io.StringIO(manifest.decode("utf-8"), newline=""))
    return {row["part"]: row["versions_read"] for row in rows}


def _bundle_part_description(path: str) -> str:
    paths = bundle_export.default_bundle_paths()
    if path.rsplit("/", 1)[-1] == NOTICE_FILE:
        return "The licence notice for the directory it sits in."
    if path.rsplit("/", 1)[-1] == DRAWN_LICENCE_TEXT:
        return "The Apache-2.0 text of the drawn WMT24++ items the directory holds."
    described = {
        _relative(paths.runtime_rows): "The runtime rows, one JSON object per line.",
        _relative(paths.quality_rows): "The quality rows, one JSON object per line.",
        _relative(paths.roster): "The model roster the rows cite by roster_entry_id.",
        _relative(paths.fiche_dir): "A hardware fiche the rows cite by fiche_hash.",
        _relative(paths.suite_definitions): (
            "A suite definition the rows cite by suite_id and suite_version."
        ),
        _relative(paths.comparisons_dir): "A paired-comparison family record.",
        _relative(paths.leader_sets_dir): "A leader-set record.",
    }
    return described.get(path) or described[path.rsplit("/", 1)[0]]


def build_readme(
    *,
    tag: str,
    version: str,
    commit: str,
    source_url: str,
    attribution: str,
    exports: Mapping[str, bytes],
    bundle: Sequence[str],
    parquet: Sequence[str] = (),
    pyarrow_version: str | None = None,
) -> str:
    versions = manifest_versions(exports[bundle_export.MANIFEST_FILE])
    rows = [f"| `{name}` | {TABLE_DESCRIPTIONS[name]} |" for name in sorted(exports)]
    rows += [
        f"| `{name}` | Typed Parquet copy of `{name.removesuffix('.parquet')}.csv`; "
        "the CSV is right wherever the two could disagree. |"
        for name in parquet
    ]
    rows += [f"| `{path}` | {_bundle_part_description(path)} |" for path in bundle]
    rows += [
        f"| `{CITATION_FILE}` | How to cite this release, with its commit. |",
        "| `LICENSE` | The MIT License, covering the code. |",
        "| `LICENSE-DATA` | CC-BY 4.0 and the parts it covers, by path. |",
        f"| `{README_FILE}` | This file. |",
    ]
    not_shipped = [
        f"- {source_url}/{'tree' if path.endswith('/') else 'blob'}/{commit}/"
        f"{path}: {entry.reason}."
        if entry.tracked
        else f"- `{path.rsplit('/', 1)[-1]}` in {path.rsplit('/', 1)[0]}/: "
        f"{entry.reason}; no commit holds it, so there is no link."
        for path, entry in PATHS_NOT_SHIPPED.items()
    ]
    lines = [
        f"# {DIST_NAME} {version}: published results",
        "",
        f"- Release: `{tag}` (packaged version {version})",
        f"- Commit: `{commit}`",
        f"- Source at this commit: {source_url}/tree/{commit}",
        (
            "- Bundle schema version read: runtime rows "
            f"{versions['runtime_rows']}, quality rows {versions['quality_rows']} "
            "(from `bundle_manifest.csv`)"
        ),
        "",
        "Everything needed to read the tables is in this archive. They open",
        "in any spreadsheet; each row resolves its pointers into its own",
        "columns, so no join is needed. The tables are derived from the bundle",
        "beside them, never edited by hand: the release build regenerates them",
        "from the bundle at this commit and fails if any byte differs.",
        "",
        "## What each file is",
        "",
        "| File | What it is |",
        "| ---- | ---------- |",
        *rows,
        "",
        *_parquet_section(parquet, pyarrow_version),
        "## How to cite this release",
        "",
        f"{attribution} Commit {commit}.",
        "",
        f"`{CITATION_FILE}` holds the same citation for citation managers. If",
        "you changed the data, say so after the string.",
        "",
        "## Licences",
        "",
        "The code is MIT (`LICENSE`); the data is CC-BY 4.0 (`LICENSE-DATA`),",
        "except the items drawn from public benchmarks, which carry their own",
        "terms (`LICENSE-DATA` section 2): MInDS-14's under CC BY 4.0 with its",
        "attribution, WMT24++'s under Apache-2.0, whose text ships beside them",
        "as `LICENSE-APACHE-2.0.txt`. Each row names its item's licence in",
        "`item_licence`. `LICENSE-DATA` names the parts it covers by repository",
        "path; the ones this archive holds sit at those same paths.",
        "",
        "## Repository paths named here but not shipped",
        "",
        "A file in this archive names each path below; none is needed to read",
        "the tables. Each link opens it at this commit:",
        "",
        *not_shipped,
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Building and verifying.
# --------------------------------------------------------------------------


def _parquet_section(parquet: Sequence[str], pyarrow_version: str | None) -> list[str]:
    if not parquet:
        return []
    return [
        "## Parquet copies",
        "",
        "Each table also ships as a Parquet file of the same name, typed from",
        "the unit `column_dictionary.csv` gives each column; an empty CSV cell",
        "is a Parquet null. The release build reads every copy back and fails",
        "unless it equals its CSV cell by cell under those types. The CSV is",
        "the contract: wherever the two could disagree, the CSV is right.",
        f"The copies were written with pyarrow {pyarrow_version}.",
        "",
    ]


def expected_files(
    tag: str, commit: str, repo_root: Path, *, parquet: bool = False
) -> dict[str, bytes]:
    """Every archive entry, relative to its top folder, and its bytes; with
    `parquet`, one typed Parquet copy per table too."""
    version = release_version(tag, commit, repo_root)
    citation = (repo_root / CITATION_FILE).read_text(encoding="utf-8")
    readme = (repo_root / README_FILE).read_text(encoding="utf-8")
    exports = export_files(repo_root)
    bundle = bundle_files(repo_root)
    files: dict[str, bytes] = dict(exports)
    copies = release_parquet.build_copies(exports) if parquet else {}
    files.update(copies)
    files.update({path: (repo_root / path).read_bytes() for path in bundle})
    files.update({name: (repo_root / name).read_bytes() for name in LICENCE_FILES})
    files[CITATION_FILE] = stamp_citation(citation, commit).encode("utf-8")
    files[README_FILE] = build_readme(
        tag=tag,
        version=version,
        commit=commit,
        source_url=repository_url(citation),
        attribution=readme_attribution(readme),
        exports=exports,
        bundle=bundle,
        parquet=sorted(copies),
        pyarrow_version=release_parquet.pyarrow_version() if parquet else None,
    ).encode("utf-8")
    return files


def write_zip(path: Path, top: str, files: Mapping[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(f"{top}/{name}", date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[name])


def read_zip(path: Path, top: str) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            entries = {info.filename: archive.read(info) for info in archive.infolist()}
    except (OSError, zipfile.BadZipFile) as error:
        raise ArchiveError(
            f"{path.as_posix()} is not a readable zip: {error}"
        ) from error
    outside = sorted(name for name in entries if not name.startswith(f"{top}/"))
    if outside:
        raise ArchiveError(f"entries outside the {top}/ folder: {outside}")
    return {name[len(top) + 1 :]: data for name, data in entries.items()}


def _resolves(reference: str, names: frozenset[str]) -> bool:
    if reference in names:
        return True
    prefix = reference if reference.endswith("/") else f"{reference}/"
    return any(name.startswith(prefix) for name in names)


def clone_only_references(files: Mapping[str, bytes]) -> list[str]:
    """Each `file: path` where a file names a repository path the archive
    does not hold, outside the reviewed `PATHS_NOT_SHIPPED`. Parquet copies
    are binary and proven equal to their CSV, which is read here instead."""
    names = frozenset(files)
    found = []
    for name in sorted(files):
        if name.endswith(".parquet"):
            continue
        text = files[name].decode("utf-8", errors="replace")
        for match in REPOSITORY_PATH_RE.finditer(text):
            reference = match.group(0).rstrip(".")
            if _resolves(reference, names):
                continue
            exception = PATHS_NOT_SHIPPED.get(reference)
            if exception is not None and name in exception.named_by:
                continue
            found.append(f"{name}: {reference}")
    return sorted(set(found))


def _identity_problems(files: Mapping[str, bytes], tag: str, commit: str) -> list[str]:
    version = tag[1:]
    readme = files.get(README_FILE, b"").decode("utf-8")
    citation = files.get(CITATION_FILE, b"").decode("utf-8")
    release = README_RELEASE_RE.search(readme)
    named_commit = README_COMMIT_RE.search(readme)
    stamped = CITATION_COMMIT_RE.search(citation)
    problems = []
    if release is None or release.group("tag") != version:
        problems.append(f"the archive README does not name release {tag}")
    if release is None or release.group("version") != version:
        problems.append(f"the archive README does not name version {version}")
    if named_commit is None or named_commit.group("commit") != commit:
        problems.append(f"the archive README does not name commit {commit}")
    if citation_version(citation) != version:
        problems.append(f"the archive CITATION.cff does not name version {version}")
    if stamped is None or stamped.group("commit") != commit:
        problems.append(f"the archive CITATION.cff is not stamped with {commit}")
    return problems


def verify(
    archive: Path,
    tag: str,
    commit: str,
    repo_root: Path = REPO_ROOT,
    *,
    parquet: bool = False,
) -> list[str]:
    """Raise `ArchiveError` naming every way `archive` is not the release
    archive this checkout derives for `tag` at `commit`; return one line per
    Parquet copy compared with its CSV and found equal."""
    expected = expected_files(tag, commit, repo_root, parquet=parquet)
    actual = read_zip(archive, archive_name(tag[1:]))
    problems = []
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing:
        problems.append(f"missing: {missing}")
    if extra:
        problems.append(f"not expected: {extra}")
    for name in sorted(set(expected) & set(actual)):
        if expected[name] != actual[name]:
            kind = "table" if name in TABLE_DESCRIPTIONS else "file"
            problems.append(
                f"{kind} {name} differs from what the bundle at {commit} derives"
            )
    problems += _identity_problems(actual, tag, commit)
    problems += [
        f"names a path only a clone holds: {ref}"
        for ref in clone_only_references(actual)
    ]
    compared: list[str] = []
    if parquet:
        found, compared = release_parquet.compare_copies(actual)
        problems += found
    if problems:
        raise ArchiveError("; ".join(problems))
    return compared


def build(
    tag: str,
    commit: str,
    output_dir: Path,
    repo_root: Path = REPO_ROOT,
    *,
    parquet: bool = False,
) -> tuple[Path, list[str]]:
    """Write the archive into `output_dir` and verify it; return its path and
    `verify`'s Parquet comparison lines."""
    files = expected_files(tag, commit, repo_root, parquet=parquet)
    top = archive_name(tag[1:])
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{top}.zip"
    write_zip(path, top, files)
    return path, verify(path, tag, commit, repo_root, parquet=parquet)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or verify the release archive that needs no clone."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--tag", required=True)
        command.add_argument("--commit", required=True)
        command.add_argument(
            "--parquet",
            action="store_true",
            help="also ship (build) or check (verify) one Parquet copy per table",
        )
        if name == "build":
            command.add_argument("--output-dir", type=Path, required=True)
        else:
            command.add_argument("archive", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            path, compared = build(
                args.tag, args.commit, args.output_dir, parquet=args.parquet
            )
            done = f"built and verified {path.as_posix()}"
        else:
            compared = verify(args.archive, args.tag, args.commit, parquet=args.parquet)
            done = f"verified {args.archive.as_posix()}"
    except (ArchiveError, release_parquet.ParquetError) as error:
        print(f"release archive refused: {error}", file=sys.stderr)
        return 1
    for line in compared:
        print(line)
    print(done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
