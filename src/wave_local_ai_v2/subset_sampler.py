"""The publication subset sampler: a seeded draw recorded as a rule that replays.

A publication suite's items are a subset drawn from named public benchmarks
(Methodology 4). "How were these items picked" is answered by the rule this
module records on the suite as data, and the rule is checked by replaying it
(`subset_replay`), never by describing it.

A seed alone does not replay a draw: a seeded draw is a function of the seed
*and* of the order the source rows arrived in, and that order belongs to
whichever loader read them. So sampler version 1 is fully specified here:

- **Canonical ordering** (`CANONICAL_ORDERING`). Source rows are sorted by
  their benchmark name (`source`) and then by the string form of the stable
  source key the rule names, before anything is drawn. Shuffling the source
  changes nothing; the loader that delivered it is recorded beside the
  sampler version, as provenance.
- **Stratification by construction.** The subset size is split equally
  across the three languages of `suite_gate.LANGUAGES` (remainders to the
  first), so every language holds at least a third of the draw and the
  publication level's 25% share holds on the first seed by design. Where the
  source is a classification benchmark, each language's allocation is split
  equally again across that language's label values in sorted order. A
  stratum the source cannot fill is refused naming it, never topped up from
  another stratum.
- **The draw.** One `random.Random(seed)` draws `sample(stratum, k)` from each
  stratum in turn, strata in the order above, rows in canonical order. The
  subset is the strata in that order, each in its drawn order. Python does
  not promise `sample` stays stable across versions, so the rule records the
  generator that drew it (`drawing_generator`: implementation and
  major.minor version), and a golden test pins the ids a fixed seed draws.
- **Retries recorded.** Where a seed is nonetheless retried, seeds run
  `first_seed`, `first_seed + 1`, ...; the rule records the attempt count and
  every seed tried, and a rule recording fewer seeds than attempts is refused
  at load (`check_selection_rule`).
- **Per-item content hash.** Each drawn item carries a SHA-256 over its own
  normalised text (each of the rule's `content_fields`, NFC-normalised with
  whitespace collapsed; a classification rule names its label field among
  them, so an upstream retag moves the hash), its licence, its source and
  that source's revision. On replay, an item whose source text moved is named
  by item id rather than surfacing only as a changed `prompt_set_hash`.

A drawn item's id is `<source>:<stable key>`, a function of the key alone, so
an edited text keeps its id and is caught by its hash. Every drawn item is
`public` provenance and contamination-risk (Methodology 5), under its
benchmark's licence and revision.

Pure: no I/O and no registry import, so the registry can check a declared
rule through this module at load.
"""

from __future__ import annotations

import hashlib
import json
import platform
import random
import re
import sys
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from wave_local_ai_v2 import suite_gate

SAMPLER_VERSION = "1"
CANONICAL_ORDERING = "source-then-stable-key-ascending"
# The row fields every source row carries under these names; a loader maps
# its benchmark's own columns onto them.
SOURCE_FIELD = "source"
LANGUAGE_FIELD = "language"
DEFAULT_MAX_ATTEMPTS = 10

RULE_KEYS = frozenset(
    {
        "sampler_version",
        "seed",
        "attempts",
        "seeds_tried",
        "loader",
        "generator",
        "stable_source_key",
        "canonical_ordering",
        "stratify_by",
        "content_fields",
        "size",
        "benchmarks",
    }
)
_BENCHMARK_KEYS = frozenset({"source", "licence", "source_revision"})
_LOADER_KEYS = frozenset({"library", "version"})
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


class SubsetSamplerError(ValueError):
    """Raised for a source the rule cannot draw from: an unknown benchmark, a
    missing or duplicate stable key, a language outside the suite languages,
    a stratum the source cannot fill, or no accepted seed."""


@dataclass(frozen=True)
class Benchmark:
    """One public benchmark a subset draws from, with its terms."""

    source: str
    licence: str
    source_revision: str


@dataclass(frozen=True)
class Loader:
    """The library that read the source rows, and its version."""

    library: str
    version: str


