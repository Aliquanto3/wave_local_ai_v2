"""The WMT24++ loader and draw, over a constructed table (no download).

The live fetch is the operator's (`scripts/wmt24pp_suite.py verify`): CI
replays the draw over pair files built here in WMT24++'s shape, so the join,
the `is_bad_source` exclusion, the direction assignment, the table's hash,
the draw, the derived output cap and the replay are all checked without a
network (owner answer Q132 (a)).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hub_source
import wmt24pp_suite as loader

from wave_local_ai_v2 import roster, settings, subset_replay, suite_registry

DOMAINS = ("literary", "news", "social", "speech")
_REVISION = "fd7405c06494bc66a57b25f55d217a72f96e60dc"  # pragma: allowlist secret
_TABLE_SHA256 = "db57a8a457dce9ae2f38e0b4595a582bf9bf471475dc545b3b4bc89e2546f4ed"  # pragma: allowlist secret
TOKENIZER = "the tokenizer of fixture-model (fixture.gguf), counted by a stub"


def _pair_rows(pair: str, segments: int = 420) -> list[dict[str, Any]]:
    """One WMT24++ pair file: the canary first, then `segments - 1` segments,
    every tenth a bad source."""
    language = loader.PAIRS[pair]
    rows = []
    for segment_id in range(segments):
        canary = segment_id == 0
        rows.append(
            {
                "lp": pair,
                "domain": "canary" if canary else DOMAINS[segment_id % 4],
                "document_id": f"doc_{segment_id // 5}",
                "segment_id": segment_id,
                "is_bad_source": canary or segment_id % 10 == 7,
                "source": f"English segment {segment_id}.",
                "target": f"{language} segment {segment_id}.",
                "original_target": f"{language} original {segment_id}.",
            }
        )
    return rows


def _files() -> dict[str, list[dict[str, Any]]]:
    return {pair: _pair_rows(pair) for pair in loader.PAIRS}


def _rows() -> list[dict[str, Any]]:
    return loader.source_rows(loader.join_pairs(_files()))


def _record(rows: list[dict[str, Any]], licence_paths: tuple[str, ...] = ()) -> dict:
    return loader.fetch_record(
        loader.table_text(rows),
        rows,
        files={"en-fr_FR.jsonl": "0" * 40, "en-de_DE.jsonl": "1" * 40},
        licence_paths=licence_paths,
    )


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tokenizer": TOKENIZER,
        "counts": {str(row["segment_id"]): 3 + row["segment_id"] % 17 for row in rows},
    }


def test_the_join_drops_every_bad_source_the_canary_included() -> None:
    segments = loader.join_pairs(_files())
    ids = [segment["segment_id"] for segment in segments]

    assert 0 not in ids
    assert not any(segment_id % 10 == 7 for segment_id in ids)
    assert len(ids) == 420 - 1 - 42
    assert segments[0] == {
        "segment_id": 1,
        "domain": "news",
        "document_id": "doc_0",
        "en": "English segment 1.",
        "fr": "fr segment 1.",
        "de": "de segment 1.",
    }


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        (lambda files: files["en-de_DE"].pop(), "not aligned"),
        (lambda files: files["en-fr_FR"].append(files["en-fr_FR"][3]), "twice"),
        (
            lambda files: files["en-de_DE"][5].update(source="moved"),
            "disagree on source",
        ),
        (
            lambda files: files["en-de_DE"][5].update(is_bad_source=True),
            "disagree on is_bad_source",
        ),
    ],
)
def test_pair_files_that_do_not_join_are_refused(edit, match) -> None:
    files = _files()
    edit(files)

    with pytest.raises(loader.LoaderError, match=match):
        loader.join_pairs(files)


def test_each_segment_is_in_one_direction_with_its_target_side_as_reference() -> None:
    rows = _rows()
    by_direction: dict[tuple[str, str], set[int]] = {}
    for row in rows:
        direction = (row["language"], row["target_language"])
        assert direction == loader.direction_of(row["segment_id"])
        by_direction.setdefault(direction, set()).add(row["segment_id"])
        segment_id = row["segment_id"]
        language = {"en": "English", "fr": "fr", "de": "de"}
        assert row["source_text"].startswith(language[row["language"]])
        assert row["reference"].startswith(language[row["target_language"]])
        assert row["reference"].endswith(f" {segment_id}.")

    assert set(by_direction) == set(loader.DIRECTIONS)
    first, second, third = by_direction.values()
    assert not (first & second or second & third or first & third)
    # The hand-written suite's cycle: EN->FR, FR->DE, DE->EN.
    en_fr = next(row for row in rows if row["language"] == "en")
    assert en_fr["reference"] == f"fr segment {en_fr['segment_id']}."
    fr_de = next(row for row in rows if row["language"] == "fr")
    assert fr_de["reference"] == f"de segment {fr_de['segment_id']}."
    de_en = next(row for row in rows if row["language"] == "de")
    assert de_en["reference"] == f"English segment {de_en['segment_id']}."


def test_the_table_and_its_hash_do_not_depend_on_row_order() -> None:
    rows = _rows()
    shuffled = rows[:]
    random.Random(5).shuffle(shuffled)

    text = loader.table_text(rows)
    record = _record(rows)

    assert text == loader.table_text(shuffled)
    assert record["table_sha256"] == hub_source.sha256_hex(text.encode("utf-8"))
    assert record["row_count"] == len(rows) == 377
    assert list(record["pool_per_direction"]) == ["en->fr", "fr->de", "de->en"]
    assert sum(record["pool_per_direction"].values()) == len(rows)


def test_a_file_is_checked_against_the_git_object_id_the_tree_records(
    tmp_path: Path, monkeypatch
) -> None:
    # `git hash-object` of "hello\n".
    assert hub_source.git_blob_sha1(b"hello\n") == (
        "ce013625030ba8dba906f756967f9e9ca394464a"  # pragma: allowlist secret
    )
    tree = [{"type": "file", "path": "en-fr_FR.jsonl", "oid": "a" * 40}]
    assert loader.file_oid(tree, "en-fr_FR.jsonl") == "a" * 40
    with pytest.raises(loader.LoaderError, match="LFS"):
        loader.file_oid([{**tree[0], "lfs": {"oid": "b" * 64}}], "en-fr_FR.jsonl")
    with pytest.raises(loader.LoaderError, match="not in the tree"):
        loader.file_oid(tree, "en-de_DE.jsonl")

    class _Response:
        content = b"moved\n"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(loader.requests, "get", lambda url, timeout: _Response())
    dest = tmp_path / "en-fr_FR.jsonl"
    expected = hub_source.git_blob_sha1(b"moved\n")
    assert loader.download("en-fr_FR.jsonl", dest, expected) == b"moved\n"
    assert dest.read_bytes() == b"moved\n"
    with pytest.raises(loader.LoaderError, match="is not the Hub's"):
        loader.download("en-fr_FR.jsonl", tmp_path / "other.jsonl", "c" * 40)


def test_token_counts_come_from_the_served_tokenizer(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    class _Response:
        def __init__(self, body: dict[str, Any]) -> None:
            self.body = body

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self.body

    def get(url: str, timeout: int) -> _Response:
        assert url == "http://server/props"
        return _Response(
            {"model_path": "D:\\models\\m\\m-Q8_0.gguf", "build_info": "b1-abc"}
        )

    def post(url: str, json: dict[str, Any], timeout: int) -> _Response:
        assert url == "http://server/tokenize"
        calls.append(json)
        return _Response({"tokens": list(range(len(json["content"].split())))})

    monkeypatch.setattr(loader.requests, "get", get)
    monkeypatch.setattr(loader.requests, "post", post)
    rows = _rows()[:3]

    counted = loader.count_tokens(rows, "http://server/", "entry-id")

    assert counted["counts"] == {str(row["segment_id"]): 3 for row in rows}
    assert {call["add_special"] for call in calls} == {False}
    assert counted["tokenizer"] == (
        "the tokenizer of entry-id (m-Q8_0.gguf), counted by llama-server b1-abc "
        "/tokenize without special tokens"
    )


def _draw(tmp_path: Path, rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    table = tmp_path / "wmt24pp.jsonl"
    table.write_bytes(loader.table_text(rows).encode("utf-8"))
    record = tmp_path / "record.json"
    record.write_text(json.dumps(_record(rows)), encoding="utf-8")
    counts = tmp_path / "counts.json"
    counts.write_text(json.dumps(_counts(rows)), encoding="utf-8")
    out = tmp_path / "definition.json"
    argv = ["draw", "--table", str(table), "--record", str(record)]
    argv += ["--token-counts", str(counts), "--out", str(out)]
    assert loader.main(argv) == 0
    return table, out


def test_the_draw_certifies_at_publication_and_replays_to_its_ids(
    tmp_path: Path, capsys
) -> None:
    rows = _rows()
    table, out = _draw(tmp_path, rows)
    definition = suite_registry.load_definition(out)

    assert definition.gate["level"] == "publication"
    assert definition.gate["language_counts"] == {"en": 100, "fr": 100, "de": 100}
    assert definition.extra["source_table"]["sha256"] == hub_source.sha256_hex(
        table.read_bytes()
    )
    assert definition.extra["selection_rule"]["stratify_by"] == ["language"]
    segment_ids = [item["item_id"].split(":", 1)[1] for item in definition.items]
    assert len(set(segment_ids)) == 300
    for item in definition.items:
        assert item["contamination_risk"] is True
        assert item["domain"] in DOMAINS
        assert (item["language"], item["target_language"]) == loader.direction_of(
            int(item["item_id"].split(":", 1)[1])
        )
        assert item["prompt"].endswith(f"\n\nText: {item['source_text']}")
    longest = max(item["reference_tokens"] for item in definition.items)
    assert definition.max_output_tokens == 2 * longest
    basis = definition.extra["max_output_tokens_basis"]
    assert (basis["tokenizer"], basis["longest_reference_tokens"]) == (
        TOKENIZER,
        longest,
    )
    assert TOKENIZER in basis["reason"]
    capsys.readouterr()
    assert subset_replay.main(["--definition", str(out), "--source", str(table)]) == 0
    assert "reproduced: 300 items" in capsys.readouterr().out


def test_a_draw_without_a_reference_count_or_with_a_licence_file_is_refused() -> None:
    rows = _rows()
    counts = _counts(rows)
    counts["counts"] = {}

    with pytest.raises(loader.LoaderError, match="no reference token count"):
        loader.build_definition(rows, _record(rows), counts)
    with pytest.raises(loader.LoaderError, match="reopens the spike"):
        loader.build_definition(
            rows, _record(rows, licence_paths=("LICENSE",)), _counts(rows)
        )


def test_a_draw_from_an_unreadable_table_is_refused(tmp_path: Path, capsys) -> None:
    missing = str(tmp_path / "absent.json")
    argv = ["draw", "--table", missing, "--record", missing]
    argv += ["--token-counts", missing, "--out", str(tmp_path / "out.json")]

    assert loader.main(argv) == 1
    assert "refused:" in capsys.readouterr().err


def test_the_committed_suite_certifies_at_publication_with_its_recorded_draw() -> None:
    definition = suite_registry.resolve(loader.SUITE_ID)
    rule = definition.extra["selection_rule"]

    assert definition.suite_version == loader.SUITE_VERSION
    assert definition.level == definition.gate["level"] == "publication"
    assert len(definition.items) == definition.extra["size_target"] == 300
    assert definition.extra["size_target_reason"]
    assert definition.gate["language_counts"] == {"en": 100, "fr": 100, "de": 100}
    assert min(definition.gate["language_shares"].values()) >= 0.25
    assert rule["benchmarks"] == [
        {
            "source": "google/wmt24pp",
            "licence": "Apache-2.0",
            "source_revision": _REVISION,
        }
    ]
    assert (rule["stable_source_key"], rule["size"]) == ("segment_id", 300)
    assert rule["stratify_by"] == ["language"]
    assert rule["content_fields"] == ["source_text", "reference"]
    assert definition.extra["source_table"] == {
        "sha256": _TABLE_SHA256,
        "row_count": 960,
        "loader_script": loader.LOADER_SCRIPT,
        "licence_file_at_revision": False,
        "licence_of_record": loader.LICENCE_OF_RECORD,
    }
    assert loader.REVISION == _REVISION
    segments = set()
    for item in definition.items:
        segment_id = int(item["item_id"].removeprefix("google/wmt24pp:"))
        segments.add(segment_id)
        assert (item["provenance"], item["contamination_risk"]) == ("public", True)
        assert (item["licence"], item["source"], item["source_revision"]) == (
            "Apache-2.0",
            "google/wmt24pp",
            _REVISION,
        )
        assert len(item["content_hash"]) == 64
        assert item["domain"] in DOMAINS
        assert (item["language"], item["target_language"]) == loader.direction_of(
            segment_id
        )
        assert item["prompt"] == loader.prompt_for(item)
    assert len(segments) == 300


def test_the_committed_cap_is_twice_the_longest_reference_under_the_subjects_tokenizer() -> (
    None
):
    definition = suite_registry.resolve(loader.SUITE_ID)
    basis = definition.extra["max_output_tokens_basis"]
    counts = [item["reference_tokens"] for item in definition.items]

    assert definition.max_output_tokens >= 2 * max(counts)
    assert basis["longest_reference_tokens"] == max(counts)
    assert basis["factor"] == 2
    assert basis["tokenizer"] in basis["reason"]
    # A byte-level BPE token covers at least one byte, so no recorded count can
    # exceed its reference's UTF-8 length: a bound CI checks without the model.
    for item in definition.items:
        assert 0 < item["reference_tokens"] <= len(item["reference"].encode("utf-8"))
    # The tokenizer is the published batches' model's: its roster entry and
    # GGUF file are the ones named.
    entry = roster.resolve_entry(
        roster.load_roster(Path(settings.DEFAULT_ROSTER_PATH)), "granite-4.0-h-350m-q8"
    )
    assert "granite-4.0-h-350m-q8" in basis["tokenizer"]
    assert Path(entry.file).name in basis["tokenizer"]


def test_the_hand_written_suite_keeps_its_id_items_licence_and_level() -> None:
    hand_written = suite_registry.resolve("translation-business-short-form")

    assert hand_written.level == "development"
    assert hand_written.max_output_tokens == 128
    assert len(hand_written.items) == 21
    assert {item["licence"] for item in hand_written.items} == {"CC-BY-4.0"}
    assert {item["provenance"] for item in hand_written.items} == {"hand_written"}


README = Path(__file__).resolve().parent.parent / "aidd_docs/results/README.md"


def test_the_readme_per_domain_counts_are_the_definitions() -> None:
    section = README.read_text(encoding="utf-8").split(
        "## Drawn items: WMT24++ on the permissive rung", 1
    )[1]
    table = section.split("| Domain | EN->FR | FR->DE | DE->EN | Total |", 1)[1]
    published = {}
    for line in table.strip().splitlines()[1:]:
        if not line.startswith("|"):
            break
        domain, *cells = (cell.strip() for cell in line.strip("|").split("|"))
        published[domain] = [int(cell) for cell in cells]
    counts = loader.domain_counts(suite_registry.resolve(loader.SUITE_ID).items)
    expected = {
        domain: [*per_direction.values(), sum(per_direction.values())]
        for domain, per_direction in counts.items()
    }
    expected["all"] = [sum(column) for column in zip(*expected.values(), strict=True)]

    assert published == expected
    assert list(next(iter(counts.values()))) == ["en->fr", "fr->de", "de->en"]
