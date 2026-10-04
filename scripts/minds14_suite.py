"""Load MInDS-14 at its pinned revision and draw the publication classification suite.

`uv run --group loaders python scripts/minds14_suite.py fetch --out TABLE.jsonl
--record RECORD.json [--cache DIR]`
    Downloads the `en-US`, `fr-FR` and `de-DE` parquet files of
    `PolyAI/minds14` at the pinned revision, checks each against the SHA-256
    the Hub's tree listing records for it, and writes the JSONL source table
    `subset_replay` reads: one row per utterance, carrying `source`,
    `language`, the stable key `path`, `transcription`, and `intent_class`
    mapped from its class index to its name. The record states the table's
    SHA-256, its row count, each parquet's SHA-256, and whether the revision
    ships a licence file. Only the three parquet files and the tree listing
    are fetched: `MInDS-14.zip`, the original release, is not.

`uv run python scripts/minds14_suite.py draw --table TABLE.jsonl --record
RECORD.json --out DEFINITION.json`
    Draws the 300-item subset with `subset_sampler` (stratified by language
    and intent, accepted only where it certifies at `publication`), wraps
    each drawn transcription in the suite's prompt template, and writes the
    suite definition with its selection rule and the source table's SHA-256.

`uv run --group loaders python scripts/minds14_suite.py verify [--cache DIR]`
    The operator replay: re-fetches the table from the pinned revision,
    checks its SHA-256 against the one the registered suite records, then
    replays the suite's selection rule over it (`subset_replay`). Exit 0
    only when both hold.

The locale-to-language and class-index-to-name mappings live here, in the
loader: the selection rule records only the loader library and version
(`subset_sampler.RULE_KEYS` is closed). The table is written sorted by
`path`, as compact sorted-key JSON in UTF-8 with `\\n` line ends, so its
SHA-256 is the same on every machine that reads the same revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests

from wave_local_ai_v2 import subset_replay, subset_sampler, suite_gate, suite_registry

REPO_ID = "PolyAI/minds14"
REVISION = "40ce77cb32a384e4d50a568e1ec39ac804019d33"  # pragma: allowlist secret
# The source configs the suite draws from, and the suite language each is.
CONFIGS = {"en-US": "en", "fr-FR": "fr", "de-DE": "de"}
PARQUET_PATH = "{config}/train-00000-of-00001.parquet"
TREE_URL = "https://huggingface.co/api/datasets/{repo}/tree/{revision}?recursive=true"
RESOLVE_URL = "https://huggingface.co/datasets/{repo}/resolve/{revision}/{path}"
CARD_URL = "https://huggingface.co/datasets/{repo}/blob/{revision}/README.md"

# The card's `license: cc-by-4.0`, as the item licence identifier.
LICENCE = "CC-BY-4.0"
STABLE_KEY = "path"
LABEL_FIELD = "intent_class"
TEXT_FIELD = "transcription"
SIZE = suite_gate.PUBLICATION_SIZE_TARGETS[-1]
FIRST_SEED = 20261004

SUITE_ID = "classification-banking-intents-minds14"
SUITE_VERSION = "1"
LOADER_SCRIPT = "scripts/minds14_suite.py"
SIZE_TARGET_REASON = (
    "MInDS-14's en-US, fr-FR and de-DE train splits supply 300 items: 100 per "
    "language and 7 or 8 per intent, against a smallest (language, intent) "
    "cell of 31 source rows, so the 300-item target applies (Methodology 4)."
)
DIVERGENCE_TOLERANCE = {
    "value": 0.1,
    "unit": suite_gate.TOLERANCE_UNIT_FRACTION_OF_ITEMS,
    "reason": (
        "Provisional, not yet set against an observed cloud re-run of this "
        "suite: none is published, and no paid call was made when it was "
        "declared. It mirrors the hand-written classification suite's 0.10 "
        "(30 of 300 items whose label differs) until a Mistral or Google "
        "re-run of this suite against its published reference is observed and "
        "the value is re-set against it."
    ),
}
LICENCE_OF_RECORD = (
    "The Hugging Face dataset card of PolyAI/minds14 at the pinned revision "
    "(YAML license: cc-by-4.0; Licensing Information: Creative Commons "
    "license (CC-BY)); the revision ships no licence file."
)
PROMPT_TEMPLATE = (
    "Classify the following e-banking customer request into exactly one of "
    "these intents: {labels}. Reply with only the intent label, exactly as "
    "written, nothing else.\n\nMessage: {text}"
)
_LICENCE_FILE_STEMS = ("license", "licence", "copying")
_CHUNK = 1 << 20


class LoaderError(RuntimeError):
    """Raised when the source cannot be fetched, verified or mapped."""


# --- pure: mapping, table, record -------------------------------------------


def licence_files(tree: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every file in the tree listing whose name is a licence file's."""
    return sorted(
        str(entry["path"])
        for entry in tree
        if entry.get("type") == "file"
        and str(entry["path"])
        .rsplit("/", 1)[-1]
        .lower()
        .startswith(_LICENCE_FILE_STEMS)
    )


