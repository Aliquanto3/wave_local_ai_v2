"""The three-state reproduction verdict: a re-run against a named reference
receives `reproduced`, `not_reproduced`, or `not_comparable`, stored on the row.

Reference matching never uses CPU, RAM, driver, or OS: only `engine_id`,
`engine_build`, `quant`, `gpu_name`, the raw `flags` list and `compute_mode`
decide whether a candidate and a reference row are the same run to compare
(PRD Methodology 8; plan.md's Decisions table resolves the tension between
"shares the re-run's fiche hash" and "CPU/RAM/driver/OS never block a
comparison" by naming these fields explicitly, separate from the fiche's full
identity hash -- a divergence from the PRD's wording that stays recorded, with
`compute_mode` now in both definitions).

A blocking field that is null on either side never matches, not even another
null: two unknown builds or GPUs are not evidence of the same run, so such a
pair is `not_comparable`, naming the null field. A fiche written under the
legacy projection carries no engine field at all (`hardware.FICHE_PROJECTIONS`
"1"); that absence reads as null here, so a run against such a reference is
`not_comparable` naming the engine fields rather than matched on a
`llama_cpp_build` nobody tied to an engine.

`compute_mode` blocks too (Methodology 8): a `gpu` row and a `cpu_only` row
from one machine are never a failed reproduction of each other. A fiche
written before projection "3" carries no mode, which reads as null here.

A GPU the machine registry declares absent is not an unknown GPU: on a fiche
whose `machine_id` names a machine declared GPU-less, a null `gpu_name` reads
as `GPU_DECLARED_ABSENT`, which matches itself, so two `cpu_only` runs on the
no-GPU machine can reproduce. A null `gpu_name` on any other fiche -- a GPU
that failed to capture on a machine that declares one, or an undeclared
machine -- stays null and never matches.

A quality batch is decided under one of two subject rules (Methodology 8). A
`local` subject is held to identical per-item output (`SUBJECT_RULE_IDENTICAL`).
A cloud subject is decided per item under its suite's declared divergence
tolerance (`SUBJECT_RULE_WITHIN_TOLERANCE`): `reproduced` while the share of
diverging items stays within it, `not_reproduced` beyond it, naming the
diverging items either way, so a provider's own non-determinism reads as a
property of the subject rather than as a failed reproduction. A cloud batch
that cannot be re-run deterministically at all (its dated model id is no
longer served, or its provider accepts no seed for it) is marked
single-run indicative, naming which, and is `not_comparable`, never
`not_reproduced`. This module owns the subject-side rule only; a judged
batch's judged component reuses it for its subject.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from wave_local_ai_v2 import fiche_registry, machines

VERDICT_REPRODUCED = "reproduced"
VERDICT_NOT_REPRODUCED = "not_reproduced"
VERDICT_NOT_COMPARABLE = "not_comparable"

# `engine_id` and `engine_build` generalise `llama_cpp_build`: two engines on
# one machine with one model are never the same run, so a mismatch is
# `not_comparable` naming the engine, never a false `not_reproduced`.
_RUNTIME_BLOCKING_FIELDS = (
    "engine_id",
    "engine_build",
    "quant",
    "gpu_name",
    "flags",
    "compute_mode",
)

# What `runtime_blocking_fields` reads a null `gpu_name` as, on a fiche whose
# machine the tracked registry declares GPU-less: a stated absence, equal to
# itself, rather than an unknown value that never matches.
GPU_DECLARED_ABSENT = "declared_absent"

# The two per-item values a quality batch can be compared on, in the order
# they are tried. Methodology 8's "identical per-item predicted labels or
# scores": an exact-match suite publishes the first, a graded one the second.
QUALITY_COMPARED_LABEL = "predicted_label"
QUALITY_COMPARED_SCORE = "item_score"

# The provider value a local subject's rows carry; every other provider is a
# cloud subject.
LOCAL_PROVIDER = "local"
SUBJECT_RULE_IDENTICAL = "identical"
SUBJECT_RULE_WITHIN_TOLERANCE = "within_tolerance"
SUBJECT_RULES = frozenset({SUBJECT_RULE_IDENTICAL, SUBJECT_RULE_WITHIN_TOLERANCE})
# Why a cloud batch cannot be re-run deterministically at all.
RERUN_MODEL_NOT_SERVED = "model_not_served"
RERUN_NO_SEED = "no_seed"
RERUN_BLOCKERS = frozenset({RERUN_MODEL_NOT_SERVED, RERUN_NO_SEED})
# The keys every quality verdict block carries from row schema "29", beside
# `verdict`, `reference_run_id`, `differing_fields`, `compared_field` and
# `reason`.
QUALITY_SUBJECT_RULE_KEYS = (
    "subject_rule",
    "tolerance",
    "divergence",
    "single_run_indicative",
)


class DecidingTolerance(TypedDict):
    """The tolerance a cloud batch was decided under, and who declared it."""

    value: float
    unit: str
    suite_id: str
    suite_version: str


class ReferenceMatch(TypedDict):
    reference_row: dict[str, Any]
    reference_fiche: dict[str, Any]


def runtime_blocking_fields(fiche: dict[str, Any]) -> dict[str, Any]:
    """Project `fiche` to exactly the fields a runtime reference match compares.

    A null `gpu_name` on a machine declared GPU-less reads as
    `GPU_DECLARED_ABSENT`; every other null stays null.
    """
    blocking = {key: fiche.get(key) for key in _RUNTIME_BLOCKING_FIELDS}
    if blocking["gpu_name"] is None and machines.declares_no_gpu(
        fiche.get("machine_id")
    ):
        blocking["gpu_name"] = GPU_DECLARED_ABSENT
    return blocking


def null_blocking_fields(fiche: dict[str, Any]) -> list[str]:
    """The blocking fields `fiche` leaves null, in declaration order."""
    blocking = runtime_blocking_fields(fiche)
    return [key for key in _RUNTIME_BLOCKING_FIELDS if blocking[key] is None]


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
    single-model snapshots, so no other ordering is meaningful. A reference
    whose fiche leaves a blocking field null is skipped: null never matches.
    """
    candidate_fiche = _resolve_fiche(candidate_row, registry_dir)
    if candidate_fiche is None or null_blocking_fields(candidate_fiche):
        return None
    candidate_blocking = runtime_blocking_fields(candidate_fiche)

    for reference_row in reference_rows:
        reference_fiche = _resolve_fiche(reference_row, registry_dir)
        if reference_fiche is None or null_blocking_fields(reference_fiche):
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
    differs" against an arbitrary reference. A field null on either side
    counts as differing, even when both are null.
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
            if candidate_blocking[key] is None
            or reference_blocking[key] is None
            or candidate_blocking[key] != reference_blocking[key]
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

    candidate_fiche = _resolve_fiche(candidate_row, registry_dir)
    candidate_nulls = null_blocking_fields(candidate_fiche) if candidate_fiche else []
    if candidate_nulls:
        return {
            "verdict": VERDICT_NOT_COMPARABLE,
            "reference_run_id": None,
            "differing_fields": candidate_nulls,
            "reason": "the candidate's fiche leaves a blocking field null, and an "
            "unknown value cannot be compared",
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
    `results.batch_rows`'s: one store -- and so one reference file --
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


def subject_rule_fields(provider: str, tolerance: DecidingTolerance) -> dict[str, Any]:
    """The subject rule a `provider` batch is decided under, and its tolerance.

    `identical` under no tolerance for a local subject; `within_tolerance`
    under `tolerance` for a cloud one. Shared with any writer that builds a
    quality verdict block without deciding it (the judge probe).
    """
    if provider == LOCAL_PROVIDER:
        return {"subject_rule": SUBJECT_RULE_IDENTICAL, "tolerance": None}
    return {"subject_rule": SUBJECT_RULE_WITHIN_TOLERANCE, "tolerance": dict(tolerance)}


def _quality_block(
    verdict: str,
    reference_run_id: object,
    differing_fields: list[str],
    compared_field: str | None,
    reason: str | None,
    *,
    rule_fields: dict[str, Any],
    divergence: float | None = None,
    single_run_indicative: str | None = None,
) -> dict[str, Any]:
    return {
        "verdict": verdict,
        "reference_run_id": reference_run_id,
        "differing_fields": differing_fields,
        "compared_field": compared_field,
        "reason": reason,
        **rule_fields,
        "divergence": divergence,
        "single_run_indicative": single_run_indicative,
    }


def quality_verdict(
    candidate_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
    *,
    provider: str,
    tolerance: DecidingTolerance,
    rerun_blocker: str | None = None,
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

    When several reference runs match the batch (the two-quality-runs
    protocol commits two per batch), the first run in file order is the
    reference, the same tie-break as `select_runtime_reference`: its items
    alone are compared, and `reference_run_id` names it.

    `provider` picks the subject rule: `local` is held to identical per-item
    values, under no tolerance (`tolerance: null` on the block); any other
    provider is decided under `tolerance`, the suite's declared divergence
    tolerance, named on the block with the suite version that declared it,
    together with the observed `divergence` (the share of diverging items).
    On a cloud batch an item whose compared value is null on either side
    counts as diverging: a null agreeing with a null is not evidence of a
    reproduction, so a cloud batch is never decided off null values.
    `rerun_blocker` (`RERUN_BLOCKERS`) marks a cloud batch that cannot be
    re-run deterministically at all: `not_comparable`, single-run indicative,
    never `not_reproduced`. A local subject has no such blocker.
    """
    is_local = provider == LOCAL_PROVIDER
    if rerun_blocker is not None and (is_local or rerun_blocker not in RERUN_BLOCKERS):
        raise ValueError(
            f"rerun_blocker {rerun_blocker!r} does not apply to provider "
            f"{provider!r}: only a cloud subject is marked single-run indicative, "
            f"for one of {', '.join(sorted(RERUN_BLOCKERS))}"
        )
    rule_fields = subject_rule_fields(provider, tolerance)

    matching = select_quality_references(candidate_rows, reference_rows)
    reference_run_id = matching[0].get("run_id") if matching else None
    if rerun_blocker is not None:
        return _quality_block(
            VERDICT_NOT_COMPARABLE,
            reference_run_id,
            [],
            None,
            f"single-run indicative ({rerun_blocker}): this cloud batch cannot "
            "be re-run deterministically, so no re-run can reproduce or "
            "contradict it",
            rule_fields=rule_fields,
            single_run_indicative=rerun_blocker,
        )
    if not matching:
        return _quality_block(
            VERDICT_NOT_COMPARABLE,
            None,
            [],
            None,
            "no reference row shares this batch's "
            "task_suite/model_id/suite_version/seed",
            rule_fields=rule_fields,
        )

    reference_by_item = {
        row["item_id"]: row for row in matching if row.get("run_id") == reference_run_id
    }
    candidate_by_item = {row["item_id"]: row for row in candidate_rows}
    # Compared before the labels: an item present on one side only cannot be
    # compared, and narrowing to the overlap silently would let a batch with
    # no shared item at all -- or one shared item out of forty -- report
    # `reproduced` off zero or near-zero evidence.
    unmatched_items = sorted(reference_by_item.keys() ^ candidate_by_item.keys())
    if unmatched_items:
        return _quality_block(
            VERDICT_NOT_COMPARABLE,
            reference_run_id,
            unmatched_items,
            None,
            "these item_ids are on one side only, so the two batches "
            "do not cover the same suite",
            rule_fields=rule_fields,
        )

    compared_field = _comparable_field(candidate_by_item, reference_by_item)
    if compared_field is None:
        return _quality_block(
            VERDICT_NOT_COMPARABLE,
            reference_run_id,
            [],
            None,
            "the two batches carry no comparable per-item value: "
            "every predicted_label and every item_score is null on both sides",
            rule_fields=rule_fields,
        )

    def diverges(item_id: str) -> bool:
        value = candidate_by_item[item_id].get(compared_field)
        reference_value = reference_by_item[item_id].get(compared_field)
        if not is_local and (value is None or reference_value is None):
            return True
        return bool(value != reference_value)

    differing_items = sorted(
        item_id for item_id in candidate_by_item if diverges(item_id)
    )
    divergence = len(differing_items) / len(candidate_by_item)
    if is_local:
        reproduced = not differing_items
    else:
        # Compared on the item count, with a rounding allowance, so a value
        # like 0.1 admits exactly 2 of 20 items despite binary floats.
        allowed = tolerance["value"] * len(candidate_by_item) + 1e-9
        reproduced = len(differing_items) <= allowed
    return _quality_block(
        VERDICT_REPRODUCED if reproduced else VERDICT_NOT_REPRODUCED,
        reference_run_id,
        differing_items,
        compared_field,
        None,
        rule_fields=rule_fields,
        divergence=divergence,
    )
