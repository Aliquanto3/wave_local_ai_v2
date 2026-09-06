"""chrF vectors, hand-computed here and checkable without running anything.

Every expected number below is worked out from the algorithm in a comment,
not read back from the implementation. A comment that disagrees with its
assertion is the bug report.
"""

import pytest

from wave_local_ai_v2.chrf import (
    BETA,
    CHAR_ORDER,
    INCLUDE_WHITESPACE,
    METRIC_ID,
    METRIC_PARAMS,
    METRIC_VERSION,
    chrf,
)


def test_identical_strings_score_one() -> None:
    # "abc" against itself.
    #   order 1: hyp {a,b,c}=3, ref 3, match 3 -> p=1, r=1
    #   order 2: hyp {ab,bc}=2, ref 2, match 2 -> p=1, r=1
    #   order 3: hyp {abc}=1,   ref 1, match 1 -> p=1, r=1
    #   orders 4-6: neither side has an n-gram, so they do not count
    # avg p = avg r = 1 -> F = 5*1*1 / (4*1 + 1) = 1
    assert chrf("abc", "abc") == 1.0


def test_one_substituted_character_collapses_to_the_average_precision() -> None:
    # ref "abcd", hyp "abce". Both are four characters, so precision and
    # recall are equal at every order and the F-score collapses to that
    # common average whatever beta is.
    #   order 1: {a,b,c,e} vs {a,b,c,d}, match 3 of 4 -> 3/4
    #   order 2: {ab,bc,ce} vs {ab,bc,cd}, match 2 of 3 -> 2/3
    #   order 3: {abc,bce} vs {abc,bcd}, match 1 of 2 -> 1/2
    #   order 4: {abce} vs {abcd}, match 0 of 1 -> 0
    #   orders 5-6: no n-grams on either side, not counted
    # avg = (3/4 + 2/3 + 1/2 + 0) / 4 = 23/48 = 0.47916666...
    assert chrf("abcd", "abce") == pytest.approx(23 / 48)


def test_beta_two_weights_recall_four_times_exactly() -> None:
    # ref "a", hyp "abab". Only order 1 has n-grams on both sides, so it is
    # the only effective order.
    #   order 1: hyp {a:2,b:2} = 4 n-grams, ref {a:1} = 1, match 1
    #            -> p = 1/4, r = 1/1 = 1
    #   orders 2-6: the one-character reference has no n-grams -> skipped
    # F = (1+4) * (1/4) * 1 / (4 * (1/4) + 1) = (5/4) / 2 = 5/8
    # Every term is a dyadic fraction, so this one is exact in binary
    # floating point and is asserted with no tolerance at all.
    # The recall weighting is what lifts it: with beta = 1 the same pair
    # would score 2 * (1/4) / (1/4 + 1) = 0.4.
    assert chrf("a", "abab") == 0.625
    assert chrf("a", "abab", beta=1) == 0.4


def test_recall_weighting_on_a_multi_order_pair() -> None:
    # ref "ab", hyp "abab".
    #   order 1: hyp {a:2,b:2} = 4, ref {a:1,b:1} = 2, match 2
    #            -> p = 2/4 = 1/2, r = 2/2 = 1
    #   order 2: hyp {ab:2,ba:1} = 3, ref {ab:1} = 1, match 1
    #            -> p = 1/3, r = 1/1 = 1
    #   orders 3-6: the two-character reference has no n-grams -> skipped
    # avg p = (1/2 + 1/3) / 2 = 5/12, avg r = 1
    # F = 5 * (5/12) / (4 * (5/12) + 1) = (25/12) / (32/12) = 25/32 = 0.78125
    # Asserted to within one ULP rather than exactly: 1/3 is not
    # representable in binary, and the summation order here is sacreBLEU's,
    # which is the property worth keeping.
    assert chrf("ab", "abab") == pytest.approx(25 / 32, abs=1e-15)