def parquet_sha256(tree: Sequence[Mapping[str, Any]], path: str) -> str:
    """The SHA-256 the Hub records for `path` (its LFS object id)."""
    for entry in tree:
        if entry.get("path") == path:
            oid = (entry.get("lfs") or {}).get("oid")
            if isinstance(oid, str) and len(oid) == 64:
                return oid
            raise LoaderError(f"{path} at {REVISION} records no LFS SHA-256")
    raise LoaderError(f"{path} is not in the tree of {REPO_ID} at {REVISION}")


def intent_names(schema_metadata: Mapping[bytes, bytes] | None) -> list[str]:
    """The `intent_class` class names, from the parquet's Hugging Face metadata."""
    raw = (schema_metadata or {}).get(b"huggingface")
    if raw is None:
        raise LoaderError("the parquet carries no Hugging Face features metadata")
    features = json.loads(raw).get("info", {}).get("features", {})
    names = features.get(LABEL_FIELD, {}).get("names")
    if not (
        isinstance(names, list) and names and all(isinstance(n, str) for n in names)
    ):
        raise LoaderError(f"the parquet metadata names no {LABEL_FIELD} classes")
    return names


def source_rows(
    config: str,
    paths: Sequence[str],
    transcriptions: Sequence[str],
    intent_ids: Sequence[int],
    names: Sequence[str],
) -> list[dict[str, Any]]:
    """One config's columns as source-table rows, the label mapped to its name."""
    language = CONFIGS[config]
    rows = []
    for path, text, intent in zip(paths, transcriptions, intent_ids, strict=True):
        if not 0 <= intent < len(names):
            raise LoaderError(f"{path} has intent_class {intent}, outside its names")
        rows.append(
            {
                subset_sampler.SOURCE_FIELD: REPO_ID,
                subset_sampler.LANGUAGE_FIELD: language,
                STABLE_KEY: path,
                TEXT_FIELD: text,
                LABEL_FIELD: names[intent],
            }
        )
    return rows


def table_text(rows: Sequence[Mapping[str, Any]]) -> str:
    """The JSONL table: rows sorted by (source, path), compact sorted-key JSON."""
    ordered = sorted(rows, key=lambda row: (row["source"], str(row[STABLE_KEY])))
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in ordered
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_record(
    table: str,
    *,
    parquet: Mapping[str, str],
    licence_paths: Sequence[str],
    loader_version: str,
) -> dict[str, Any]:
    """What a fetch establishes: the table's hash and the source's facts."""
    return {
        "source": REPO_ID,
        "source_revision": REVISION,
        "table_sha256": sha256_hex(table.encode("utf-8")),
        "row_count": table.count("\n"),
        "parquet_sha256": dict(parquet),
        "licence_files_at_revision": list(licence_paths),
        "loader": {"library": "pyarrow", "version": loader_version},
    }


