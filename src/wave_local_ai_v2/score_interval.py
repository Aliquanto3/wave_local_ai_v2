"""The interval a quality score is published with, and what it could resolve.

Every quality batch publishes, beside its suite score and each per-language
cell, a percentile bootstrap confidence interval and the minimum detectable
effect read off the same resample (Methodology 24). A seed alone does not
reproduce an interval -- `random.Random(7)`, numpy's generator and a library's
own bootstrap draw three different resample sequences from it -- so the block
a row carries holds six values, not one: the confidence level, the resample
count, the method, the seed, the generator's identity and version, and the
draw procedure's versioned id. That id names the definition below; changing
any part of it is a new id.

Draw procedure `stdlib-getrandbits-percentile/1`:

- **Items.** A cell's items are taken in ascending `item_id` order, so the
  draw does not depend on the order rows arrive in. The suite cell holds
  every item of the batch (unstratified); a language cell holds that
  language's items only (resampled within its language). A failed
  generation is in the set as the zero Methodology 9 makes it.
- **Draw order.** Each cell draws from its own freshly seeded
  `random.Random(seed)`, so any one cell replays from the block alone.
  Resample `b = 0 .. B-1` draws `n` indexes in turn; one index is
  `getrandbits(n.bit_length())`, redrawn until it is below `n`. Only
  `getrandbits` is called. Python guarantees reproducibility only for
  `random()`; the seeded Mersenne Twister's `getrandbits` stream has been
  stable in practice across CPython versions, where `choices` and
  `randrange` have changed, and the block records the generator's version so
  a replay under another one can be told apart.
- **Statistic.** A resample's value is `math.fsum` of its drawn values over
  `n`, correctly rounded and independent of summation order.
- **Ties and interpolation.** The `B` resample values are sorted ascending.
  Tied values are equal floats, so their relative order cannot move a bound.
  The bounds are the quantiles at `q = (1 - level) / 2` and `1 - q` by linear
  interpolation between order statistics at position `h = (B - 1) * q`
  (Hyndman and Fan type 7, scipy's and numpy's default).
- **Minimum detectable effect.** Half the interval's width, from the same
  sorted resample: the smallest difference this suite and scoring kind could
  have told from noise, which stops "not distinguishable" being read as
  "the same".

A cell is a value or a named reason, never both, and each reason is decided
by the state that names it: `no_items` when the cell holds no item (a
language absent from the suite), `zero_width` when every item carries the
same value (a suite scored 1.0 or 0.0), whose every resample is identical and
whose `[1.0, 1.0]` would read as certainty.

Standard library only at runtime; scipy is a dev-only test oracle.
"""

from __future__ import annotations

import math
import operator
import random
import struct
from collections.abc import Iterable, Iterator, Mapping, Sequence
from itertools import batched, chain, islice, repeat
from typing import Any, TypedDict

from wave_local_ai_v2.subset_sampler import drawing_generator
from wave_local_ai_v2.suite_gate import LANGUAGES

CONFIDENCE_LEVEL = 0.95
RESAMPLES = 10_000
METHOD_PERCENTILE = "percentile"
DRAW_PROCEDURE_ID = "stdlib-getrandbits-percentile/1"
# Fixed and recorded on every block: an interval replays from what the row
# says, never from a seed chosen at write time and lost.
DEFAULT_SEED = 20261002

NULL_NO_ITEMS = "no_items"
NULL_ZERO_WIDTH = "zero_width"
NULL_REASONS: frozenset[str] = frozenset({NULL_NO_ITEMS, NULL_ZERO_WIDTH})

HEADER_KEYS: frozenset[str] = frozenset(
    {
        "confidence_level",
        "resamples",
        "method",
        "seed",
        "generator",
        "draw_procedure_id",
    }
)
BLOCK_KEYS: frozenset[str] = HEADER_KEYS | {"suite", "by_language"}
CELL_VALUE_KEYS: tuple[str, ...] = ("lower", "upper", "minimum_detectable_effect")
CELL_KEYS: frozenset[str] = frozenset({"n", *CELL_VALUE_KEYS, "null_reason"})
GENERATOR_KEYS: frozenset[str] = frozenset({"library", "version"})

# Absolute slack for "the estimate lies inside its interval": the published
# score is a plain sum over n, the bounds an `fsum`, and the two may differ
# in the last bit on a graded score.
_INSIDE_SLACK = 1e-12


class ScoreIntervalError(ValueError):
    """Raised for a block this code cannot replay: an unknown method or draw
    procedure."""


class IntervalInvariantError(ValueError):
    """Raised when a batch's interval does not qualify the score it sits
    beside: the estimate outside its interval, an n that differs from the
    published breakdown's, or two rows of one batch carrying different
    blocks."""


class IntervalCell(TypedDict):
    """One cell's interval: three values and no reason, or no values and one."""

    n: int
    lower: float | None
    upper: float | None
    minimum_detectable_effect: float | None
    null_reason: str | None


