"""Constructed bundles, one per rung of LICENSE-DATA section 2, each laid out
as a repository root the release archive can be built from.

Both live drawn sources are permissive (MInDS-14 under CC BY 4.0, WMT24++
under Apache-2.0), so the share-alike and no-redistribution rungs have no
live case: they are built here from a handful of committed rows relabelled
to fictional `example/...` sources. Every bundle also holds one hand-written
row, and the permissive bundle keeps its MInDS-14 and WMT24++ rows as
published.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import bundle_export, subset_sampler
from wave_local_ai_v2.suite_snapshot import snapshot_filename

REPO = Path(__file__).resolve().parents[1]
PATHS = bundle_export.default_bundle_paths()
RESULTS = PATHS.quality_rows.parent
MINDS14 = ("classification-banking-intents-minds14", "1")
WMT24PP = ("translation-mixed-domain-wmt24pp", "1")
APACHE_TEXT = "LICENSE-APACHE-2.0.txt"
NOTICE = "NOTICE.md"

PERMISSIVE = "permissive"
SHARE_ALIKE = "share-alike"
NO_REDISTRIBUTION = "no redistribution"

SHARE_ALIKE_SOURCE = "example/share-alike-corpus"
SHARE_ALIKE_LICENCE = "CC-BY-SA-4.0"
SHARE_ALIKE_TEXT = "Constructed stand-in for the CC BY-SA 4.0 legal code.\n"
CLOSED_SOURCE = "example/closed-corpus"
CLOSED_LICENCE = "LicenseRef-closed-corpus"
CLOSED_REVISION = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret


@dataclass
class Constructed:
    """A constructed repository root and what a test needs to know of it."""

    root: Path
    rung: str
    # The redacted items' source rows, as a reader would fetch them.
    source_rows: list[dict[str, Any]] = field(default_factory=list)
    # Text that must appear in no archive file (the redacted items').
    withheld_text: list[str] = field(default_factory=list)

    @property
    def paths(self) -> bundle_export.BundlePaths:
        """The bundle paths, absolute under the constructed root."""
        default = bundle_export.default_bundle_paths()
        assert default.share_alike_dir is not None
        return bundle_export.BundlePaths(
            runtime_rows=self.root / default.runtime_rows,
            quality_rows=self.root / default.quality_rows,
            fiche_dir=self.root / default.fiche_dir,
            roster=self.root / default.roster,
            suite_definitions=self.root / default.suite_definitions,
            comparisons_dir=self.root / default.comparisons_dir,
            leader_sets_dir=self.root / default.leader_sets_dir,
            share_alike_dir=self.root / default.share_alike_dir,
        )


def _rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (REPO / path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _snapshot(pair: tuple[str, str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The committed snapshot of `pair`, trimmed to the items `rows` score."""
    definition: dict[str, Any] = json.loads(
        (REPO / PATHS.suite_definitions / snapshot_filename(*pair)).read_text(
            encoding="utf-8"
        )
    )
    cited = {row["item_id"] for row in rows}
    definition["items"] = [i for i in definition["items"] if i["item_id"] in cited]
    return definition


def _pick(rows: list[dict[str, Any]], pair: tuple[str, str], n: int) -> list[dict]:
    return [r for r in rows if (r["suite_id"], r["suite_version"]) == pair][:n]


def _subsection(number: int, title: str, source: str, licence: str, rung: str) -> str:
    return (
        f"### 2.{number} {title}\n\n"
        f"- Source: `{source}`, constructed for the tests.\n"
        f"- Licence: {licence}.\n"
        f"- Rung: {rung}. Constructed: no live source sits on this rung.\n\n"
    )


def _licence_data(extra: str) -> str:
    text = (REPO / "LICENSE-DATA").read_text(encoding="utf-8")
    if not extra:
        return text
    head, tail = text.split("\n## 3.", 1)
    return head.rstrip("\n") + "\n\n" + extra + "\n## 3." + tail


def _copy(name: Path | str, root: Path) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / name, target)


def _relabel(record: dict[str, Any], source: str, licence: str) -> None:
    for key, value in (("source", source), ("licence", licence)):
        if key in record:
            record[key] = value
    if "item_source" in record:
        record["item_source"] = source
        record["item_licence"] = licence