# --- pure: the draw and the definition ----------------------------------------


def selection_spec() -> subset_sampler.SelectionSpec:
    return subset_sampler.SelectionSpec(
        benchmarks=(subset_sampler.Benchmark(REPO_ID, LICENCE, REVISION),),
        stable_source_key=STABLE_KEY,
        stratify_by=(subset_sampler.LANGUAGE_FIELD, LABEL_FIELD),
        content_fields=(TEXT_FIELD, LABEL_FIELD),
        size=SIZE,
    )


def prompt_for(text: str, labels: Sequence[str]) -> str:
    """One drawn transcription wrapped in the suite's prompt template."""
    return PROMPT_TEMPLATE.format(labels=", ".join(sorted(labels)), text=text)


def _certifies_at_publication(items: list[dict[str, Any]]) -> bool:
    try:
        suite_gate.gate_suite(
            items,
            level=suite_gate.LEVEL_PUBLICATION,
            size_target=SIZE,
            size_target_reason=SIZE_TARGET_REASON,
        )
    except suite_gate.SuiteGateError:
        return False
    return True


def build_definition(
    rows: Sequence[Mapping[str, Any]], record: Mapping[str, Any]
) -> dict[str, Any]:
    """The suite definition drawn from the source table `record` describes."""
    if record["licence_files_at_revision"]:
        raise LoaderError(
            "the pinned revision ships a licence file "
            f"({', '.join(record['licence_files_at_revision'])}): read it before "
            "drawing; one naming anything other than CC BY 4.0 reopens the spike"
        )
    loader = subset_sampler.Loader(
        record["loader"]["library"], record["loader"]["version"]
    )
    items, rule = subset_sampler.draw_with_retries(
        rows,
        selection_spec(),
        first_seed=FIRST_SEED,
        accept=_certifies_at_publication,
        loader=loader,
    )
    labels = sorted({str(row[LABEL_FIELD]) for row in rows})
    by_id = {
        subset_sampler.drawn_item_id(row["source"], row[STABLE_KEY]): row
        for row in rows
    }
    suite_items = []
    for item in items:
        row = by_id[item["item_id"]]
        suite_items.append(
            {
                "item_id": item["item_id"],
                "prompt": prompt_for(str(row[TEXT_FIELD]), labels),
                "expected_label": row[LABEL_FIELD],
                **{key: value for key, value in item.items() if key != "item_id"},
            }
        )
    return {
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "task_suite": "classification",
        "scoring_rule": "exact_label_match",
        "max_output_tokens": 32,
        "stop_sequences": [],
        "context_length": 32768,
        "thinking_policy": "disabled",
        "level": suite_gate.LEVEL_PUBLICATION,
        "size_target": SIZE,
        "size_target_reason": SIZE_TARGET_REASON,
        suite_gate.DIVERGENCE_TOLERANCE_KEY: DIVERGENCE_TOLERANCE,
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


def definition_text(definition: Mapping[str, Any]) -> str:
    return json.dumps(definition, ensure_ascii=False, indent=2) + "\n"


# --- I/O: the Hub, parquet, files --------------------------------------------


def fetch_tree() -> list[dict[str, Any]]:
    response = requests.get(
        TREE_URL.format(repo=REPO_ID, revision=REVISION), timeout=60
    )
    response.raise_for_status()
    tree: list[dict[str, Any]] = response.json()
    return tree


def download(path: str, dest: Path, expected_sha256: str) -> None:
    """`path` at the pinned revision into `dest`, checked against its SHA-256.

    A file already at `dest` with the right hash is kept (the cache).
    """
    if dest.is_file() and sha256_hex(dest.read_bytes()) == expected_sha256:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    url = RESOLVE_URL.format(repo=REPO_ID, revision=REVISION, path=path)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_content(_CHUNK):
                digest.update(chunk)
                handle.write(chunk)
    if digest.hexdigest() != expected_sha256:
        dest.unlink()
        raise LoaderError(
            f"{path}: downloaded SHA-256 {digest.hexdigest()} is not the Hub's "
            f"{expected_sha256}"
        )


def read_config(config: str, parquet: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    table = pq.read_table(parquet, columns=[STABLE_KEY, TEXT_FIELD, LABEL_FIELD])
    names = intent_names(pq.read_schema(parquet).metadata)
    return source_rows(
        config,
        table.column(STABLE_KEY).to_pylist(),
        table.column(TEXT_FIELD).to_pylist(),
        table.column(LABEL_FIELD).to_pylist(),
        names,
    )


def fetch(cache: Path) -> tuple[str, dict[str, Any]]:
    """Fetch, verify and map the three configs: the table text and its record."""
    import pyarrow

    tree = fetch_tree()
    rows: list[dict[str, Any]] = []
    parquet: dict[str, str] = {}
    for config in CONFIGS:
        path = PARQUET_PATH.format(config=config)
        expected = parquet_sha256(tree, path)
        dest = cache / REVISION / path
        download(path, dest, expected)
        parquet[path] = expected
        rows += read_config(config, dest)
    table = table_text(rows)
    record = fetch_record(
        table,
        parquet=parquet,
        licence_paths=licence_files(tree),
        loader_version=pyarrow.__version__,
    )
    return table, record


def read_table(path: Path) -> list[dict[str, Any]]:
    return subset_replay.read_source(path)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def verify_table(table: str, recorded_sha256: str) -> str | None:
    """Why a re-fetched table is not the recorded one, or None."""
    actual = sha256_hex(table.encode("utf-8"))
    if actual == recorded_sha256:
        return None
    return (
        f"the re-fetched table hashes to {actual}, the suite records "
        f"{recorded_sha256}: the source moved at its pinned revision, or the "
        "loader maps it differently"
    )


# --- the command ---------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python scripts/minds14_suite.py")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch_cmd = commands.add_parser("fetch", help="write the JSONL source table")
    fetch_cmd.add_argument("--out", type=Path, required=True)
    fetch_cmd.add_argument("--record", type=Path, required=True)
    fetch_cmd.add_argument(
        "--cache", type=Path, default=Path(tempfile.gettempdir()) / "minds14"
    )
    draw_cmd = commands.add_parser("draw", help="draw the suite definition")
    draw_cmd.add_argument("--table", type=Path, required=True)
    draw_cmd.add_argument("--record", type=Path, required=True)
    draw_cmd.add_argument("--out", type=Path, required=True)
    verify_cmd = commands.add_parser("verify", help="the operator replay")
    verify_cmd.add_argument(
        "--cache", type=Path, default=Path(tempfile.gettempdir()) / "minds14"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "fetch":
            table, record = fetch(args.cache)
            _write(args.out, table)
            _write(args.record, json.dumps(record, indent=2, sort_keys=True) + "\n")
            print(
                f"{args.out}: {record['row_count']} rows, SHA-256 "
                f"{record['table_sha256']}; licence files at {REVISION}: "
                f"{record['licence_files_at_revision'] or 'none'}"
            )
            return 0
        if args.command == "draw":
            record = json.loads(args.record.read_text(encoding="utf-8"))
            definition = build_definition(read_table(args.table), record)
            _write(args.out, definition_text(definition))
            print(f"{args.out}: {len(definition['items'])} items")
            return 0
        return verify(args.cache)
    except (LoaderError, subset_sampler.SubsetSamplerError, OSError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1


def verify(cache: Path) -> int:
    definition = suite_registry.resolve(SUITE_ID)
    table, _ = fetch(cache)
    problem = verify_table(table, definition.extra["source_table"]["sha256"])
    if problem is not None:
        print(f"not reproduced: {problem}", file=sys.stderr)
        return 1
    print(f"source table SHA-256 matches: {definition.extra['source_table']['sha256']}")
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "minds14.jsonl"
        _write(source, table)
        return subset_replay.main(["--suite", SUITE_ID, "--source", str(source)])


if __name__ == "__main__":
    sys.exit(main())
