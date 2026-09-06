"""The three-state reproduction verdict: a re-run against a named reference
receives `reproduced`, `not_reproduced`, or `not_comparable`, stored on the row.

Reference matching never uses CPU, RAM, driver, or OS: only
`llama_cpp_build`, `quant`, `gpu_name` and the raw `flags` list decide whether
a candidate and a reference row are the same run to compare (PRD Methodology
8; plan.md's Decisions table resolves the tension between "shares the
re-run's fiche hash" and "CPU/RAM/driver/OS never block a comparison" by
naming these four fields explicitly, separate from the fiche's full identity
hash).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from wave_local_ai_v2 import fiche_registry

VERDICT_REPRODUCED = "reproduced"
VERDICT_NOT_REPRODUCED = "not_reproduced"
VERDICT_NOT_COMPARABLE = "not_comparable"

_RUNTIME_BLOCKING_FIELDS = ("llama_cpp_build", "quant", "gpu_name", "flags")

# The two per-item values a quality batch can be compared on, in the order
# they are tried. Methodology 8's "identical per-item predicted labels or
# scores": an exact-match suite publishes the first, a graded one the second.
QUALITY_COMPARED_LABEL = "predicted_label"
QUALITY_COMPARED_SCORE = "item_score"


class ReferenceMatch(TypedDict):
    reference_row: dict[str, Any]
    reference_fiche: dict[str, Any]


def runtime_blocking_fields(fiche: dict[str, Any]) -> dict[str, Any]:
    """Project `fiche` to exactly the fields a runtime reference match compares."""
    return {key: fiche[key] for key in _RUNTIME_BLOCKING_FIELDS}


def _resolve_fiche(row: dict[str, Any], registry_dir: Path) -> dict[str, Any] | None:
    fiche_hash = row.get("fiche_hash")
    if fiche_hash is None:
        return None
    return fiche_registry.read_fiche(fiche_hash, registry_dir)


def select_runtime_reference(
    candidate_row: dict[str, Any],
    reference_rows: list[dict[str, Any]],
    registry_dir: Path,
) -> ReferenceMatch | None:
    """Return the first reference row whose blocking fields all match, or `None`.

    File order is the only tie-break: reference files are curated
    single-model snapshots, so no other ordering is meaningful.
    """
    candidate_fiche = _resolve_fiche(candidate_row, registry_dir)
    if candidate_fiche is None:
        return None
    candidate_blocking = runtime_blocking_fields(candidate_fiche)

    for reference_row in reference_rows:
        reference_fiche = _resolve_fiche(reference_row, registry_dir)
        if reference_fiche is None:
            continue
        if runtime_blocking_fields(reference_fiche) == candidate_blocking:
            return ReferenceMatch(
                reference_row=reference_row, reference_fiche=reference_fiche
            )
    return None


def _closest_reference_differing_fields(
    candidate_row: dict[str, Any],
    reference_rows: list[dict[str, Any]],
    registry_dir: Path,
) -> list[str]:
    """Name every blocking field that differs against the closest reference.

    "Closest" is the reference with the fewest differing blocking fields,
    file order breaking a tie -- informative rather than reporting "everything
    differs" against an arbitrary reference.
    """
    candidate_fiche = _resolve_fiche(candidate_row, registry_dir)
    if candidate_fiche is None:
        return ["fiche_hash: candidate row's fiche is not registered"]
    candidate_blocking = runtime_blocking_fields(candidate_fiche)

    best: list[str] | None = None
    for reference_row in reference_rows:
        reference_fiche = _resolve_fiche(reference_row, registry_dir)
        if reference_fiche is None:
            continue
        reference_blocking = runtime_blocking_fields(reference_fiche)
        differing = sorted(
            key
            for key in _RUNTIME_BLOCKING_FIELDS
            if candidate_blocking[key] != reference_blocking[key]
        )
        if best is None or len(differing) < len(best):
            best = differing

    return best if best is not None else ["no reference row has a registered fiche"]


def _as_number(value: object) -> float | None:
    """`value` as a float, or `None` when it is not a plain number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _relative_delta(
    candidate_row: dict[str, Any], reference_row: dict[str, Any], metric: str
) -> float | None:
    """Relative delta on `metric`, or `None` when either row cannot supply it.

    Returns `None` rather than raising on an absent, non-numeric or
    zero-denominator value: a reference file is an operator-supplied artifact,
    and this is computed after the measurement but before the row is written,
    so an unguarded `KeyError`/`ZeroDivisionError` here would discard a
    completed run.
    """
    candidate_value = _as_number(candidate_row.get(metric))
    reference_value = _as_number(reference_row.get(metric))
    if candidate_value is None or not reference_value:
        return None
    return abs(candidate_value - reference_value) / reference_value


