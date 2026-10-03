"""The suite registry: a task suite is a declared definition, resolved by id.

A suite is data plus a named scoring rule, not a module the CLI imports. Its
definition -- id, version, the use case its rows publish as `task_suite`,
the four Methodology 3 generation constraints (`max_output_tokens`,
`stop_sequences`, `context_length`, `thinking_policy`), the name of its
scoring rule, and its items with their language, provenance and
contamination-risk tags -- is one JSON object. The shipped definitions live in
this package's `suite_data/` directory, one file per suite named
`<suite_id>.json`; the registry lists that directory to know which ids exist
and loads a file only when its id is resolved, so one broken file never stops
another suite from running.

Every definition passes through `suite_gate.gate_suite` as it is loaded: the
gate is consumed here, not reimplemented, and a definition it refuses raises
before any `SuiteDefinition` exists, so a refused suite can never be run.
The gate's result is held on the definition, which is what the CLI reads.

The shape is open to additions: a top-level key the core does not name is
kept in `SuiteDefinition.extra` and exported in the snapshot, and an item key
the core does not name stays on the item. The interval epic's per-suite and
per-item fields (size target, source, licence, source revision, content
hash, selection rule) land that way, as data, without a second shape. Only
the core keys are checked here; what an added key means is the business of
the story that adds it. The declared `level` is a core key, and the gate
checks it together with the optional `size_target`/`size_target_reason` and
each item's optional `licence`, `source` and `source_revision`. A declared
`selection_rule` and each item's `content_hash` are checked through
`subset_sampler`, which owns what they mean: a rule it could not replay, or
items that disagree with it, never load.

The `divergence_tolerance` a cloud subject's re-run is decided under is a
required declaration, checked by `suite_gate.gate_divergence_tolerance` at
load and held on the definition; it stays in `extra` too, so the snapshot of
the suite version that declared it publishes it.

`prompt_set_hash` is never declared in the data: it is computed from the
items at load, so a hand-edited prompt always moves it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from types import MappingProxyType
from typing import Any

from wave_local_ai_v2 import row_contract, scoring_rules, subset_sampler, suite_gate
from wave_local_ai_v2.suite_gate import DivergenceTolerance, SuiteGateResult

SUITE_DATA_DIRNAME = "suite_data"

_CORE_KEYS = frozenset(
    {
        "suite_id",
        "suite_version",
        "task_suite",
        "scoring_rule",
        "max_output_tokens",
        "stop_sequences",
        "context_length",
        "thinking_policy",
        "level",
        "items",
    }
)
# Keys a definition may not declare, because the registry computes them.
_COMPUTED_KEYS = frozenset({"prompt_set_hash"})


class SuiteRegistryError(ValueError):
    """Raised for an unregistered suite id, an unknown scoring rule, or a
    definition whose core keys are missing or malformed."""


@dataclass(frozen=True)
class SuiteDefinition:
    """One registered suite, loaded from data and passed by the gate."""

    suite_id: str
    suite_version: str
    task_suite: str
    scoring_rule: str
    max_output_tokens: int
    stop_sequences: list[str]
    context_length: int
    # Whether the subject may spend its cap reasoning before answering. Only
    # the local path can enforce it today (llama-server's
    # `chat_template_kwargs`); every row of the batch publishes it regardless,
    # because it is the suite's declaration and not a per-provider report.
    thinking_policy: str
    # The level the suite declares (`suite_gate.SUITE_LEVELS`); the gate
    # certifies it there or refuses it, so `gate["level"]` always equals it.
    level: str
    items: tuple[Mapping[str, Any], ...]
    prompt_set_hash: str
    gate: SuiteGateResult
    # The per-item divergence a cloud subject's re-run is decided under
    # (`verdict.quality_verdict`), as the gate checked it.
    divergence_tolerance: DivergenceTolerance
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def score_batch(
        self, completions: Sequence[Mapping[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Score this suite's items against one batch's completions."""
        # The name was checked against the table when the definition loaded.
        rule = scoring_rules.SCORING_RULES[self.scoring_rule]
        return rule(self.items, completions, max_output_tokens=self.max_output_tokens)

    def score_items(
        self,
        items: Sequence[Mapping[str, Any]],
        completions: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """Score a subset of this suite's items: the per-item fields only.

        A resumed batch runs only its missing items, so their per-item fields
        are scored here and the batch fields come from `aggregate_batch`
        over the whole suite.
        """
        rule = scoring_rules.SCORING_RULES[self.scoring_rule]
        per_item, _ = rule(items, completions, max_output_tokens=self.max_output_tokens)
        return per_item

    def aggregate_batch(
        self,
        items: Sequence[Mapping[str, Any]],
        per_item: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """The suite-level fields over `items` and their per-item fields."""
        # Checked against the table when the definition loaded.
        return scoring_rules.BATCH_AGGREGATES[self.scoring_rule](items, per_item)

    def preflight(self) -> None:
        """Run the scoring rule's host check, if it declares one.

        Raises before any process starts when the rule cannot score here
        (the code-generation sandbox absent): the suite refuses to start.
        """
        check = scoring_rules.PREFLIGHTS.get(self.scoring_rule)
        if check is not None:
            check(self.items)


def prompt_set_hash(items: Sequence[Mapping[str, Any]]) -> str:
    """SHA-256 hex digest over the items' prompts only, deterministically ordered.

    Deliberately not over the whole item dict: adding a non-prompt field later
    (a tag, a provenance note) must never move the hash. Only an edited prompt
    should.

    Duck-typed against any mapping exposing `item_id` and `prompt`, the same
    choice `suite_gate.gate_suite` documents. `judge_probe.JUDGE_PROBE_ITEMS`
    hashes through this one function, so a reader comparing a
    `prompt_set_hash` across two published files is comparing like with like
    rather than two suites' separate hashing rules.
    """
    sorted_items = sorted(items, key=lambda item: item["item_id"])
    serialized = "\n".join(
        f"{item['item_id']}:{item['prompt']}" for item in sorted_items
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_definition(source: Path | Traversable) -> SuiteDefinition:
    """Read, check and gate one definition file.

    Raises `SuiteRegistryError` on a malformed core or an unknown scoring
    rule, and lets `suite_gate.SuiteGateError` through on an item whose
    language or provenance declaration the gate refuses.
    """
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SuiteRegistryError(
            f"suite definition {source} is not JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise SuiteRegistryError(f"suite definition {source} is not a JSON object")
    return _definition_from_data(data, origin=str(source))


def _definition_from_data(data: dict[str, Any], *, origin: str) -> SuiteDefinition:
    missing = sorted(_CORE_KEYS - data.keys())
    if missing:
        raise SuiteRegistryError(
            f"suite definition {origin} is missing {', '.join(missing)}"
        )
    computed = sorted(_COMPUTED_KEYS & data.keys())
    if computed:
        raise SuiteRegistryError(
            f"suite definition {origin} declares {', '.join(computed)}, which "
            "the registry computes from the items and never reads from data"
        )

    for key in ("suite_id", "suite_version", "task_suite", "scoring_rule"):
        _require(isinstance(data[key], str) and data[key] != "", origin, key)
    for key in ("max_output_tokens", "context_length"):
        value = data[key]
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value > 0,
            origin,
            key,
        )
    stop_sequences = data["stop_sequences"]
    _require(
        isinstance(stop_sequences, list)
        and all(isinstance(stop, str) for stop in stop_sequences),
        origin,
        "stop_sequences",
    )
    if data["thinking_policy"] not in row_contract.THINKING_POLICIES:
        raise SuiteRegistryError(
            f"suite definition {origin} has thinking_policy "
            f"{data['thinking_policy']!r}, not one of "
            f"{', '.join(sorted(row_contract.THINKING_POLICIES))}"
        )

    rule_name = data["scoring_rule"]
    if rule_name not in scoring_rules.SCORING_RULES:
        raise SuiteRegistryError(
            f"suite definition {origin} names scoring rule {rule_name!r}, which "
            "the registry does not know (known: "
            f"{', '.join(sorted(scoring_rules.SCORING_RULES))})"
        )
    if rule_name not in scoring_rules.BATCH_AGGREGATES:
        raise SuiteRegistryError(
            f"suite definition {origin} names scoring rule {rule_name!r}, which "
            "has no batch aggregate: a batch under it could not be completed "
            "by --resume"
        )

    items = _items(data["items"], origin)
    item_check = scoring_rules.ITEM_CHECKS.get(rule_name)
    item_problems = item_check(items) if item_check is not None else []
    if item_problems:
        raise SuiteRegistryError(
            f"suite definition {origin} has items its scoring rule "
            f"{rule_name!r} cannot score: " + "; ".join(item_problems)
        )
    _check_selection(data, items, origin)
    # The gate runs on every load and its refusal propagates: no definition
    # object exists for a suite it refuses, including a suite that falls short
    # of the level it declares. The size target and its reason stay in
    # `extra` (exported in the snapshot); the gate is what checks them.
    gate = suite_gate.gate_suite(
        items,
        level=data["level"],
        size_target=data.get("size_target"),
        size_target_reason=data.get("size_target_reason"),
    )
    divergence_tolerance = suite_gate.gate_divergence_tolerance(
        data.get(suite_gate.DIVERGENCE_TOLERANCE_KEY)
    )

    return SuiteDefinition(
        suite_id=data["suite_id"],
        suite_version=data["suite_version"],
        task_suite=data["task_suite"],
        scoring_rule=rule_name,
        max_output_tokens=data["max_output_tokens"],
        stop_sequences=list(stop_sequences),
        context_length=data["context_length"],
        thinking_policy=data["thinking_policy"],
        level=data["level"],
        items=items,
        prompt_set_hash=prompt_set_hash(items),
        gate=gate,
        divergence_tolerance=divergence_tolerance,
        extra=MappingProxyType(
            {key: value for key, value in data.items() if key not in _CORE_KEYS}
        ),
    )


def _check_selection(
    data: Mapping[str, Any], items: Sequence[Mapping[str, Any]], origin: str
) -> None:
    """Refuse a declared selection rule that cannot be replayed, items that
    disagree with it, or a malformed item content hash.

    The rule and the hashes are additions to this shape, carried as data
    (`extra` and the item mapping); what they mean is `subset_sampler`'s.
    """
    if "selection_rule" in data:
        rule = data["selection_rule"]
        problems = subset_sampler.check_selection_rule(rule, data["task_suite"])
        if not problems:
            problems = subset_sampler.check_drawn_items(items, rule)
    else:
        problems = [
            problem
            for problem in map(subset_sampler.content_hash_problem, items)
            if problem is not None
        ]
    if problems:
        raise SuiteRegistryError(
            f"suite definition {origin} has a selection it cannot replay: "
            + "; ".join(problems)
        )


def _require(condition: bool, origin: str, key: str) -> None:
    if not condition:
        raise SuiteRegistryError(f"suite definition {origin} has a malformed {key}")


def _items(raw_items: Any, origin: str) -> tuple[Mapping[str, Any], ...]:
    _require(
        isinstance(raw_items, list)
        and raw_items != []
        and all(isinstance(item, dict) for item in raw_items),
        origin,
        "items",
    )
    seen: set[str] = set()
    for item in raw_items:
        item_id = item.get("item_id")
        _require(isinstance(item_id, str) and item_id != "", origin, "item_id")
        if item_id in seen:
            raise SuiteRegistryError(
                f"suite definition {origin} declares item {item_id!r} twice"
            )
        seen.add(item_id)
        prompt = item.get("prompt")
        if not (isinstance(prompt, str) and prompt.strip()):
            raise SuiteRegistryError(
                f"suite definition {origin} item {item_id!r} has no prompt"
            )
    # Read-only views: a resolved definition is cached and shared, so no
    # caller may edit an item another caller will score.
    return tuple(MappingProxyType(dict(item)) for item in raw_items)


def _built_in_dir() -> Traversable:
    return resources.files("wave_local_ai_v2") / SUITE_DATA_DIRNAME


def _built_in_ids() -> set[str]:
    return {
        entry.name.removesuffix(".json")
        for entry in _built_in_dir().iterdir()
        if entry.name.endswith(".json")
    }


# Definitions resolved from the shipped data, cached on first resolve.
_LOADED: dict[str, SuiteDefinition] = {}
# Definitions registered at run time, from a file outside `suite_data/`.
_REGISTERED: dict[str, SuiteDefinition] = {}


def registered_ids() -> list[str]:
    """Every suite id `resolve` answers, sorted."""
    return sorted(_built_in_ids() | _REGISTERED.keys())


def register(source: Path | Traversable) -> SuiteDefinition:
    """Load, gate and register one definition from outside `suite_data/`.

    Takes a file, never a built object, so nothing reaches the registry
    without passing the gate. An id already registered is refused: a suite
    id names exactly one definition.
    """
    definition = load_definition(source)
    if definition.suite_id in registered_ids():
        raise SuiteRegistryError(f"suite {definition.suite_id!r} is already registered")
    _REGISTERED[definition.suite_id] = definition
    return definition


def unregister(suite_id: str) -> None:
    """Drop a run-time registration; the shipped definitions stay."""
    _REGISTERED.pop(suite_id, None)


def resolve(suite_id: str) -> SuiteDefinition:
    """The definition registered under `suite_id`, loaded and gated.

    An unregistered id is refused naming every registered one.
    """
    if suite_id in _REGISTERED:
        return _REGISTERED[suite_id]
    if suite_id in _LOADED:
        return _LOADED[suite_id]
    if suite_id not in _built_in_ids():
        raise SuiteRegistryError(
            f"suite {suite_id!r} is not registered (registered: "
            f"{', '.join(registered_ids())})"
        )
    definition = load_definition(_built_in_dir() / f"{suite_id}.json")
    if definition.suite_id != suite_id:
        raise SuiteRegistryError(
            f"suite definition {suite_id}.json declares suite_id "
            f"{definition.suite_id!r}: the file name and the id must match"
        )
    _LOADED[suite_id] = definition
    return definition
