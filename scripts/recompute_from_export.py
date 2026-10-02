"""Recompute the published intervals and McNemar comparisons from the export alone.

A third party holding only the CSV tables `wave-local-ai-v2-export` writes
can check every interval and every exact-match comparison they publish. This
reader is that third party, run against ourselves: it uses the standard
library and nothing from this project, reads `quality_items.csv` and
`comparison_records.csv`, and recomputes from the per-item columns:

- each batch's interval block (the suite cell and each language cell), with
  the block's own recorded seed, resample count, confidence level and draw
  procedure, implemented here from the definition `column_dictionary.csv`
  states for `score_interval_draw_procedure_id`;
- each `mcnemar_exact` comparison's contingency, paired n and exact p-value,
  from the two sides' per-item `correct` columns joined on `item_id`;
- each family's Holm-adjusted p-values, from its comparisons' raw p-values.

Every recomputed value is compared, as text, with the published cell (floats
are written as Python's shortest round-trip `repr`). Exit 0 when every one
matches, 1 when any differs or a block names a procedure not implemented here.

    uv run python scripts/recompute_from_export.py <export-dir>
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

QUALITY_TABLE = "quality_items.csv"
RECORDS_TABLE = "comparison_records.csv"
DRAW_PROCEDURE = "stdlib-getrandbits-percentile/1"
METHOD = "percentile"
MCNEMAR = "mcnemar_exact"

_INTERVAL = "score_interval_"
_CELL_KEYS = ("n", "lower", "upper", "minimum_detectable_effect", "null_reason")
_BATCH_FIELDS = ("run_id", "provider", "model_id", "prompt_variant_id")

Row = dict[str, str]


@dataclass(frozen=True)
class Check:
    """One recomputed value beside the published cell it must equal."""

    subject: str
    field: str
    published: str
    recomputed: str

    @property
    def matches(self) -> bool:
        return self.published == self.recomputed


def read_table(path: Path) -> list[Row]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _cell(value: object) -> str:
    """A value as the export writes it: empty for null, `repr` for a float."""
    if value is None:
        return ""
    return repr(value) if isinstance(value, float) else str(value)


# --------------------------------------------------------------------------
# The interval


def item_value(row: Row) -> float:
    """An item's value in its cell: its item_score, else correct as 1 or 0."""
    if row.get("item_score"):
        return float(row["item_score"])
    return 1.0 if row["correct"] == "true" else 0.0


def _quantile(ordered: Sequence[float], q: float) -> float:
    h = (len(ordered) - 1) * q
    below = math.floor(h)
    low = ordered[below]
    high = ordered[min(below + 1, len(ordered) - 1)]
    return low + (h - below) * (high - low)


def interval_cell(
    values: Sequence[float], *, seed: int, resamples: int, level: float
) -> dict[str, object]:
    """One cell, drawn one index at a time as the published procedure says."""
    n = len(values)
    if n == 0:
        return {"n": 0, "null_reason": "no_items"}
    if all(value == values[0] for value in values):
        return {"n": n, "null_reason": "zero_width"}
    draw = random.Random(seed).getrandbits
    bits = n.bit_length()
    means: list[float] = []
    for _ in range(resamples):
        drawn: list[float] = []
        for _ in range(n):
            index = draw(bits)
            while index >= n:
                index = draw(bits)
            drawn.append(values[index])
        means.append(math.fsum(drawn) / n)
    means.sort()
    tail = (1.0 - level) / 2.0
    lower = _quantile(means, tail)
    upper = _quantile(means, 1.0 - tail)
    return {
        "n": n,
        "lower": lower,
        "upper": upper,
        "minimum_detectable_effect": (upper - lower) / 2.0,
    }


def _batch_key(row: Row) -> tuple[str, ...]:
    return tuple(row.get(field, "") for field in _BATCH_FIELDS)