def runtime_verdict(
    candidate_row: dict[str, Any],
    reference_rows: list[dict[str, Any]],
    registry_dir: Path,
    tolerance: float,
) -> dict[str, Any]:
    """Compute the runtime verdict block, stored on the row before `append_row`."""
    if not reference_rows:
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": None,
            "differing_fields": [],
            "reason": "no reference rows configured or matched",
        }

    same_model = [
        row
        for row in reference_rows
        if row.get("roster_entry_id") == candidate_row.get("roster_entry_id")
    ]
    if not same_model:
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": None,
            "differing_fields": [],
            "reason": "no reference row shares this candidate's roster_entry_id",
        }

    match = select_runtime_reference(candidate_row, same_model, registry_dir)
    if match is None:
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": None,
            "differing_fields": _closest_reference_differing_fields(
                candidate_row, same_model, registry_dir
            ),
            "reason": "no reference row matches every blocking field",
        }

    reference_row = match["reference_row"]
    delta = _relative_delta(candidate_row, reference_row, "gen_tok_per_s")
    if delta is None:
        # The one gating metric: without it there is nothing to decide on, and
        # declining to compare beats inventing a verdict from a partial row.
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": reference_row.get("run_id"),
            "differing_fields": [],
            "reason": "the matching reference row carries no usable gen_tok_per_s",
        }
    verdict = VERDICT_REPRODUCED if delta <= tolerance else VERDICT_NOT_REPRODUCED

    return {
        "verdict": verdict,
        "reference_run_id": reference_row.get("run_id"),
        "differing_fields": [],
        "reason": None,
        "gen_tok_per_s_delta": delta,
        # Reported, never gating: null when the reference row cannot supply it.
        "ttft_ms_delta": _relative_delta(candidate_row, reference_row, "ttft_ms"),
        "prompt_tok_per_s_delta": _relative_delta(
            candidate_row, reference_row, "prompt_tok_per_s"
        ),
        # The candidate's own repetitions are already a sibling key of the row
        # this block is attached to, so only the reference's are carried here.
        "reference_repetitions": reference_row.get("repetitions"),
    }


def select_quality_references(
    candidate_rows: list[dict[str, Any]], reference_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reference rows sharing the candidate's suite, model, suite version and seed.

    `task_suite` is part of the key for the same reason it is part of
    `results.resume_skip_reason`'s: one store -- and so one reference file --
    now holds rows from more than one suite, and two suites version
    themselves independently, so `model_id` + `suite_version` + seed is not
    on its own evidence that two rows describe the same batch. Without it, a
    reference file holding both suites for one model at a shared version
    number pulls both suites' rows into the comparison, trips the
    `unmatched_items` guard below, and reports `not_comparable` for a batch
    that reproduced item for item.
    """
    if not candidate_rows:
        return []
    first = candidate_rows[0]
    seed = first.get("sampling", {}).get("seed")
    return [
        row
        for row in reference_rows
        if row.get("task_suite") == first.get("task_suite")
        and row.get("model_id") == first.get("model_id")
        and row.get("suite_version") == first.get("suite_version")
        and row.get("sampling", {}).get("seed") == seed
    ]


def _comparable_field(
    candidate_by_item: dict[str, dict[str, Any]],
    reference_by_item: dict[str, dict[str, Any]],
) -> str | None:
    """Which per-item value this batch can be compared on, or `None`.

    `predicted_label` when any item carries one on either side, otherwise
    `item_score` when any item carries one. Resolved once for the whole batch
    rather than per item, so the returned block can name a single
    `compared_field` a reader can act on.

    A field is "carried" only when it is non-null somewhere: a batch whose
    every `predicted_label` is null on both sides is not reproducible on
    labels, it is unlabelled, and comparing two sets of nulls would publish
    `reproduced` off no evidence at all -- the exact failure `judge_probe.py`
    documents and writes around by hand.
    """
    for field in (QUALITY_COMPARED_LABEL, QUALITY_COMPARED_SCORE):
        for by_item in (candidate_by_item, reference_by_item):
            if any(row.get(field) is not None for row in by_item.values()):
                return field
    return None


def quality_verdict(
    candidate_rows: list[dict[str, Any]], reference_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute the quality verdict block, shared by every row of one suite batch.

    Methodology 8 asks for "identical per-item predicted labels **or
    scores**", and both halves are honoured here: an exact-match batch is
    decided on `predicted_label`, a graded one on `item_score`, and the
    returned block names which under `compared_field` so a reader can tell a
    label reproduction from a score reproduction without inspecting the rows.

    Deciding a graded batch on scores rather than on the generated text is
    deliberate: two different translations can coincidentally score the same
    and would be called reproduced. That is accepted, because the published
    rule is about scores, and pinning reproduction to output text instead
    would hold a re-run to a stricter standard than the one the PRD states.
    """
    matching = select_quality_references(candidate_rows, reference_rows)
    if not matching:
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": None,
            "differing_fields": [],
            "compared_field": None,
            "reason": "no reference row shares this batch's "
            "task_suite/model_id/suite_version/seed",
        }

    reference_by_item = {row["item_id"]: row for row in matching}
    candidate_by_item = {row["item_id"]: row for row in candidate_rows}
    # Compared before the labels: an item present on one side only cannot be
    # compared, and narrowing to the overlap silently would let a batch with
    # no shared item at all -- or one shared item out of forty -- report
    # `reproduced` off zero or near-zero evidence.
    unmatched_items = sorted(reference_by_item.keys() ^ candidate_by_item.keys())
    if unmatched_items:
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": matching[0].get("run_id"),
            "differing_fields": unmatched_items,
            "compared_field": None,
            "reason": "these item_ids are on one side only, so the two batches "
            "do not cover the same suite",
        }

    compared_field = _comparable_field(candidate_by_item, reference_by_item)
    if compared_field is None:
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": matching[0].get("run_id"),
            "differing_fields": [],
            "compared_field": None,
            "reason": "the two batches carry no comparable per-item value: "
            "every predicted_label and every item_score is null on both sides",
        }

    differing_items = sorted(
        item_id
        for item_id, row in candidate_by_item.items()
        if row.get(compared_field) != reference_by_item[item_id].get(compared_field)
    )
    verdict = VERDICT_NOT_REPRODUCED if differing_items else VERDICT_REPRODUCED

    return {
        "verdict": verdict,
        "reference_run_id": matching[0].get("run_id"),
        "differing_fields": differing_items,
        "compared_field": compared_field,
        "reason": None,
    }