def item_value(fields: Mapping[str, Any]) -> float:
    """The value one item contributes to its cell's mean.

    An exact-match item contributes 1.0 when `correct` and 0.0 otherwise -- a
    failed generation is `correct=False`, so it is the zero Methodology 9
    makes it. A graded item (one carrying `item_score`) contributes its
    score, a failure's 0.0 included.
    """
    score = fields.get("item_score")
    if score is not None:
        return float(score)
    return 1.0 if fields["correct"] else 0.0


# Words read from the generator per bulk call: bounds the memory a draw holds
# (a few MB) whatever the cell's n and the resample count.
_WORDS_PER_CHUNK = 1 << 16


def _index_stream(seed: int, n: int) -> Iterator[int]:
    """A cell's accepted index draws, from its freshly seeded generator.

    Drawing `getrandbits(bits)` and redrawing a rejected value at once is the
    same sequence as filtering one stream of such draws on `< n`; resample
    `b` takes accepted draws `b*n .. b*n + n - 1`. For `bits <= 32`, CPython's
    `getrandbits(bits)` is one 32-bit Mersenne Twister word shifted right by
    `32 - bits`, and `getrandbits(32 * m)` is `m` such words, the first drawn
    in the least significant position. So the stream is read here in bounded
    chunks of `m` words, unpacked little-endian and shifted -- the same draws
    with no Python-level call per index (`tests/test_score_interval.py`
    checks it against the one-call-per-draw loop).
    """
    bits = n.bit_length()
    getrandbits = random.Random(seed).getrandbits
    unpack = struct.Struct(f"<{_WORDS_PER_CHUNK}I").unpack

    def chunk(_: object) -> list[int]:
        raw = getrandbits(32 * _WORDS_PER_CHUNK).to_bytes(
            4 * _WORDS_PER_CHUNK, "little"
        )
        return list(
            filter(n.__gt__, map(operator.rshift, unpack(raw), repeat(32 - bits)))
        )

    # One Python call per chunk, none per index: the chain iterates in C.
    return chain.from_iterable(map(chunk, repeat(None)))


def _accepted_indexes(seed: int, n: int, count: int) -> list[int]:
    """The first `count` draws of the cell's index stream."""
    return list(islice(_index_stream(seed, n), count))


def resample_values(
    values: Sequence[float], *, seed: int, resamples: int
) -> list[float]:
    """The `resamples` bootstrap means of `values`, sorted ascending.

    `values` must already be in the cell's canonical (`item_id`) order and
    non-empty. Draws exactly as the module docstring's procedure says, one
    resample at a time: only the means are held, never every draw.
    """
    n = len(values)
    drawn = map(values.__getitem__, islice(_index_stream(seed, n), n * resamples))
    means = list(map(operator.truediv, map(math.fsum, batched(drawn, n)), repeat(n)))
    means.sort()
    return means


def quantile(sorted_values: Sequence[float], q: float) -> float:
    """The type-7 quantile of an ascending sequence: linear between order
    statistics at position `(len - 1) * q`."""
    position = (len(sorted_values) - 1) * q
    below = math.floor(position)
    above = min(below + 1, len(sorted_values) - 1)
    fraction = position - below
    low = sorted_values[below]
    return low + fraction * (sorted_values[above] - low)


def _null_cell(n: int, reason: str) -> IntervalCell:
    return IntervalCell(
        n=n,
        lower=None,
        upper=None,
        minimum_detectable_effect=None,
        null_reason=reason,
    )


def bootstrap_cell(
    values: Sequence[float],
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = RESAMPLES,
    confidence_level: float = CONFIDENCE_LEVEL,
) -> IntervalCell:
    """The percentile interval and minimum detectable effect over `values`.

    `no_items` when `values` is empty and `zero_width` when every value is
    the same, each decided on the values themselves, never on a computed
    width.
    """
    n = len(values)
    if n == 0:
        return _null_cell(0, NULL_NO_ITEMS)
    if all(value == values[0] for value in values):
        return _null_cell(n, NULL_ZERO_WIDTH)
    means = resample_values(values, seed=seed, resamples=resamples)
    tail = (1.0 - confidence_level) / 2.0
    lower = quantile(means, tail)
    upper = quantile(means, 1.0 - tail)
    return IntervalCell(
        n=n,
        lower=lower,
        upper=upper,
        minimum_detectable_effect=(upper - lower) / 2.0,
        null_reason=None,
    )


def _ordered_values(
    pairs: Iterable[tuple[Mapping[str, Any], float]],
) -> list[float]:
    return [value for _, value in sorted(pairs, key=lambda pair: pair[0]["item_id"])]


