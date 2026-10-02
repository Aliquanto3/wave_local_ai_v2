"""Tests for the published score interval: oracles, replay, reasons, invariants.

The bounds are checked against references named in advance -- the exact
Binomial(n, p)/n quantiles within one grid step, the Wilson interval as a
coarse sanity check, scipy's quantile and bootstrap as independent
implementations -- never against this module's own output.
"""

from __future__ import annotations

import ast
import random
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from scipy import stats

from wave_local_ai_v2 import score_interval
from wave_local_ai_v2.score_interval import (
    DEFAULT_SEED,
    DRAW_PROCEDURE_ID,
    NULL_NO_ITEMS,
    NULL_ZERO_WIDTH,
    IntervalInvariantError,
    ScoreIntervalError,
    bootstrap_cell,
    check_batch_invariants,
    interval_block,
    item_value,
    quantile,
    replay,
    resample_values,
)
from wave_local_ai_v2.scoring import score_suite_by_language
from wave_local_ai_v2.subset_sampler import drawing_generator

SRC = Path(__file__).resolve().parent.parent / "src" / "wave_local_ai_v2"


def _proportion(n: int, p: float) -> list[float]:
    correct = round(n * p)
    return [1.0] * correct + [0.0] * (n - correct)


def _items(languages: list[str]) -> list[dict[str, Any]]:
    return [
        {"item_id": f"item-{index:03d}", "language": language}
        for index, language in enumerate(languages)
    ]


# 20 items: en 8, fr 6, de 6; 16 correct (0.80), the misses spread across
# the three languages.
_LANGUAGES = ["en"] * 8 + ["fr"] * 6 + ["de"] * 6
_CORRECT = [
    *(True, True, True, True, True, True, False, True),
    *(True, True, False, True, True, True),
    *(True, False, True, True, False, True),
]


def _batch_rows(
    *, block: dict[str, Any] | None = None, correct: list[bool] | None = None
) -> list[dict[str, Any]]:
    """One exact-match batch as rows: score, breakdown and block over 20 items."""
    correct = _CORRECT if correct is None else correct
    items = _items(_LANGUAGES)
    scored = [
        {
            "item_id": item["item_id"],
            "expected_label": "billing",
            "predicted_label": "billing" if ok else "other",
            "correct": ok,
            "failure_reason": None,
        }
        for item, ok in zip(items, correct, strict=True)
    ]
    accuracy = sum(correct) / len(correct)
    breakdown = score_suite_by_language(items, scored)  # type: ignore[arg-type]
    if block is None:
        block = interval_block(items, [1.0 if ok else 0.0 for ok in correct])
    return [
        {
            "item_id": item["item_id"],
            "suite_accuracy": accuracy,
            "language_breakdown": breakdown,
            "score_interval": block,
        }
        for item in items
    ]


# --- the draw procedure ---------------------------------------------------


def test_hand_computed_interval_on_a_small_fixture() -> None:
    # The generator's bit stream for seed 7, two bits at a time, pinned.
    bits = random.Random(7).getrandbits
    assert [bits(2) for _ in range(15)] == [
        1, 3, 0, 1, 2, 0, 0, 3, 2, 0, 1, 2, 0, 3, 2,
    ]  # fmt: skip
    # Values [0, 0, 1], n=3, two-bit draws, 3 rejected:
    #   resample 0: 1, (3), 0, 1 -> [0, 0, 0] -> 0
    #   resample 1: 2, 0, 0      -> [1, 0, 0] -> 1/3
    #   resample 2: (3), 2, 0, 1 -> [1, 0, 0] -> 1/3
    #   resample 3: 2, 0, (3), 2 -> [1, 0, 1] -> 2/3
    #   resample 4: 0, 0, 0      -> [0, 0, 0] -> 0
    assert resample_values([0.0, 0.0, 1.0], seed=7, resamples=5) == [
        0.0, 0.0, 1 / 3, 1 / 3, 2 / 3,
    ]  # fmt: skip
    # Type 7: h = 4 * 0.025 = 0.1 -> 0.0; h = 4 * 0.975 = 3.9 -> 1/3 + 0.9/3.
    cell = bootstrap_cell([0.0, 0.0, 1.0], seed=7, resamples=5)
    assert cell["lower"] == 0.0
    assert cell["upper"] == pytest.approx(1 / 3 + 0.9 * (2 / 3 - 1 / 3), abs=1e-15)
    assert cell["minimum_detectable_effect"] == pytest.approx(
        cell["upper"] / 2, abs=1e-15
    )
    assert cell["n"] == 3
    assert cell["null_reason"] is None


