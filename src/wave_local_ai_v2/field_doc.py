"""How one published field is described: its meaning, its unit, its empty cell.

Shared by the modules that write a record and the export that flattens it:
`comparison.py` and `leader_set.py` define the fields of the records they
write, and `bundle_export.py` reads those definitions into its column
dictionary rather than redefining them.
"""

from __future__ import annotations

from dataclasses import dataclass

# Units a field description names; one spelling for every module.
ID = "identifier"
TEXT = "text"
BOOL = "boolean"
COUNT = "count"
JSON_ARRAY = "JSON array"
JSON_OBJECT = "JSON object"
SHA = "SHA-256, lowercase hex"
RATIO = "ratio, 0..1"
PROBABILITY = "probability, 0..1"
SUITE_SCORE = "the suite's score scale (suite_accuracy or suite_score, 0..1)"


@dataclass(frozen=True)
class FieldDoc:
    """One source field's meaning, unit, and what an empty cell means for it.

    For a field a record module defines, `empty` says what a null value means
    for that field (its named reasons); the export adds what an empty cell
    means on a table row of another kind.
    """

    meaning: str
    unit: str
    empty: str | None = None
