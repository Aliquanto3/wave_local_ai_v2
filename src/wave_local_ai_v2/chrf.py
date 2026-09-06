"""chrF: the character n-gram F-score, reproduced from sacreBLEU's defaults.

chrF (Popović 2015, "chrF: character n-gram F-score for automatic MT
evaluation", WMT15) scores a hypothesis translation against a reference by
overlapping their character n-grams: precision and recall are averaged over
the n-gram orders that exist on both sides, then combined once into a single
F-score that `beta` tilts toward recall. It is fully deterministic and
offline -- the same pair of strings always yields the same number, on any
machine, with no model and no network involved.

This module reproduces sacreBLEU's default parameterisation, so a published
score can be checked against the reference implementation rather than against
a private variant. The two files that are the spec here:

- https://raw.githubusercontent.com/mjpost/sacrebleu/master/sacrebleu/metrics/chrf.py
- https://raw.githubusercontent.com/mjpost/sacrebleu/master/sacrebleu/metrics/helpers.py

Why in-repo instead of `pip install sacrebleu`: the algorithm below is sixty
lines of `Counter` arithmetic with no I/O and no randomness, while the
package pulls `numpy`, `regex`, `portalocker`, `tabulate`, `colorama` and
`lxml` into a project whose CI audits every transitive dependency
(`scripts/audit_dependencies.py`) and whose reproduction story asks a client
engineer to install the tree. Six packages for sixty lines fails that trade.
sacreBLEU's source stays the specification; this is an implementation of it.

Scale: scores are returned on `0..1`, not sacreBLEU's `0..100`, because the
quality store already publishes `suite_accuracy` on `0..1` and two score
scales in one file is a reading trap. To compare a row against a sacreBLEU
printout, multiply by 100.

What the number does not mean: chrF against a *single* reference penalises a
valid alternative translation that happens to share fewer character n-grams
with the one reference on file. A score is defensible as a comparison between
models measured against identical references; it is not an absolute
translation-quality figure, and no claim of that kind should be built on it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType

# sacreBLEU's chrF defaults, named rather than buried in a signature default
# so `METRIC_PARAMS` below can be derived from them: a parameter cannot move
# without the block published on every row moving with it.
CHAR_ORDER = 6
BETA = 2
# sacreBLEU's `whitespace` flag, spelled from this module's point of view.
# False means whitespace is stripped before n-grams are cut, so the same
# sentence spaced two ways scores identically.
INCLUDE_WHITESPACE = False

METRIC_ID = "chrf"
METRIC_VERSION = "1"

# The parameter block a row publishes beside its score, so a reader holding
# the row's `reference_output` and `subject_output` knows exactly which chrF
# was computed. Keys match sacreBLEU's own parameter names where they exist
# (`char_order`, `beta`, `whitespace`) so the block reads as instructions for
# reproducing the number. Frozen because it is embedded in every row: a
# caller writing a row copies it (`dict(METRIC_PARAMS)`) rather than sharing
# and risking mutating this one object.
METRIC_PARAMS: Mapping[str, object] = MappingProxyType(
    {
        "char_order": CHAR_ORDER,
        "beta": BETA,
        "whitespace": INCLUDE_WHITESPACE,
        "scale": "0..1",
    }
)


def _char_ngrams(text: str, order: int) -> list[Counter[str]]:
    """Character n-gram counts per order, index 0 holding order 1.

    Whitespace is collapsed with `"".join(text.split())` when
    `INCLUDE_WHITESPACE` is false, matching sacreBLEU's
    `extract_all_char_ngrams(..., include_whitespace=False)`. Nothing is
    lowercased: sacreBLEU does not lowercase by default, and case carries
    meaning in a translation (German capitalises every noun).
    """
    if not INCLUDE_WHITESPACE:
        text = "".join(text.split())
    return [
        Counter(text[i : i + n] for i in range(len(text) - n + 1))
        for n in range(1, order + 1)
    ]


def chrf(
    reference: str,
    hypothesis: str,
    *,
    char_order: int = CHAR_ORDER,
    beta: int = BETA,
) -> float:
    """Score `hypothesis` against `reference`, on `0..1`.

    Per order, the match count is the multiset intersection of the two
    character n-gram counters. An order counts toward the effective order
    only when both sides have at least one n-gram at it -- so a short pair is
    not punished for the orders neither string is long enough to reach.
    Precision and recall are averaged over the effective orders and combined
    once, which is sacreBLEU's behaviour with `eps_smoothing` off (its
    default), not a per-order F-score averaged afterwards.

    Not symmetric: `beta = 2` weights recall four times as heavily as
    precision, so swapping the arguments changes the score. `reference`
    first, matching sacreBLEU's `sentence_chrf(hypothesis, references)`
    reversed for the two-string case that reads more naturally here.

    Returns `0.0` rather than raising when there is nothing to compare: an
    empty string on either side, a whitespace-only one, or a pair whose
    precision and recall are both zero.
    """
    ref_ngrams = _char_ngrams(reference, char_order)
    hyp_ngrams = _char_ngrams(hypothesis, char_order)

    effective_order = 0
    precision_sum = 0.0
    recall_sum = 0.0
    for ref_counts, hyp_counts in zip(ref_ngrams, hyp_ngrams, strict=True):
        n_ref = sum(ref_counts.values())
        n_hyp = sum(hyp_counts.values())
        if n_ref == 0 or n_hyp == 0:
            continue
        n_match = sum((hyp_counts & ref_counts).values())
        effective_order += 1
        precision_sum += n_match / n_hyp
        recall_sum += n_match / n_ref

    if effective_order == 0:
        return 0.0

    precision = precision_sum / effective_order
    recall = recall_sum / effective_order
    if precision + recall == 0.0:
        return 0.0

    factor = beta**2
    return (1 + factor) * precision * recall / (factor * precision + recall)
