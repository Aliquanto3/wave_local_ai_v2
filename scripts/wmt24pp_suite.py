"""Load WMT24++ at its pinned revision and draw the publication translation suite.

`uv run python scripts/wmt24pp_suite.py fetch --out TABLE.jsonl --record
RECORD.json [--cache DIR]`
    Downloads `en-fr_FR.jsonl` and `en-de_DE.jsonl` of `google/wmt24pp` at
    the pinned revision, checks each against the git object id the Hub's
    tree listing records for it, joins the two on `segment_id`, drops every
    segment whose `is_bad_source` is true (the canary included), assigns
    each remaining segment to exactly one direction (`direction_of`), and
    writes the JSONL source table `subset_replay` reads: one row per
    segment, carrying `source`, `language` (the direction's source
    language), `target_language`, the stable key `segment_id`, `source_text`,
    `reference`, `domain` and `document_id`. The record states the table's
    SHA-256, its row count, the post-filter pool size per direction, each
    file's git object id, and whether the revision ships a licence file.

`uv run python scripts/wmt24pp_suite.py count-tokens --table TABLE.jsonl
--server URL --roster-entry ID --out COUNTS.json`
    Counts every pool reference's tokens with the tokenizer of the model a
    running `llama-server` at URL serves (`/tokenize`, no special tokens),
    for the `max_output_tokens` the draw derives. The server is the
    operator's, started on the subject's GGUF and stopped after.

`uv run python scripts/wmt24pp_suite.py draw --table TABLE.jsonl --record
RECORD.json --token-counts COUNTS.json --out DEFINITION.json`
    Draws the 300-item subset with `subset_sampler` (stratified by language
    only, accepted only where it certifies at `publication`), wraps each
    drawn source text in the hand-written suite's prompt shell, sets
    `max_output_tokens` to twice the longest drawn reference's token count,
    and writes the suite definition with its selection rule, the source
    table's SHA-256 and the cap's basis.

`uv run python scripts/wmt24pp_suite.py verify [--cache DIR]`
    The operator replay: re-fetches the table from the pinned revision,
    checks its SHA-256 against the one the registered suite records, then
    replays the suite's selection rule over it (`subset_replay`). Exit 0
    only when both hold.

The join, the `is_bad_source` exclusion, the direction assignment and the
pool sizes live here, in the loader: the selection rule records only the
loader library and version (`subset_sampler.RULE_KEYS` is closed). The two
files are read with the standard library's `json`.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath
from typing import Any

import hub_source
import requests
from hub_source import (
    RESOLVE_URL,
    LoaderError,
    definition_text,
    fetch_tree,
    git_blob_sha1,
    licence_files,
    sha256_hex,
    verify_table,
    write_text,
)

from wave_local_ai_v2 import subset_replay, subset_sampler, suite_gate, suite_registry

REPO_ID = "google/wmt24pp"
REVISION = "fd7405c06494bc66a57b25f55d217a72f96e60dc"  # pragma: allowlist secret
# The pair files the suite draws from, and the target language each holds.
PAIRS = {"en-fr_FR": "fr", "en-de_DE": "de"}
PAIR_FILE = "{pair}.jsonl"
# The three directions, as (source language, target language), indexed by
# `segment_id % 3`: the hand-written suite's cycle.
DIRECTIONS = (("en", "fr"), ("fr", "de"), ("de", "en"))
LANGUAGE_NAMES = {"en": "English", "fr": "French", "de": "German"}
# The fields every joined segment must carry the same value for in both files.
_SHARED_FIELDS = ("source", "domain", "document_id", "is_bad_source")

# The card's `license: apache-2.0`, as the item licence identifier.
LICENCE = "Apache-2.0"
STABLE_KEY = "segment_id"
SOURCE_TEXT_FIELD = "source_text"
REFERENCE_FIELD = "reference"
SIZE = suite_gate.PUBLICATION_SIZE_TARGETS[-1]
FIRST_SEED = 20261004
CAP_FACTOR = 2

SUITE_ID = "translation-mixed-domain-wmt24pp"
SUITE_VERSION = "1"
LOADER_SCRIPT = "scripts/wmt24pp_suite.py"
LOADER = subset_sampler.Loader(
    "CPython json", f"{sys.version_info.major}.{sys.version_info.minor}"
)
DIVERGENCE_TOLERANCE = {
    "value": 0.1,
    "unit": suite_gate.TOLERANCE_UNIT_FRACTION_OF_ITEMS,
    "reason": (
        "Provisional, not yet set against an observed cloud re-run of this "
        "suite: none is published, and no paid call was made when it was "
        "declared. It mirrors the hand-written translation suite's 0.10 (30 "
        "of 300 items whose chrF item_score differs) until a Mistral or "
        "Google re-run of this suite against its published reference is "
        "observed and the value is re-set against it."
    ),
}
LICENCE_OF_RECORD = (
    "The Hugging Face dataset card of google/wmt24pp at the pinned revision "
    "(YAML license: apache-2.0); the revision ships no licence or NOTICE "
    "file. The English sources are the WMT24 general test set's, which WMT "
    "released for research use: the items rest on Google's Apache-2.0 label "
    "(LICENSE-DATA section 3)."
)
PROMPT_TEMPLATE = (
    "Translate the following {source} text into {target}. Reply with only the "
    "translation, nothing else.\n\nText: {text}"
)


# --- pure: join, filter, directions, table, record -----------------------------


def direction_of(segment_id: int) -> tuple[str, str]:
    """The one direction a segment is drawn in: `segment_id % 3` indexes
    `DIRECTIONS`, so no segment is ever in two."""
    return DIRECTIONS[segment_id % len(DIRECTIONS)]


def join_pairs(
    files: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """The two pair files joined on `segment_id`, bad sources dropped.

    Each joined segment carries `segment_id`, `domain`, `document_id` and
    its text per language (`en` from the shared `source`, then each pair's
    `target`). Refused: a segment one file lacks, a segment id twice in one
    file, or a shared field the two files disagree on.
    """
    by_pair: dict[str, dict[int, Mapping[str, Any]]] = {}
    for pair in PAIRS:
        rows: dict[int, Mapping[str, Any]] = {}
        for row in files[pair]:
            segment_id = row[STABLE_KEY]
            if segment_id in rows:
                raise LoaderError(f"{pair} holds segment {segment_id} twice")
            rows[segment_id] = row
        by_pair[pair] = rows
    first, second = (by_pair[pair] for pair in PAIRS)
    if first.keys() != second.keys():
        unmatched = sorted(first.keys() ^ second.keys())
        raise LoaderError(
            f"the pair files are not aligned on segment_id: {unmatched[:5]} "
            "is in one file only"
        )
    joined = []
    for segment_id in sorted(first):
        left, right = first[segment_id], second[segment_id]
        for field in _SHARED_FIELDS:
            if left[field] != right[field]:
                raise LoaderError(
                    f"segment {segment_id}: the pair files disagree on {field}"
                )
        if left["is_bad_source"]:
            continue
        segment = {
            STABLE_KEY: segment_id,
            "domain": left["domain"],
            "document_id": left["document_id"],
            "en": left["source"],
        }
        for pair, language in PAIRS.items():
            segment[language] = by_pair[pair][segment_id]["target"]
        joined.append(segment)
    return joined


def source_rows(segments: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One table row per segment, in its one direction: the source language's
    text to translate and the target language's text as the reference."""
    rows = []
    for segment in segments:
        source, target = direction_of(segment[STABLE_KEY])
        rows.append(
            {
                subset_sampler.SOURCE_FIELD: REPO_ID,
                subset_sampler.LANGUAGE_FIELD: source,
                "target_language": target,
                STABLE_KEY: segment[STABLE_KEY],
                SOURCE_TEXT_FIELD: segment[source],
                REFERENCE_FIELD: segment[target],
                "domain": segment["domain"],
                "document_id": segment["document_id"],
            }
        )
    return rows