@pytest.mark.parametrize("n", [1, 2, 3, 7, 8, 9, 20, 33, 64, 65, 100, 1000, 1025])
def test_the_bulk_draw_is_the_one_call_per_draw_procedure(n: int) -> None:
    # The procedure as published: one getrandbits(bits) call per index, a
    # rejected value redrawn at once. The implementation reads the same
    # stream in bounded chunks and must draw exactly these indexes; at
    # n >= 1000 the draw runs past one chunk (65 536 words), so the chunk seam
    # is covered too.
    count = 5 * n if n < 1000 else 3 * score_interval._WORDS_PER_CHUNK
    for seed in (0, 7, DEFAULT_SEED):
        bits = random.Random(seed).getrandbits
        expected = []
        while len(expected) < count:
            index = bits(n.bit_length())
            if index < n:
                expected.append(index)
        assert score_interval._accepted_indexes(seed, n, count) == expected


@pytest.mark.parametrize("n", [20, 100])
def test_bounds_equal_the_exact_binomial_within_one_grid_step(n: int) -> None:
    cell = bootstrap_cell(_proportion(n, 0.80))
    low, high = stats.binom.ppf([0.025, 0.975], n, 0.80) / n
    step = 1 / n
    assert cell["lower"] is not None and cell["upper"] is not None
    assert abs(cell["lower"] - low) <= step + 1e-12
    assert abs(cell["upper"] - high) <= step + 1e-12


def test_wilson_is_a_coarse_sanity_check_at_n_100() -> None:
    cell = bootstrap_cell(_proportion(100, 0.80))
    wilson = stats.binomtest(80, 100).proportion_ci(method="wilson")
    assert cell["lower"] is not None and cell["upper"] is not None
    assert abs(cell["lower"] - wilson.low) <= 0.05
    assert abs(cell["upper"] - wilson.high) <= 0.05


def test_percentile_interpolation_matches_scipy_quantile() -> None:
    rng = random.Random(3)
    for size in (2, 7, 100, 10_000):
        values = sorted(rng.random() for _ in range(size))
        for q in (0.0, 0.025, 0.5, 0.975, 1.0):
            oracle = float(stats.quantile(np.array(values), q))
            assert quantile(values, q) == pytest.approx(oracle, abs=1e-15)


@pytest.mark.parametrize("n", [20, 100])
def test_interval_agrees_with_scipy_bootstrap_within_one_grid_step(n: int) -> None:
    # Where the conventions match -- percentile method, 95%, 10 000
    # resamples, type-7 quantiles -- an independent implementation drawing
    # its own resamples lands within one grid step of ours.
    values = _proportion(n, 0.80)
    cell = bootstrap_cell(values)
    oracle = stats.bootstrap(
        (np.array(values),),
        np.mean,
        method="percentile",
        confidence_level=0.95,
        n_resamples=10_000,
        rng=np.random.default_rng(DEFAULT_SEED),
    ).confidence_interval
    assert abs(cell["lower"] - oracle.low) <= 1 / n + 1e-12  # type: ignore[operator]
    assert abs(cell["upper"] - oracle.high) <= 1 / n + 1e-12  # type: ignore[operator]


def test_convention_the_same_seed_draws_differently_under_numpy() -> None:
    # Why the block records the generator and the draw procedure, not only
    # the seed: numpy's generator seeded alike draws another resample set.
    values = [0.0, 0.25, 0.5, 0.75, 1.0, 0.1, 0.9, 0.3]
    ours = resample_values(values, seed=DEFAULT_SEED, resamples=200)
    data = np.array(values)
    numpy_draw = np.random.default_rng(DEFAULT_SEED).integers(
        0, len(values), size=(200, len(values))
    )
    theirs = sorted(float(m) for m in data[numpy_draw].mean(axis=1))
    assert ours != theirs


def test_convention_scipy_publishes_a_zero_width_interval_we_name() -> None:
    oracle = stats.bootstrap(
        (np.ones(20),), np.mean, method="percentile", rng=np.random.default_rng(1)
    ).confidence_interval
    assert (oracle.low, oracle.high) == (1.0, 1.0)
    cell = bootstrap_cell([1.0] * 20)
    assert cell["null_reason"] == NULL_ZERO_WIDTH
    assert cell["lower"] is None and cell["upper"] is None