@dataclass(frozen=True)
class SelectionSpec:
    """Everything a draw depends on except the seed."""

    benchmarks: tuple[Benchmark, ...]
    stable_source_key: str
    # `("language",)`, or `("language", <label field>)` for a classification
    # source.
    stratify_by: tuple[str, ...]
    content_fields: tuple[str, ...]
    size: int

    @property
    def label_field(self) -> str | None:
        return self.stratify_by[1] if len(self.stratify_by) > 1 else None

    def benchmark(self, source: str) -> Benchmark | None:
        return next((b for b in self.benchmarks if b.source == source), None)


@dataclass(frozen=True)
class ReplayReport:
    """What a replay of a recorded rule found."""

    recorded_ids: tuple[str, ...]
    redrawn_ids: tuple[str, ...]
    # Item ids whose source text no longer matches their recorded hash.
    edited: tuple[str, ...]
    # Item ids the source no longer holds.
    absent: tuple[str, ...]

    @property
    def first_difference(self) -> int | None:
        """The first position where the recorded and redrawn ids differ."""
        for index, (recorded, redrawn) in enumerate(
            zip(self.recorded_ids, self.redrawn_ids, strict=False)
        ):
            if recorded != redrawn:
                return index
        if len(self.recorded_ids) != len(self.redrawn_ids):
            return min(len(self.recorded_ids), len(self.redrawn_ids))
        return None

    @property
    def reproduced(self) -> bool:
        return self.first_difference is None and not self.edited and not self.absent


def normalise_text(text: str) -> str:
    """NFC-normalised, with every whitespace run collapsed to one space."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def content_hash(
    row: Mapping[str, Any], content_fields: Sequence[str], benchmark: Benchmark
) -> str:
    """SHA-256 over the row's normalised text and its licence, source and
    revision, serialised as compact sorted-key JSON."""
    text: list[str] = []
    for field in content_fields:
        value = row.get(field)
        if not isinstance(value, str):
            raise SubsetSamplerError(
                f"source row {_row_name(row)} has no text field {field!r}"
            )
        text.append(normalise_text(value))
    payload = {
        "text": text,
        "licence": benchmark.licence,
        "source": benchmark.source,
        "source_revision": benchmark.source_revision,
    }
    serialised = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def drawn_item_id(source: str, key: object) -> str:
    return f"{source}:{key}"


def canonical_order(
    rows: Sequence[Mapping[str, Any]], spec: SelectionSpec
) -> list[Mapping[str, Any]]:
    """The source rows sorted by (source, stable key), after refusing any row
    the rule cannot place."""
    seen: set[str] = set()
    for row in rows:
        source = row.get(SOURCE_FIELD)
        if not isinstance(source, str) or spec.benchmark(source) is None:
            raise SubsetSamplerError(
                f"source row {_row_name(row)} names source {source!r}, which the "
                "rule does not draw from"
            )
        key = row.get(spec.stable_source_key)
        if not _is_key(key):
            raise SubsetSamplerError(
                f"source row {_row_name(row)} has no stable source key "
                f"{spec.stable_source_key!r}"
            )
        item_id = drawn_item_id(source, key)
        if item_id in seen:
            raise SubsetSamplerError(f"source holds {item_id!r} twice")
        seen.add(item_id)
        if row.get(LANGUAGE_FIELD) not in suite_gate.LANGUAGES:
            raise SubsetSamplerError(
                f"source row {item_id!r} has a language outside "
                f"{suite_gate.LANGUAGES}: {row.get(LANGUAGE_FIELD)!r}"
            )
    return sorted(
        rows, key=lambda row: (row[SOURCE_FIELD], str(row[spec.stable_source_key]))
    )


def draw(
    rows: Sequence[Mapping[str, Any]], spec: SelectionSpec, seed: int
) -> list[dict[str, Any]]:
    """One seeded, stratified draw of `spec.size` items."""
    generator = random.Random(seed)
    drawn: list[dict[str, Any]] = []
    for name, stratum, count in _strata(canonical_order(rows, spec), spec):
        if len(stratum) < count:
            raise SubsetSamplerError(
                f"stratum {name} holds {len(stratum)} source rows for {count} draws"
            )
        drawn.extend(_drawn_item(row, spec) for row in generator.sample(stratum, count))
    return drawn


def draw_with_retries(
    rows: Sequence[Mapping[str, Any]],
    spec: SelectionSpec,
    *,
    first_seed: int,
    accept: Callable[[list[dict[str, Any]]], bool],
    loader: Loader,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Draw until `accept` takes the subset; return it with its rule.

    Every seed tried is recorded on the rule, not only the accepted one.
    """
    seeds: list[int] = []
    for attempt in range(max_attempts):
        seed = first_seed + attempt
        seeds.append(seed)
        items = draw(rows, spec, seed)
        if accept(items):
            return items, selection_rule(spec, loader, seeds)
    raise SubsetSamplerError(
        f"no seed accepted after {max_attempts} attempts (seeds tried: "
        f"{', '.join(str(seed) for seed in seeds)})"
    )