def interval_block(
    items: Sequence[Mapping[str, Any]],
    values: Sequence[float],
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = RESAMPLES,
    confidence_level: float = CONFIDENCE_LEVEL,
) -> dict[str, Any]:
    """The interval block one batch publishes on every row.

    `items` (each carrying `item_id` and `language`) and `values` are paired
    by position. The suite cell resamples every item unstratified; each
    language cell resamples that language's items only.
    """
    pairs = list(zip(items, values, strict=True))

    def cell(selected: list[tuple[Mapping[str, Any], float]]) -> IntervalCell:
        return bootstrap_cell(
            _ordered_values(selected),
            seed=seed,
            resamples=resamples,
            confidence_level=confidence_level,
        )

    return {
        "confidence_level": confidence_level,
        "resamples": resamples,
        "method": METHOD_PERCENTILE,
        "seed": seed,
        "generator": drawing_generator(),
        "draw_procedure_id": DRAW_PROCEDURE_ID,
        "suite": cell(pairs),
        "by_language": {
            language: cell([pair for pair in pairs if pair[0]["language"] == language])
            for language in LANGUAGES
        },
    }


def replay(
    block: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    values: Sequence[float],
) -> dict[str, Any]:
    """Recompute a recorded block over `items`, under its own recorded values.

    Refuses a method or draw procedure this code does not implement rather
    than recomputing under a different one. The recorded generator is carried
    through, not enforced: the procedure draws only `getrandbits`, and a
    generator that draws differently shows up as a different interval.
    """
    if block["method"] != METHOD_PERCENTILE:
        raise ScoreIntervalError(
            f"method {block['method']!r} is not one this code replays "
            f"({METHOD_PERCENTILE!r})"
        )
    if block["draw_procedure_id"] != DRAW_PROCEDURE_ID:
        raise ScoreIntervalError(
            f"draw procedure {block['draw_procedure_id']!r} is not one this code "
            f"replays ({DRAW_PROCEDURE_ID!r})"
        )
    replayed = interval_block(
        items,
        values,
        seed=block["seed"],
        resamples=block["resamples"],
        confidence_level=block["confidence_level"],
    )
    replayed["generator"] = dict(block["generator"])
    return replayed


def _score_and_breakdown(row: Mapping[str, Any]) -> tuple[Any, Any, str]:
    """The row's published suite score, its breakdown and the cell's score key."""
    if row.get("suite_accuracy") is not None:
        return row["suite_accuracy"], row["language_breakdown"], "accuracy"
    return row.get("suite_score"), row.get("score_breakdown"), "score"


def _check_inside(where: str, estimate: Any, cell: Mapping[str, Any]) -> None:
    if cell["null_reason"] is not None:
        return
    if not (cell["lower"] - _INSIDE_SLACK <= estimate <= cell["upper"] + _INSIDE_SLACK):
        raise IntervalInvariantError(
            f"{where}: point estimate {estimate!r} lies outside its interval "
            f"[{cell['lower']!r}, {cell['upper']!r}]"
        )


def _check_row(row: Mapping[str, Any]) -> None:
    block = row["score_interval"]
    item = row.get("item_id")
    estimate, breakdown, key = _score_and_breakdown(row)
    if estimate is None or not isinstance(breakdown, Mapping):
        raise IntervalInvariantError(
            f"row {item!r} carries an interval beside no published suite score"
        )
    published_n = sum(cell["n"] for cell in breakdown.values())
    if block["suite"]["n"] != published_n:
        raise IntervalInvariantError(
            f"row {item!r}: the suite interval was computed over "
            f"n={block['suite']['n']} but the published breakdown holds "
            f"n={published_n}"
        )
    _check_inside(f"row {item!r} suite", estimate, block["suite"])
    for language, cell in block["by_language"].items():
        published = breakdown.get(language)
        published_cell_n = published["n"] if published is not None else 0
        if cell["n"] != published_cell_n:
            raise IntervalInvariantError(
                f"row {item!r}: the {language} interval was computed over "
                f"n={cell['n']} but the published {language} cell holds "
                f"n={published_cell_n}"
            )
        if published is not None:
            _check_inside(f"row {item!r} {language}", published[key], cell)


def check_batch_invariants(rows: Iterable[Mapping[str, Any]]) -> None:
    """Raise `IntervalInvariantError` unless one batch's intervals qualify
    its scores.

    Three invariants, over every row carrying a block: the point estimate
    lies inside its own interval (suite and each language); the n each
    interval was computed over equals the n `language_breakdown` or
    `score_breakdown` publishes; and every such row carries the identical
    block. A row with a null block (a partial batch's, written before a
    resume completed it) publishes no score and is never rewritten, so it is
    not held to the block its batch later published.
    """
    first: Mapping[str, Any] | None = None
    for row in rows:
        block = row.get("score_interval")
        if block is None:
            continue
        _check_row(row)
        if first is None:
            first = row
        elif block != first["score_interval"]:
            raise IntervalInvariantError(
                f"rows {first.get('item_id')!r} and {row.get('item_id')!r} of one "
                "batch carry different interval blocks"
            )