def test_minimum_detectable_effect_is_the_half_width_of_the_same_resample() -> None:
    cell = bootstrap_cell(_proportion(20, 0.80))
    assert cell["lower"] is not None and cell["upper"] is not None
    assert cell["minimum_detectable_effect"] == (cell["upper"] - cell["lower"]) / 2


# --- the block and its replay ----------------------------------------------


def test_block_carries_the_six_values_beside_the_cells() -> None:
    items = _items(_LANGUAGES)
    block = interval_block(items, [1.0 if ok else 0.0 for ok in _CORRECT])
    assert block["confidence_level"] == 0.95
    assert block["resamples"] == 10_000
    assert block["method"] == "percentile"
    assert block["seed"] == DEFAULT_SEED
    assert block["generator"] == drawing_generator()
    assert block["draw_procedure_id"] == DRAW_PROCEDURE_ID
    assert set(block) == score_interval.BLOCK_KEYS
    assert set(block["by_language"]) == {"en", "fr", "de"}


def test_suite_resamples_unstratified_and_a_language_within_itself() -> None:
    items = _items(_LANGUAGES)
    values = [1.0 if ok else 0.0 for ok in _CORRECT]
    block = interval_block(items, values)
    assert block["suite"] == bootstrap_cell(values)
    fr = [v for item, v in zip(items, values, strict=True) if item["language"] == "fr"]
    assert block["by_language"]["fr"] == bootstrap_cell(fr)


def test_the_block_does_not_depend_on_the_order_rows_arrive_in() -> None:
    items = _items(_LANGUAGES)
    values = [1.0 if ok else 0.0 for ok in _CORRECT]
    pairs = list(zip(items, values, strict=True))
    random.Random(5).shuffle(pairs)
    shuffled_items, shuffled_values = zip(*pairs, strict=True)
    assert interval_block(list(shuffled_items), list(shuffled_values)) == (
        interval_block(items, values)
    )


def test_a_recorded_block_replays_bit_for_bit() -> None:
    items = _items(_LANGUAGES)
    values = [1.0 if ok else 0.0 for ok in _CORRECT]
    recorded = interval_block(items, values, seed=11, resamples=2_000)
    assert replay(recorded, items, values) == recorded


def test_a_changed_seed_changes_the_interval() -> None:
    values = [0.0, 0.2, 0.4, 0.5, 0.7, 0.9, 1.0, 0.3, 0.6, 0.8]
    assert bootstrap_cell(values, seed=1) != bootstrap_cell(values, seed=2)


def test_replay_refuses_a_method_or_procedure_it_does_not_implement() -> None:
    items = _items(["en", "fr"])
    block = interval_block(items, [0.0, 1.0], resamples=10)
    with pytest.raises(ScoreIntervalError, match="method 'bca'"):
        replay({**block, "method": "bca"}, items, [0.0, 1.0])
    with pytest.raises(ScoreIntervalError, match="draw procedure 'other/1'"):
        replay({**block, "draw_procedure_id": "other/1"}, items, [0.0, 1.0])


# --- named reasons ------------------------------------------------------------


@pytest.mark.parametrize("value", [1.0, 0.0, 0.5])
def test_a_constant_cell_publishes_the_zero_width_reason(value: float) -> None:
    cell = bootstrap_cell([value] * 20)
    assert cell == {
        "n": 20,
        "lower": None,
        "upper": None,
        "minimum_detectable_effect": None,
        "null_reason": NULL_ZERO_WIDTH,
    }


def test_an_empty_cell_publishes_its_reason_not_an_interval_around_zero() -> None:
    block = interval_block(_items(["en", "fr", "fr"]), [1.0, 0.0, 1.0])
    assert block["by_language"]["de"] == {
        "n": 0,
        "lower": None,
        "upper": None,
        "minimum_detectable_effect": None,
        "null_reason": NULL_NO_ITEMS,
    }
    # A one-item cell is constant, not empty.
    assert block["by_language"]["en"]["null_reason"] == NULL_ZERO_WIDTH


def test_each_reason_is_produced_by_its_own_state_only() -> None:
    assert bootstrap_cell([])["null_reason"] == NULL_NO_ITEMS
    assert bootstrap_cell([1.0])["null_reason"] == NULL_ZERO_WIDTH
    # One miss in twenty: defined, never zero_width.
    near_perfect = bootstrap_cell([1.0] * 19 + [0.0])
    assert near_perfect["null_reason"] is None
    assert near_perfect["lower"] is not None
    assert near_perfect["lower"] < near_perfect["upper"]  # type: ignore[operator]