def direction_name(source: str, target: str) -> str:
    return f"{source}->{target}"


def pool_sizes(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """The post-filter pool per direction, in `DIRECTIONS` order."""
    counts = Counter(
        direction_name(row[subset_sampler.LANGUAGE_FIELD], row["target_language"])
        for row in rows
    )
    return {direction_name(*d): counts[direction_name(*d)] for d in DIRECTIONS}


def table_text(rows: Sequence[Mapping[str, Any]]) -> str:
    """The JSONL table: rows sorted by (source, segment_id), compact sorted-key
    JSON."""
    return hub_source.table_text(rows, STABLE_KEY)


def fetch_record(
    table: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    files: Mapping[str, str],
    licence_paths: Sequence[str],
) -> dict[str, Any]:
    """What a fetch establishes: the table's hash and the source's facts."""
    return {
        "source": REPO_ID,
        "source_revision": REVISION,
        "table_sha256": sha256_hex(table.encode("utf-8")),
        "row_count": table.count("\n"),
        "pool_per_direction": pool_sizes(rows),
        "git_blob_sha1": dict(files),
        "licence_files_at_revision": list(licence_paths),
        "loader": {"library": LOADER.library, "version": LOADER.version},
    }


# --- pure: the draw and the definition ----------------------------------------


def selection_spec() -> subset_sampler.SelectionSpec:
    return subset_sampler.SelectionSpec(
        benchmarks=(subset_sampler.Benchmark(REPO_ID, LICENCE, REVISION),),
        stable_source_key=STABLE_KEY,
        stratify_by=(subset_sampler.LANGUAGE_FIELD,),
        content_fields=(SOURCE_TEXT_FIELD, REFERENCE_FIELD),
        size=SIZE,
    )


def prompt_for(row: Mapping[str, Any]) -> str:
    """One drawn source text wrapped in the hand-written suite's prompt shell."""
    return PROMPT_TEMPLATE.format(
        source=LANGUAGE_NAMES[row[subset_sampler.LANGUAGE_FIELD]],
        target=LANGUAGE_NAMES[row["target_language"]],
        text=row[SOURCE_TEXT_FIELD],
    )


def size_target_reason(pool: Mapping[str, int]) -> str:
    sizes = ", ".join(
        f"{name} {pool[name]}" for name in (direction_name(*d) for d in DIRECTIONS)
    )
    return (
        "WMT24++'s en-fr_FR and en-de_DE pair files, joined on segment_id with "
        "every is_bad_source segment dropped and each segment assigned to one "
        f"direction, leave pools of {sizes} segments, each above the 100 a "
        "direction draws, so the 300-item target applies (Methodology 4)."
    )


def output_cap(
    items: Sequence[Mapping[str, Any]], tokenizer: str
) -> tuple[int, dict[str, Any]]:
    """`max_output_tokens` and its recorded basis: twice the longest drawn
    reference's token count (owner answer Q118 (a))."""
    longest = max(items, key=lambda item: (item["reference_tokens"], item["item_id"]))
    cap = CAP_FACTOR * int(longest["reference_tokens"])
    return cap, {
        "tokenizer": tokenizer,
        "longest_reference_item_id": longest["item_id"],
        "longest_reference_tokens": longest["reference_tokens"],
        "factor": CAP_FACTOR,
        "reason": (
            f"Twice the longest drawn reference, {longest['reference_tokens']} "
            f"tokens ({longest['item_id']}) under {tokenizer}, so a "
            "complete translation is never cut by the cap; not the hand-written "
            "suite's 128, which a paragraph-level segment exceeds (owner answer "
            "Q118 (a))."
        ),
    }


def build_definition(
    rows: Sequence[Mapping[str, Any]],
    record: Mapping[str, Any],
    token_counts: Mapping[str, Any],
) -> dict[str, Any]:
    """The suite definition drawn from the source table `record` describes."""
    if record["licence_files_at_revision"]:
        raise LoaderError(
            "the pinned revision ships a licence file "
            f"({', '.join(record['licence_files_at_revision'])}): read it before "
            "drawing; one naming anything other than Apache-2.0 reopens the spike"
        )
    reason = size_target_reason(record["pool_per_direction"])
    items, rule = subset_sampler.draw_with_retries(
        rows,
        selection_spec(),
        first_seed=FIRST_SEED,
        accept=lambda drawn: hub_source.certifies_at_publication(drawn, SIZE, reason),
        loader=subset_sampler.Loader(
            record["loader"]["library"], record["loader"]["version"]
        ),
    )
    by_id = {
        subset_sampler.drawn_item_id(row["source"], row[STABLE_KEY]): row
        for row in rows
    }
    counts = token_counts["counts"]
    suite_items = []
    for item in items:
        row = by_id[item["item_id"]]
        segment_key = str(row[STABLE_KEY])
        if segment_key not in counts:
            raise LoaderError(f"no reference token count for segment {segment_key}")
        suite_items.append(
            {
                "item_id": item["item_id"],
                "prompt": prompt_for(row),
                SOURCE_TEXT_FIELD: row[SOURCE_TEXT_FIELD],
                REFERENCE_FIELD: row[REFERENCE_FIELD],
                "target_language": row["target_language"],
                "domain": row["domain"],
                "reference_tokens": counts[segment_key],
                **{key: value for key, value in item.items() if key != "item_id"},
            }
        )
    cap, basis = output_cap(suite_items, token_counts["tokenizer"])
    return {
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "task_suite": "translation",
        "scoring_rule": "chrf_against_reference",
        "max_output_tokens": cap,
        "stop_sequences": [],
        "context_length": 32768,
        "thinking_policy": "disabled",
        "level": suite_gate.LEVEL_PUBLICATION,
        "size_target": SIZE,
        "size_target_reason": reason,
        suite_gate.DIVERGENCE_TOLERANCE_KEY: DIVERGENCE_TOLERANCE,
        "max_output_tokens_basis": basis,
        "source_table": {
            "sha256": record["table_sha256"],
            "row_count": record["row_count"],
            "loader_script": LOADER_SCRIPT,
            "licence_file_at_revision": bool(record["licence_files_at_revision"]),
            "licence_of_record": LICENCE_OF_RECORD,
        },
        "selection_rule": rule,
        "items": suite_items,
    }


def domain_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """Drawn items per domain (sorted) and direction (in `DIRECTIONS` order)."""
    counts = Counter(
        (
            str(item["domain"]),
            direction_name(item["language"], item["target_language"]),
        )
        for item in items
    )
    return {
        domain: {
            direction_name(*d): counts[(domain, direction_name(*d))] for d in DIRECTIONS
        }
        for domain in sorted({domain for domain, _ in counts})
    }


# --- I/O: the Hub, the server, files ------------------------------------------


def download(path: str, dest: Path, expected_oid: str) -> bytes:
    """`path` at the pinned revision, checked against its git object id; a
    file already at `dest` with that id is kept (the cache)."""
    if dest.is_file():
        cached = dest.read_bytes()
        if git_blob_sha1(cached) == expected_oid:
            return cached
    url = RESOLVE_URL.format(repo=REPO_ID, revision=REVISION, path=path)
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    data = response.content
    if git_blob_sha1(data) != expected_oid:
        raise LoaderError(
            f"{path}: downloaded git object id {git_blob_sha1(data)} is not the "
            f"Hub's {expected_oid}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data


def file_oid(tree: Sequence[Mapping[str, Any]], path: str) -> str:
    """The git object id the Hub records for a non-LFS file at `path`."""
    for entry in tree:
        if entry.get("path") == path:
            if entry.get("lfs"):
                raise LoaderError(f"{path} at {REVISION} is an LFS file")
            return str(entry["oid"])
    raise LoaderError(f"{path} is not in the tree of {REPO_ID} at {REVISION}")


def parse_jsonl(data: bytes, name: str) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise LoaderError(f"{name} line {number} is not a JSON object")
        rows.append(row)
    return rows


def fetch(cache: Path) -> tuple[str, dict[str, Any]]:
    """Fetch, verify, join and assign: the table text and its record."""
    tree = fetch_tree(REPO_ID, REVISION)
    files: dict[str, list[dict[str, Any]]] = {}
    oids: dict[str, str] = {}
    for pair in PAIRS:
        path = PAIR_FILE.format(pair=pair)
        oids[path] = file_oid(tree, path)
        files[pair] = parse_jsonl(
            download(path, cache / REVISION / path, oids[path]), path
        )
    rows = source_rows(join_pairs(files))
    table = table_text(rows)
    record = fetch_record(table, rows, files=oids, licence_paths=licence_files(tree))
    return table, record


def count_tokens(
    rows: Sequence[Mapping[str, Any]], server: str, roster_entry_id: str
) -> dict[str, Any]:
    """Every row's reference token count under the served model's tokenizer."""
    base = server.rstrip("/")
    props = requests.get(f"{base}/props", timeout=30)
    props.raise_for_status()
    served = props.json()
    # PureWindowsPath splits on both separators, so a Windows server path
    # reduces to its file name on any OS (a POSIX Path keeps the backslashes).
    model = PureWindowsPath(str(served.get("model_path", "unknown model"))).name
    build = served.get("build_info", "unknown build")
    counts: dict[str, int] = {}
    for row in rows:
        response = requests.post(
            f"{base}/tokenize",
            json={"content": row[REFERENCE_FIELD], "add_special": False},
            timeout=30,
        )
        response.raise_for_status()
        counts[str(row[STABLE_KEY])] = len(response.json()["tokens"])
    return {
        "tokenizer": (
            f"the tokenizer of {roster_entry_id} ({model}), counted by "
            f"llama-server {build} /tokenize without special tokens"
        ),
        "counts": counts,
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --- the command ---------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python scripts/wmt24pp_suite.py")
    commands = parser.add_subparsers(dest="command", required=True)
    default_cache = Path(tempfile.gettempdir()) / "wmt24pp"
    fetch_cmd = commands.add_parser("fetch", help="write the JSONL source table")
    fetch_cmd.add_argument("--out", type=Path, required=True)
    fetch_cmd.add_argument("--record", type=Path, required=True)
    fetch_cmd.add_argument("--cache", type=Path, default=default_cache)
    count_cmd = commands.add_parser("count-tokens", help="count reference tokens")
    count_cmd.add_argument("--table", type=Path, required=True)
    count_cmd.add_argument("--server", required=True)
    count_cmd.add_argument("--roster-entry", required=True)
    count_cmd.add_argument("--out", type=Path, required=True)
    draw_cmd = commands.add_parser("draw", help="draw the suite definition")
    draw_cmd.add_argument("--table", type=Path, required=True)
    draw_cmd.add_argument("--record", type=Path, required=True)
    draw_cmd.add_argument("--token-counts", type=Path, required=True)
    draw_cmd.add_argument("--out", type=Path, required=True)
    verify_cmd = commands.add_parser("verify", help="the operator replay")
    verify_cmd.add_argument("--cache", type=Path, default=default_cache)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "fetch":
            table, record = fetch(args.cache)
            write_text(args.out, table)
            write_text(args.record, json.dumps(record, indent=2, sort_keys=True) + "\n")
            print(
                f"{args.out}: {record['row_count']} rows, SHA-256 "
                f"{record['table_sha256']}; pool per direction "
                f"{record['pool_per_direction']}; licence files at {REVISION}: "
                f"{record['licence_files_at_revision'] or 'none'}"
            )
            return 0
        if args.command == "count-tokens":
            rows = subset_replay.read_source(args.table)
            counts = count_tokens(rows, args.server, args.roster_entry)
            write_text(args.out, json.dumps(counts, indent=2, sort_keys=True) + "\n")
            print(f"{args.out}: {len(counts['counts'])} references counted")
            return 0
        if args.command == "draw":
            definition = build_definition(
                subset_replay.read_source(args.table),
                _read_json(args.record),
                _read_json(args.token_counts),
            )
            write_text(args.out, definition_text(definition))
            print(
                f"{args.out}: {len(definition['items'])} items, max_output_tokens "
                f"{definition['max_output_tokens']}, per domain "
                f"{domain_counts(definition['items'])}"
            )
            return 0
        return verify(args.cache)
    except (
        LoaderError,
        subset_sampler.SubsetSamplerError,
        OSError,
        ValueError,
        requests.RequestException,
    ) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1


def verify(cache: Path) -> int:
    definition = suite_registry.resolve(SUITE_ID)
    table, _ = fetch(cache)
    recorded = definition.extra["source_table"]["sha256"]
    problem = verify_table(table, recorded)
    if problem is not None:
        print(f"not reproduced: {problem}", file=sys.stderr)
        return 1
    print(f"source table SHA-256 matches: {recorded}")
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "wmt24pp.jsonl"
        write_text(source, table)
        return subset_replay.main(["--suite", SUITE_ID, "--source", str(source)])


if __name__ == "__main__":
    sys.exit(main())