def test_chrf_is_not_symmetric_under_beta_two() -> None:
    # Swapping the arguments swaps precision and recall, and beta = 2
    # weights them differently, so the two scores must differ. Pinned so a
    # later "simplification" cannot quietly reverse the parameters.
    #   chrf("ab", "abab") = 25/32 = 0.78125   (recall 1, precision 5/12)
    #   chrf("abab", "ab") = 5 * (5/12) / (4 + 5/12) = 25/53 = 0.4716...
    assert chrf("ab", "abab") != chrf("abab", "ab")
    assert chrf("abab", "ab") == pytest.approx(25 / 53)


def test_whitespace_differences_do_not_change_a_score() -> None:
    # sacreBLEU's chrF default strips whitespace before cutting n-grams.
    assert chrf("a b c", "abc") == chrf("abc", "abc")
    assert chrf("abc", "a\tb\nc") == 1.0
    assert chrf("le chat", "lechat") == 1.0


@pytest.mark.parametrize(
    ("reference", "hypothesis"),
    [
        ("abc", ""),
        ("", "abc"),
        ("", ""),
        ("   ", "abc"),
        ("abc", " \t\n "),
        ("   ", "   "),
    ],
)
def test_degenerate_pairs_score_zero_and_raise_nothing(
    reference: str, hypothesis: str
) -> None:
    # Nothing to compare on one side means no effective order, which returns
    # 0.0 rather than dividing by zero.
    assert chrf(reference, hypothesis) == 0.0


def test_a_pair_shorter_than_the_char_order_uses_only_the_orders_it_has() -> None:
    # Two characters cannot reach order 3, and the missing orders must not
    # drag the score down: an identical two-character pair is a perfect one.
    assert chrf("ab", "ab") == 1.0
    # And a two-character pair sharing one character is not zero either.
    #   order 1: {a,c} vs {a,b}, match 1 of 2 -> p = r = 1/2
    #   order 2: {ac} vs {ab},   match 0 of 1 -> p = r = 0
    # avg p = avg r = 1/4 -> F = 5 * (1/16) / (4/4 + 1/4) = 0.3125 / 1.25
    assert chrf("ab", "ac") == 0.25


def test_n_grams_are_cut_over_characters_not_bytes() -> None:
    # "résumé" and "resume" differ by two accents. Cut over characters the
    # pair still shares most of its unigrams; cut over UTF-8 bytes the
    # accented characters would each be two bytes and the arithmetic below
    # would not hold.
    score = chrf("résumé", "resume")
    assert 0.0 < score < 1.0
    # One accent alone is enough to move the score off 1.0.
    assert chrf("resume", "résumé") < 1.0
    assert chrf("résumé", "résumé") == 1.0


@pytest.mark.parametrize(
    ("reference", "hypothesis"),
    [
        ("Bonjour", "Bonjour"),
        ("Bonjour", "Guten Tag"),
        ("Die Lieferung kommt morgen.", "The delivery arrives tomorrow."),
        ("a", "aaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
        ("!!!", "???"),
        ("123", "1 2 3"),
    ],
)
def test_every_score_is_a_float_inside_the_unit_interval(
    reference: str, hypothesis: str
) -> None:
    score = chrf(reference, hypothesis)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_metric_params_are_derived_from_the_module_constants() -> None:
    # The published block cannot drift from the parameters actually used.
    assert METRIC_PARAMS == {
        "char_order": CHAR_ORDER,
        "beta": BETA,
        "whitespace": INCLUDE_WHITESPACE,
        "scale": "0..1",
    }
    assert METRIC_ID == "chrf"
    assert METRIC_VERSION == "1"
    # Frozen: a caller embedding it in a row copies it instead of mutating it.
    with pytest.raises(TypeError):
        METRIC_PARAMS["beta"] = 3  # type: ignore[index]


def test_sacrebleu_default_parameterisation_is_what_is_declared() -> None:
    assert CHAR_ORDER == 6
    assert BETA == 2
    assert INCLUDE_WHITESPACE is False