def build_repo(root: Path, rung: str) -> Constructed:
    """A repository root at `root` holding a constructed bundle on `rung`."""
    root.mkdir(parents=True, exist_ok=True)
    quality = _rows(PATHS.quality_rows)
    hand_written = next(r for r in quality if r["provenance"] == "hand_written")
    hand_pair = (hand_written["suite_id"], hand_written["suite_version"])
    minds = _pick(quality, MINDS14, 2)
    wmt = _pick(quality, WMT24PP, 2)
    runtime = _rows(PATHS.runtime_rows)[:1]
    constructed = Constructed(root, rung)
    suites = {
        hand_pair: _snapshot(hand_pair, [hand_written]),
        MINDS14: _snapshot(MINDS14, minds),
        WMT24PP: _snapshot(WMT24PP, wmt),
    }
    extra = ""
    share_alike: list[dict[str, Any]] = []

    if rung == SHARE_ALIKE:
        share_alike = wmt
        wmt = []
        definition = suites.pop(WMT24PP)
        for record in (*share_alike, *definition["items"]):
            _relabel(record, SHARE_ALIKE_SOURCE, SHARE_ALIKE_LICENCE)
        for benchmark in definition["selection_rule"]["benchmarks"]:
            _relabel(benchmark, SHARE_ALIKE_SOURCE, SHARE_ALIKE_LICENCE)
        # A fictional source has no loader in this repository.
        definition["source_table"]["loader_script"] = "constructed, none"
        assert PATHS.share_alike_dir is not None
        directory = root / PATHS.share_alike_dir / SHARE_ALIKE_LICENCE
        _write_rows(directory / bundle_export.SHARE_ALIKE_ROWS, share_alike)
        _write_json(
            directory / bundle_export.SHARE_ALIKE_SUITES / snapshot_filename(*WMT24PP),
            definition,
        )
        (directory / bundle_export.SHARE_ALIKE_LICENCE).write_text(
            SHARE_ALIKE_TEXT, encoding="utf-8", newline="\n"
        )
        extra = _subsection(
            3, "Share-alike corpus", SHARE_ALIKE_SOURCE, "CC BY-SA 4.0", SHARE_ALIKE
        )
    elif rung == NO_REDISTRIBUTION:
        _redact(constructed, minds, suites[MINDS14])
        extra = _subsection(
            3, "Closed corpus", CLOSED_SOURCE, CLOSED_LICENCE, NO_REDISTRIBUTION
        )

    _write_rows(root / PATHS.quality_rows, [hand_written, *minds, *wmt])
    _write_rows(root / PATHS.runtime_rows, runtime)
    for pair, definition in suites.items():
        _write_json(
            root / PATHS.suite_definitions / snapshot_filename(*pair), definition
        )
    for row in [hand_written, *minds, *wmt, *share_alike, *runtime]:
        _copy(PATHS.fiche_dir / f"{row['fiche_hash']}.json", root)
    _copy(PATHS.roster, root)
    for directory in (
        RESULTS,
        PATHS.suite_definitions,
        PATHS.fiche_dir,
        PATHS.roster.parent,
        PATHS.comparisons_dir,
        PATHS.leader_sets_dir,
    ):
        for name in (NOTICE, APACHE_TEXT):
            if (REPO / directory / name).is_file():
                _copy(directory / name, root)
    for name in ("CITATION.cff", "README.md", "LICENSE"):
        _copy(name, root)
    (root / "LICENSE-DATA").write_text(
        _licence_data(extra), encoding="utf-8", newline="\n"
    )
    return constructed


def _redact(
    constructed: Constructed,
    rows: list[dict[str, Any]],
    definition: dict[str, Any],
) -> None:
    """Move `rows` and their items to the closed source and withhold their
    text, the hash computed from a fixture source row per item."""
    rule = definition["selection_rule"]
    benchmark = subset_sampler.Benchmark(CLOSED_SOURCE, CLOSED_LICENCE, CLOSED_REVISION)
    rule["benchmarks"] = [
        {
            "source": CLOSED_SOURCE,
            "licence": CLOSED_LICENCE,
            "source_revision": CLOSED_REVISION,
        }
    ]
    items = {item["item_id"]: item for item in definition["items"]}
    definition["items"] = []
    for row in rows:
        item = items[row["item_id"]]
        key = row["item_id"].split(":", 1)[1]
        transcription = item["prompt"].rsplit("Message: ", 1)[1]
        source_row = {
            "source": CLOSED_SOURCE,
            rule["stable_source_key"]: key,
            "language": item["language"],
            "transcription": f"  {transcription}\n",
            "intent_class": item["expected_label"],
        }
        digest = subset_sampler.content_hash(
            source_row, rule["content_fields"], benchmark
        )
        constructed.source_rows.append(source_row)
        constructed.withheld_text.append(transcription)
        item_id = subset_sampler.drawn_item_id(CLOSED_SOURCE, key)
        definition["items"].append(
            {
                "item_id": item_id,
                "language": item["language"],
                "provenance": "public",
                "contamination_risk": True,
                "licence": CLOSED_LICENCE,
                "source": CLOSED_SOURCE,
                "source_revision": CLOSED_REVISION,
                "content_hash": digest,
                "source_key": key,
                "redaction": bundle_export.NO_REDISTRIBUTION,
            }
        )
        row.update(
            {
                "item_id": item_id,
                "item_licence": CLOSED_LICENCE,
                "item_source": CLOSED_SOURCE,
                "item_source_revision": CLOSED_REVISION,
                "item_redaction": bundle_export.NO_REDISTRIBUTION,
                "item_content_hash": digest,
                "item_source_key": key,
            }
        )
        for name in bundle_export.ITEM_TEXT_ROW_FIELDS:
            if name in row:
                row[name] = None