def _languages(header: Sequence[str]) -> list[str]:
    prefix, suffix = f"{_INTERVAL}by_language_", "_n"
    return [
        column[len(prefix) : -len(suffix)]
        for column in header
        if column.startswith(prefix) and column.endswith(suffix)
    ]


def check_intervals(rows: Sequence[Row]) -> list[Check]:
    """Every batch carrying a block, every cell of it, recomputed."""
    batches: dict[tuple[str, ...], list[Row]] = defaultdict(list)
    for row in rows:
        batches[_batch_key(row)].append(row)
    languages = _languages(list(rows[0])) if rows else []
    checks: list[Check] = []
    for key, batch in sorted(batches.items()):
        carrying = [row for row in batch if row.get(f"{_INTERVAL}method")]
        if not carrying:
            continue
        subject = "interval " + " ".join(part for part in key if part)
        header = {
            column: {row[column] for row in carrying}
            for column in carrying[0]
            if column.startswith(_INTERVAL)
        }
        if any(len(values) > 1 for values in header.values()):
            checks.append(Check(subject, "block", "one block per batch", "several"))
            continue
        block = {column: next(iter(values)) for column, values in header.items()}
        method = block[f"{_INTERVAL}method"]
        procedure = block[f"{_INTERVAL}draw_procedure_id"]
        if (method, procedure) != (METHOD, DRAW_PROCEDURE):
            checks.append(
                Check(subject, "procedure", f"{method} {procedure}", "not implemented")
            )
            continue
        seed = int(block[f"{_INTERVAL}seed"])
        resamples = int(block[f"{_INTERVAL}resamples"])
        level = float(block[f"{_INTERVAL}confidence_level"])
        ordered = sorted(batch, key=lambda row: row["item_id"])
        cells: list[tuple[str, list[Row]]] = [("suite", ordered)]
        cells += [
            (
                f"by_language_{language}",
                [row for row in ordered if row["language"] == language],
            )
            for language in languages
        ]
        for name, items in cells:
            recomputed = interval_cell(
                [item_value(row) for row in items],
                seed=seed,
                resamples=resamples,
                level=level,
            )
            for cell_key in _CELL_KEYS:
                column = f"{_INTERVAL}{name}_{cell_key}"
                checks.append(
                    Check(
                        subject,
                        column,
                        block[column],
                        _cell(recomputed.get(cell_key)),
                    )
                )
    return checks


# --------------------------------------------------------------------------
# McNemar and Holm


def _selector(record: Row, side: str) -> dict[str, str]:
    prefix = f"comparison_{side}_selector_"
    return {
        column[len(prefix) :]: value
        for column, value in record.items()
        if column.startswith(prefix) and value
    }


def side_values(rows: Sequence[Row], record: Row, side: str) -> dict[str, bool]:
    """`item_id` to `correct` for the side's rows; an empty `correct` is unobserved."""
    run_id = record[f"comparison_{side}_run_id"]
    selector = _selector(record, side)
    return {
        row["item_id"]: row["correct"] == "true"
        for row in rows
        if row["run_id"] == run_id
        and all(row.get(field) == value for field, value in selector.items())
        and row["correct"]
    }


def mcnemar(pairs: Sequence[tuple[bool, bool]]) -> dict[str, object]:
    """McNemar's exact test: p = min(1, 2 * sum_{k <= min(b, c)} C(b+c, k) / 2^(b+c))."""
    b = sum(1 for reference, candidate in pairs if reference and not candidate)
    c = sum(1 for reference, candidate in pairs if candidate and not reference)
    both = sum(1 for reference, candidate in pairs if reference and candidate)
    discordant = b + c
    p_value: float | None = None
    if discordant:
        tail = sum(math.comb(discordant, k) for k in range(min(b, c) + 1))
        p_value = float(min(Fraction(1), Fraction(2 * tail, 2**discordant)))
    return {
        "paired_n": len(pairs),
        "result_contingency_both_correct": both,
        "result_contingency_reference_only_correct": b,
        "result_contingency_candidate_only_correct": c,
        "result_contingency_both_wrong": len(pairs) - b - c - both,
        "result_discordant_n": discordant,
        "result_p_value": p_value,
    }