def selection_rule(
    spec: SelectionSpec, loader: Loader, seeds_tried: Sequence[int]
) -> dict[str, Any]:
    """The rule as the data a suite definition records."""
    return {
        "sampler_version": SAMPLER_VERSION,
        "seed": seeds_tried[-1],
        "attempts": len(seeds_tried),
        "seeds_tried": list(seeds_tried),
        "loader": {"library": loader.library, "version": loader.version},
        "generator": drawing_generator(),
        "stable_source_key": spec.stable_source_key,
        "canonical_ordering": CANONICAL_ORDERING,
        "stratify_by": list(spec.stratify_by),
        "content_fields": list(spec.content_fields),
        "size": spec.size,
        "benchmarks": [
            {
                "source": benchmark.source,
                "licence": benchmark.licence,
                "source_revision": benchmark.source_revision,
            }
            for benchmark in spec.benchmarks
        ],
    }


def drawing_generator() -> dict[str, str]:
    """The generator this interpreter draws with: implementation and
    major.minor version, the granularity at which `random.sample` may change."""
    return {
        "library": f"{platform.python_implementation()} random.Random",
        "version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def spec_from_rule(rule: Mapping[str, Any]) -> SelectionSpec:
    """The draw parameters of a rule `check_selection_rule` accepted."""
    return SelectionSpec(
        benchmarks=tuple(
            Benchmark(b["source"], b["licence"], b["source_revision"])
            for b in rule["benchmarks"]
        ),
        stable_source_key=rule["stable_source_key"],
        stratify_by=tuple(rule["stratify_by"]),
        content_fields=tuple(rule["content_fields"]),
        size=rule["size"],
    )


def check_selection_rule(rule: object, task_suite: str) -> list[str]:
    """Every way `rule` is not a replayable rule for a `task_suite` suite."""
    if not isinstance(rule, dict):
        return ["selection_rule is not an object"]
    problems: list[str] = []
    missing = sorted(RULE_KEYS - rule.keys())
    if missing:
        problems.append(f"selection_rule is missing {', '.join(missing)}")
    unknown = sorted(rule.keys() - RULE_KEYS)
    if unknown:
        problems.append(f"selection_rule declares unknown {', '.join(unknown)}")
    if problems:
        return problems

    if rule["sampler_version"] != SAMPLER_VERSION:
        problems.append(
            f"sampler_version {rule['sampler_version']!r} is not one this code "
            f"replays ({SAMPLER_VERSION!r})"
        )
    if rule["canonical_ordering"] != CANONICAL_ORDERING:
        problems.append(
            f"canonical_ordering {rule['canonical_ordering']!r} is not "
            f"{CANONICAL_ORDERING!r}"
        )
    problems += _seed_problems(rule["seed"], rule["attempts"], rule["seeds_tried"])
    if not _is_declaration(rule["loader"], _LOADER_KEYS):
        problems.append("loader must name its library and version")
    if not _is_declaration(rule["generator"], _LOADER_KEYS):
        problems.append("generator must name its library and version")
    if not _is_text(rule["stable_source_key"]):
        problems.append("stable_source_key must be a non-empty string")
    content_fields = rule["content_fields"]
    if not (
        isinstance(content_fields, list)
        and content_fields
        and all(_is_text(field) for field in content_fields)
        and len(set(content_fields)) == len(content_fields)
    ):
        problems.append("content_fields must be distinct non-empty strings")
        content_fields = []
    problems += _stratify_problems(rule["stratify_by"], task_suite, content_fields)
    if not (_is_int(rule["size"]) and rule["size"] >= 1):
        problems.append(f"size {rule['size']!r} is not a positive integer")
    benchmarks = rule["benchmarks"]
    if not (
        isinstance(benchmarks, list)
        and benchmarks
        and all(_is_declaration(b, _BENCHMARK_KEYS) for b in benchmarks)
    ):
        problems.append(
            "benchmarks must each name their source, licence and source_revision"
        )
    elif len({b["source"] for b in benchmarks}) != len(benchmarks):
        problems.append("benchmarks names one source twice")
    return problems


def check_drawn_items(
    items: Sequence[Mapping[str, Any]], rule: Mapping[str, Any]
) -> list[str]:
    """Every way the suite's items disagree with the rule that drew them.

    `rule` must already have passed `check_selection_rule`.
    """
    spec = spec_from_rule(rule)
    problems: list[str] = []
    if len(items) != spec.size:
        problems.append(
            f"the suite holds {len(items)} items, its selection rule draws {spec.size}"
        )
    for item in items:
        item_id = item["item_id"]
        hash_problem = content_hash_problem(item)
        if hash_problem is not None:
            problems.append(hash_problem)
        elif "content_hash" not in item:
            problems.append(f"item {item_id!r} carries no content_hash")
        benchmark = spec.benchmark(str(item.get("source")))
        if benchmark is None or not str(item_id).startswith(f"{benchmark.source}:"):
            problems.append(
                f"item {item_id!r} is not drawn from a benchmark the rule names"
            )
        elif (item.get("licence"), item.get("source_revision")) != (
            benchmark.licence,
            benchmark.source_revision,
        ):
            problems.append(
                f"item {item_id!r} declares a licence or source_revision other "
                f"than its benchmark {benchmark.source!r}"
            )
    return problems


def content_hash_problem(item: Mapping[str, Any]) -> str | None:
    """Why a declared `content_hash` is malformed, or None."""
    if "content_hash" not in item:
        return None
    value = item["content_hash"]
    if isinstance(value, str) and _SHA256_HEX.fullmatch(value):
        return None
    return (
        f"item {item.get('item_id')!r} declares a content_hash that is not a "
        f"SHA-256 hex digest: {value!r}"
    )


def replay(
    items: Sequence[Mapping[str, Any]],
    rule: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> ReplayReport:
    """Re-draw the rule over `rows` and compare with the recorded items.

    Raises `SubsetSamplerError` when the rule cannot draw from `rows` at all.
    """
    spec = spec_from_rule(rule)
    redrawn = draw(rows, spec, rule["seed"])
    by_id = {
        drawn_item_id(row[SOURCE_FIELD], row[spec.stable_source_key]): row
        for row in rows
    }
    edited: list[str] = []
    absent: list[str] = []
    for item in items:
        row = by_id.get(item["item_id"])
        benchmark = spec.benchmark(str(item.get("source")))
        if row is None or benchmark is None:
            absent.append(item["item_id"])
        elif content_hash(row, spec.content_fields, benchmark) != item.get(
            "content_hash"
        ):
            edited.append(item["item_id"])
    return ReplayReport(
        recorded_ids=tuple(item["item_id"] for item in items),
        redrawn_ids=tuple(item["item_id"] for item in redrawn),
        edited=tuple(edited),
        absent=tuple(absent),
    )


def _strata(
    ordered: list[Mapping[str, Any]], spec: SelectionSpec
) -> list[tuple[str, list[Mapping[str, Any]], int]]:
    """(name, rows in canonical order, draw count) per stratum, in draw order."""
    strata: list[tuple[str, list[Mapping[str, Any]], int]] = []
    languages = suite_gate.LANGUAGES
    for language, language_count in zip(
        languages, _allocate(spec.size, len(languages)), strict=True
    ):
        language_rows = [row for row in ordered if row[LANGUAGE_FIELD] == language]
        label_field = spec.label_field
        if label_field is None:
            strata.append((f"language {language!r}", language_rows, language_count))
            continue
        labels = sorted({str(row.get(label_field)) for row in language_rows})
        if not labels:
            strata.append((f"language {language!r}", [], language_count))
            continue
        for label, label_count in zip(
            labels, _allocate(language_count, len(labels)), strict=True
        ):
            label_rows = [
                row for row in language_rows if str(row.get(label_field)) == label
            ]
            strata.append(
                (f"language {language!r}, label {label!r}", label_rows, label_count)
            )
    return strata


def _allocate(total: int, buckets: int) -> list[int]:
    """`total` split equally over `buckets`, remainders to the first ones."""
    return [
        total // buckets + (1 if index < total % buckets else 0)
        for index in range(buckets)
    ]


def _drawn_item(row: Mapping[str, Any], spec: SelectionSpec) -> dict[str, Any]:
    source = row[SOURCE_FIELD]
    benchmark = spec.benchmark(source)
    assert benchmark is not None  # canonical_order refused any other source
    return {
        "item_id": drawn_item_id(source, row[spec.stable_source_key]),
        "language": row[LANGUAGE_FIELD],
        "provenance": "public",
        "contamination_risk": True,
        "licence": benchmark.licence,
        "source": benchmark.source,
        "source_revision": benchmark.source_revision,
        "content_hash": content_hash(row, spec.content_fields, benchmark),
    }


def _seed_problems(seed: object, attempts: object, seeds_tried: object) -> list[str]:
    if not (_is_int(seed) and _is_int(attempts) and isinstance(seeds_tried, list)):
        return ["seed, attempts and seeds_tried must be integers and a list of them"]
    assert isinstance(attempts, int)
    problems: list[str] = []
    if attempts < 1:
        problems.append(f"attempts {attempts} is below 1")
    if not all(_is_int(tried) for tried in seeds_tried):
        problems.append("seeds_tried must hold integers only")
    elif len(seeds_tried) != attempts:
        problems.append(
            f"seeds_tried records {len(seeds_tried)} seeds for {attempts} attempts: "
            "every seed tried is recorded, not only the final one"
        )
    elif len(set(seeds_tried)) != len(seeds_tried):
        problems.append("seeds_tried records one seed twice")
    elif seeds_tried and seeds_tried[-1] != seed:
        problems.append(
            f"the last seed tried ({seeds_tried[-1]}) is not the recorded seed ({seed})"
        )
    return problems


def _stratify_problems(
    stratify_by: object, task_suite: str, content_fields: Sequence[str]
) -> list[str]:
    classification = task_suite == "classification"
    expected = (
        "['language', <label field>] for a classification suite"
        if classification
        else "['language']"
    )
    if not (
        isinstance(stratify_by, list)
        and all(_is_text(key) for key in stratify_by)
        and stratify_by[:1] == [LANGUAGE_FIELD]
        and len(stratify_by) == (2 if classification else 1)
    ):
        return [f"stratify_by {stratify_by!r} is not {expected}"]
    if classification and stratify_by[1] not in content_fields:
        return [
            (
                f"label field {stratify_by[1]!r} is not among content_fields, "
                "so a retagged item would keep its content hash"
            )
        ]
    return []


def _row_name(row: Mapping[str, Any]) -> str:
    return repr({key: row.get(key) for key in (SOURCE_FIELD, LANGUAGE_FIELD)})


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_text(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_key(value: object) -> bool:
    return _is_text(value) or _is_int(value)


def _is_declaration(value: object, keys: frozenset[str]) -> bool:
    return (
        isinstance(value, dict)
        and value.keys() == keys
        and all(_is_text(value[key]) for key in keys)
    )