def test_a_failed_generation_resamples_as_a_zero() -> None:
    failed = {"correct": False, "failure_reason": "empty", "predicted_label": None}
    assert item_value(failed) == 0.0
    assert item_value({"correct": True}) == 1.0
    assert item_value({"item_score": 0.0, "failure_reason": "empty"}) == 0.0
    assert item_value({"item_score": 0.62, "correct": None}) == 0.62
    with_failures = bootstrap_cell([1.0] * 15 + [0.0] * 5)
    successes_only = bootstrap_cell([1.0] * 15)
    assert with_failures["n"] == 20
    assert with_failures != successes_only


# --- the three batch invariants ----------------------------------------------


def test_a_well_formed_batch_holds_the_three_invariants() -> None:
    check_batch_invariants(_batch_rows())


def test_an_estimate_outside_its_interval_fails() -> None:
    rows = _batch_rows()
    block = rows[0]["score_interval"]
    moved = {**block, "suite": {**block["suite"], "upper": 0.7}}
    with pytest.raises(IntervalInvariantError, match="outside its interval"):
        check_batch_invariants(_batch_rows(block=moved))


def test_a_language_estimate_outside_its_interval_fails() -> None:
    block = _batch_rows()[0]["score_interval"]
    en = {**block["by_language"]["en"], "lower": 0.95, "upper": 0.99}
    moved = {**block, "by_language": {**block["by_language"], "en": en}}
    with pytest.raises(IntervalInvariantError, match="'item-000' en: point estimate"):
        check_batch_invariants(_batch_rows(block=moved))


def test_a_resumed_batch_whose_interval_covers_other_items_fails() -> None:
    # The score and breakdown span all 20 items; the interval was computed
    # over the 12 items the resume itself ran.
    items = _items(_LANGUAGES)
    values = [1.0 if ok else 0.0 for ok in _CORRECT]
    resumed_only = interval_block(items[8:], values[8:])
    with pytest.raises(IntervalInvariantError, match="n=12 .* n=20"):
        check_batch_invariants(_batch_rows(block=resumed_only))


def test_a_language_n_that_differs_from_the_breakdown_fails() -> None:
    block = _batch_rows()[0]["score_interval"]
    fr = {**block["by_language"]["fr"], "n": 5}
    moved = {**block, "by_language": {**block["by_language"], "fr": fr}}
    with pytest.raises(IntervalInvariantError, match="fr interval .* n=5"):
        check_batch_invariants(_batch_rows(block=moved))


def test_two_rows_of_one_batch_with_different_blocks_fail() -> None:
    rows = _batch_rows()
    rows[5] = {**rows[5], "score_interval": {**rows[5]["score_interval"], "seed": 1}}
    with pytest.raises(IntervalInvariantError, match="different interval blocks"):
        check_batch_invariants(rows)


def test_rows_written_partial_before_a_resume_are_not_held_to_the_block() -> None:
    rows = _batch_rows()
    for row in rows[:8]:
        row.update(suite_accuracy=None, language_breakdown=None, score_interval=None)
    check_batch_invariants(rows)


def test_a_block_beside_no_published_score_fails() -> None:
    rows = _batch_rows()
    rows[0] = {**rows[0], "suite_accuracy": None, "language_breakdown": None}
    with pytest.raises(IntervalInvariantError, match="beside no published"):
        check_batch_invariants(rows)


def test_a_graded_batch_is_checked_against_its_score_breakdown() -> None:
    items = _items(["en", "en", "fr", "de"])
    values = [0.4, 0.6, 0.5, 0.8]
    block = interval_block(items, values, resamples=500)
    breakdown = {
        "en": {"score": 0.5, "n": 2, "indicative": True},
        "fr": {"score": 0.5, "n": 1, "indicative": True},
        "de": {"score": 0.8, "n": 1, "indicative": True},
    }
    row = {
        "item_id": "item-000",
        "suite_accuracy": None,
        "suite_score": sum(values) / 4,
        "score_breakdown": breakdown,
        "score_interval": block,
    }
    check_batch_invariants([row])
    with pytest.raises(
        IntervalInvariantError, match="n=4 but the published breakdown holds n=5"
    ):
        check_batch_invariants(
            [
                {
                    **row,
                    "score_breakdown": {**breakdown, "de": {**breakdown["de"], "n": 2}},
                }
            ]
        )


# --- the runtime stays on the standard library --------------------------------


def test_src_imports_no_scipy() -> None:
    importers = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name == "scipy" or name.startswith("scipy.") for name in names):
                importers.append(path.name)
    assert importers == []