def check_mcnemar(rows: Sequence[Row], records: Sequence[Row]) -> list[Check]:
    """Every exact-match comparison, recomputed from the per-item columns."""
    checks: list[Check] = []
    for record in records:
        if record["record_kind"] != "comparison":
            continue
        if record["comparison_test"] != MCNEMAR:
            continue
        reference = side_values(rows, record, "reference")
        candidate = side_values(rows, record, "candidate")
        paired = sorted(reference.keys() & candidate.keys())
        recomputed = mcnemar([(reference[i], candidate[i]) for i in paired])
        subject = (
            f"mcnemar {record['comparison_reference_run_id']} "
            f"{_selector(record, 'reference')} vs "
            f"{record['comparison_candidate_run_id']} "
            f"{_selector(record, 'candidate')}"
        )
        checks += [
            Check(
                subject,
                f"comparison_{field}",
                record[f"comparison_{field}"],
                _cell(value),
            )
            for field, value in recomputed.items()
        ]
    return checks


def holm(p_values: Sequence[float]) -> list[float]:
    """Holm's step-down: max over j <= i of min(1, (m - j + 1) * p_(j)), exactly."""
    m = len(p_values)
    order = sorted(range(m), key=lambda index: p_values[index])
    adjusted = [0.0] * m
    running = Fraction(0)
    for rank, index in enumerate(order):
        running = max(running, min(Fraction(1), (m - rank) * Fraction(p_values[index])))
        adjusted[index] = float(running)
    return adjusted


def check_holm(records: Sequence[Row]) -> list[Check]:
    """Each family's adjusted p-values, from the raw p of its non-refused members.

    A null raw p enters as 1 and keeps its adjusted p null. A family without
    `tested_count` is an earlier record version and is not recomputed.
    """
    members: dict[str, list[Row]] = defaultdict(list)
    for record in records:
        if record["record_kind"] == "comparison" and record.get("family_tested_count"):
            members[record["family_family_id"]].append(record)
    checks: list[Check] = []
    for family_id, family in sorted(members.items()):
        tested = [m for m in family if m["comparison_comparison_kind"] != "refusal"]
        raw = [
            float(m["comparison_raw_p_value"]) if m["comparison_raw_p_value"] else 1.0
            for m in tested
        ]
        for member, adjusted in zip(tested, holm(raw), strict=True):
            if member["comparison_raw_p_value"]:
                checks.append(
                    Check(
                        f"holm family {family_id[:12]}",
                        "comparison_adjusted_p_value",
                        member["comparison_adjusted_p_value"],
                        _cell(adjusted),
                    )
                )
    return checks


# --------------------------------------------------------------------------
# The command


def recompute(export_dir: Path) -> list[Check]:
    rows = read_table(export_dir / QUALITY_TABLE)
    records = read_table(export_dir / RECORDS_TABLE)
    return check_intervals(rows) + check_mcnemar(rows, records) + check_holm(records)


def main(argv: Sequence[str] | None = None, echo: Callable[[str], None] = print) -> int:
    parser = argparse.ArgumentParser(
        prog="recompute_from_export",
        description=__doc__.splitlines()[0] if __doc__ else None,
    )
    parser.add_argument("export_dir", type=Path)
    args = parser.parse_args(argv)
    checks = recompute(args.export_dir)
    for check in checks:
        verdict = "match" if check.matches else "MISMATCH"
        echo(
            f"{verdict}  {check.subject}  {check.field}: published "
            f"{json.dumps(check.published)}, recomputed {json.dumps(check.recomputed)}"
        )
    subjects = {check.subject.split(" ")[0] for check in checks}
    mismatches = [check for check in checks if not check.matches]
    echo(
        f"{len(checks)} values recomputed ({', '.join(sorted(subjects)) or 'none'}), "
        f"{len(mismatches)} differ"
    )
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
