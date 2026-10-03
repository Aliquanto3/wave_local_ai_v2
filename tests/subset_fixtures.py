"""Shared subset fixtures: a constructed public source and a suite drawn from it.

The source is a table built here, not a real benchmark: no download, no
loader. Lives beside the tests because `test_subset_sampler`,
`test_suite_registry` and `test_subset_replay` draw from the same source.
"""

from __future__ import annotations

from typing import Any

from wave_local_ai_v2 import subset_sampler, suite_gate

SOURCE = "fixture-intents"
BENCHMARK = subset_sampler.Benchmark(SOURCE, "CC-BY-4.0", "rev-1")
LOADER = subset_sampler.Loader("json", "stdlib")
LABELS = ("account", "billing", "other", "technical")
SIZE_TARGET_REASON = "the constructed source holds fewer than 300 items per language"

CLASSIFICATION_SPEC = subset_sampler.SelectionSpec(
    benchmarks=(BENCHMARK,),
    stable_source_key="id",
    stratify_by=("language", "intent"),
    content_fields=("text", "intent"),
    size=102,
)
TRANSLATION_SPEC = subset_sampler.SelectionSpec(
    benchmarks=(BENCHMARK,),
    stable_source_key="id",
    stratify_by=("language",),
    content_fields=("text",),
    size=102,
)


def classification_source(per_label: int = 15) -> list[dict[str, Any]]:
    """`per_label` rows for each (language, label), in source order."""
    return [
        {
            "source": SOURCE,
            "id": f"{language}-{label}-{index:02d}",
            "language": language,
            "intent": label,
            "text": f"{language} message about {label}, number {index}",
        }
        for language in suite_gate.LANGUAGES
        for label in LABELS
        for index in range(per_label)
    ]


def publication_gate_accepts(items: list[dict[str, Any]]) -> bool:
    """Whether the drawn items certify at `publication` (order 4's gate)."""
    try:
        suite_gate.gate_suite(
            items,
            level=suite_gate.LEVEL_PUBLICATION,
            size_target=100,
            size_target_reason=SIZE_TARGET_REASON,
        )
    except suite_gate.SuiteGateError:
        return False
    return True


def drawn_definition(seed: int = 7) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """A publication classification definition drawn from the constructed
    source, and that source."""
    rows = classification_source()
    items, rule = subset_sampler.draw_with_retries(
        rows,
        CLASSIFICATION_SPEC,
        first_seed=seed,
        accept=publication_gate_accepts,
        loader=LOADER,
    )
    by_id = {f"{SOURCE}:{row['id']}": row for row in rows}
    suite_items = [
        {
            **item,
            "prompt": f"Classify: {by_id[item['item_id']]['text']}",
            "expected_label": by_id[item["item_id"]]["intent"],
        }
        for item in items
    ]
    definition = {
        "suite_id": "fixture-drawn",
        "suite_version": "1",
        "task_suite": "classification",
        "scoring_rule": "exact_label_match",
        "max_output_tokens": 8,
        "stop_sequences": [],
        "context_length": 2048,
        "thinking_policy": "disabled",
        "level": "publication",
        "divergence_tolerance": {
            "value": 0.1,
            "unit": "fraction_of_items",
            "reason": "Fixture tolerance.",
        },
        "size_target": 100,
        "size_target_reason": SIZE_TARGET_REASON,
        "selection_rule": rule,
        "items": suite_items,
    }
    return definition, rows
