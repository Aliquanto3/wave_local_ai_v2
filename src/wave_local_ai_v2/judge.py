"""One judge call, through a backend this module knows nothing about.

No provider is named here: a backend is injected as `JudgeBackend`, owns the
pacing/retry layer and its own error types, and a transport failure propagates
out untouched -- this module catches nothing but its own parse. The provider
bindings live in `judge_backends.py`, the only judge-path module that imports
a client.

A reply that cannot be parsed is a missing judgement, never a zero. The raw
text is recorded whatever the parse does, because a judge reply is not assumed
reproducible: `aidd_docs/results/README.md` records Mistral at temperature 0
with a pinned `random_seed` failing to reproduce one item across two runs, so
the text the judge actually returned is the row's evidence, not a score that
could be re-derived on demand.

Independence is enforced on model family (`roster.family_of`): a judge of the
subject's own family is refused by name, never skipped and never quietly
substituted.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

from wave_local_ai_v2 import agreement, cost, judge_protocol, scoring
from wave_local_ai_v2.judge_protocol import Rubric

# Any run of digits, sign included, so "-1" and "7" both reach the scale check
# as out-of-scale rather than as unparseable prose.
_INTEGER_RE = re.compile(r"-?\d+")

FAILURE_REASON_JUDGE_EMPTY = "judge_response_empty"
FAILURE_REASON_JUDGE_UNPARSEABLE = "judge_response_unparseable"
FAILURE_REASON_JUDGE_OUT_OF_SCALE = "judge_score_out_of_scale"

JUDGE_FAILURE_REASONS = (
    FAILURE_REASON_JUDGE_EMPTY,
    FAILURE_REASON_JUDGE_UNPARSEABLE,
    FAILURE_REASON_JUDGE_OUT_OF_SCALE,
)

# Why a row carries one judge instead of two. The caller states which applies:
# `select_judges` refuses a collision rather than filtering it out, so by the
# time `judge_item` sees one judge it cannot tell whether the subject's own
# family was left out or whether only one judge was configured, and guessing
# would publish a reason the row cannot back.
SINGLE_JUDGE_REASON_CLOUD_SUBJECT = "cloud_subject_other_family_only"
SINGLE_JUDGE_REASON_ONE_JUDGE_AVAILABLE = "only_one_independent_judge_available"

SINGLE_JUDGE_REASONS = (
    SINGLE_JUDGE_REASON_CLOUD_SUBJECT,
    SINGLE_JUDGE_REASON_ONE_JUDGE_AVAILABLE,
)

# One generation per judged item, whatever the judge count. Recorded on the
# egress block so a reader can add up what left the machine.
_GENERATIONS_PER_ITEM = 1


class JudgeResponse(TypedDict):
    """What a backend returns: the reply plus who produced it, at what cost.

    Names no provider-specific type. `family` is what the independence rule is
    enforced on (`roster.family_of`), carried here so a judged row can state
    it without re-resolving the model id.
    """

    content: str
    model_id: str
    provider: str
    family: str
    tokens_in: int | None
    tokens_out: int | None
    retries: int


class JudgeBackend(Protocol):
    """One judge call: a prompt in, a `JudgeResponse` out.

    The backend owns the pacing/retry layer and the provider error types. A
    transport failure -- a non-200, an exhausted retry budget -- propagates
    through `run_judge_call` untouched; this module handles parse failures and
    nothing else, which is what keeps it free of any provider import.
    """

    def __call__(self, prompt: str) -> JudgeResponse: ...


class JudgeCallRecord(TypedDict):
    """One judge's call as a judged row publishes it."""

    model_id: str
    provider: str
    family: str
    score: int | str | None
    raw_text: str
    failure_reason: str | None
    tokens_in: int | None
    tokens_out: int | None
    retries: int


# The key set `row_contract` validates a row's `judges` entries against,
# derived from the TypedDict rather than restated, so the two cannot drift.
JUDGE_CALL_RECORD_FIELDS: frozenset[str] = frozenset(JudgeCallRecord.__required_keys__)


def parse_judge_score(raw: str, rubric: Rubric) -> tuple[int | str | None, str | None]:
    """Parse `raw` into `rubric`'s scale, or name why it could not be.

    Returns `(score, failure_reason)` with exactly one of them non-null. A
    failed parse yields `None`, never `0`: on a 1-5 rubric a `0` is outside
    the scale entirely, and on any rubric it would read as a judgement that
    was never made.

    Branches on which of `scale`/`categories` is populated rather than on
    `kind`; `Rubric.__post_init__` binds the two, so the check that narrows
    the type is the same check that identifies the kind.
    """
    if raw.strip() == "":
        return None, FAILURE_REASON_JUDGE_EMPTY

    if rubric.scale is not None:
        candidates = _INTEGER_RE.findall(raw)
        # Exactly one, not the first: "4/5" and "between 2 and 3" are a judge
        # that did not answer in the form the rubric asked for, and picking
        # either number would publish a guess as a judgement.
        if len(candidates) != 1:
            return None, FAILURE_REASON_JUDGE_UNPARSEABLE
        value = int(candidates[0])
        if value not in rubric.scale:
            return None, FAILURE_REASON_JUDGE_OUT_OF_SCALE
        return value, None

    if rubric.categories is not None:
        # `scoring.normalize_label`, not a second normalizer: the rule for
        # extracting a closed-set label from free-text model output is already
        # declared once, and a judge reply is the same problem.
        label = scoring.normalize_label(raw, rubric.categories)
        if label is None:
            return None, FAILURE_REASON_JUDGE_UNPARSEABLE
        return label, None

    raise ValueError(
        f"rubric {rubric.rubric_id!r} carries neither a scale nor categories"
    )


def run_judge_call(
    backend: JudgeBackend,
    rendered: judge_protocol.RenderedJudgePrompt,
    rubric: Rubric,
) -> JudgeCallRecord:
    """Call `backend` with the rendered prompt and record what came back.

    `raw_text` is recorded whatever happens to the parse -- it is the row's
    evidence, and a row that names a `failure_reason` without the text it
    failed on cannot be re-judged by a reader. A failed parse leaves `score`
    at `None`; it is never `0`.

    Catches nothing: a provider's transport error, or an exhausted retry
    budget, propagates to the caller that owns the "skip that provider" rule.
    """
    response = backend(rendered["prompt"])
    score, failure_reason = parse_judge_score(response["content"], rubric)
    return JudgeCallRecord(
        model_id=response["model_id"],
        provider=response["provider"],
        family=response["family"],
        score=score,
        raw_text=response["content"],
        failure_reason=failure_reason,
        tokens_in=response["tokens_in"],
        tokens_out=response["tokens_out"],
        retries=response["retries"],
    )


@dataclass(frozen=True)
class Judge:
    """One candidate judge: who it is, which family it belongs to, how to call it."""

    model_id: str
    provider: str
    family: str
    backend: JudgeBackend


class JudgeFamilyCollisionError(ValueError):
    """Raised when a candidate judge belongs to the subject's own model family."""


def select_judges(subject_family: str, judges: Sequence[Judge]) -> list[Judge]:
    """Return `judges` unchanged, or refuse the one that shares the subject's family.

    A refusal, not a filter: the colliding judge is never quietly dropped and
    another is never substituted for it, because either would publish a
    two-judge row that silently became something else. Raises before any
    backend is invoked, so a refused call costs nothing.
    """
    for candidate in judges:
        if candidate.family == subject_family:
            raise JudgeFamilyCollisionError(
                f"judge {candidate.model_id!r} is of family "
                f"{candidate.family!r}, the subject's own family: a judge "
                "never scores output from its own family. This is a refusal, "
                "not a skip -- name a judge of another family instead."
            )
    return list(judges)


def judge_item(
    *,
    subject_family: str,
    subject_provider: str,
    subject_output: str,
    item_prompt: str,
    item_language: judge_protocol.JudgeLanguage,
    rubric: Rubric,
    judges: Sequence[Judge],
    threshold: agreement.ContestedThreshold,
    single_judge_reason: str | None = None,
) -> dict[str, Any]:
    """Judge one subject output and return the row's whole judge block.

    The returned key set is exactly `row_contract.JUDGED_FIELDS`. Two surviving
    judges produce an agreement figure and `single_judge=False`; one produces
    the flag and the `single_judge_reason` the caller states, with
    `agreement=None`. It is the number of judges left after the independence
    rule that decides this, never a `provider == "local"` test -- that keeps
    the rule true for a roster this increment has not seen.

    `single_judge_reason` is the caller's to supply and is refused when a
    single-judge call omits it, or when a two-judge call carries it: only the
    caller knows whether the subject's own family was excluded or whether one
    judge was all that was configured, and a defaulted reason would put a
    claim on the row that nothing backs.

    Both judges' own scores stay on the block whatever the suite-level
    statistic says, so another agreement statistic can be recomputed from the
    published rows alone.
    """
    selected = select_judges(subject_family, judges)
    if not selected:
        raise ValueError(
            f"no judge is available for a subject of family {subject_family!r} "
            f"from provider {subject_provider!r}: a judged row carries at "
            "least one judge call"
        )
    if len(selected) > 2:
        raise ValueError(
            f"{len(selected)} judges given for one item: the agreement "
            "statistic is defined over exactly two, and publishing one over a "
            "subset would name a figure the row cannot back"
        )

    # Checked before any backend runs, so a row that could not have stated its
    # own independence never costs a judge call.
    if len(selected) == 1 and single_judge_reason is None:
        raise ValueError(
            "a single-judge row must state why only one judge scored it: pass "
            f"single_judge_reason (one of {', '.join(SINGLE_JUDGE_REASONS)})"
        )
    if len(selected) == 2 and single_judge_reason is not None:
        raise ValueError(
            f"single_judge_reason={single_judge_reason!r} was given for two "
            "judges: a two-judge row carries an agreement figure, not a "
            "single-judge flag"
        )

    rendered = judge_protocol.render_judge_prompt(
        rubric=rubric,
        language=item_language,
        item_prompt=item_prompt,
        subject_output=subject_output,
    )
    records = [run_judge_call(one.backend, rendered, rubric) for one in selected]
    scores = [record["score"] for record in records]

    if len(records) == 2:
        single_judge = False
        computed = agreement.agreement_for_rubric(rubric, [(scores[0], scores[1])])
        item_agreement: agreement.Agreement | None = computed
        # The row names the statistic it published, read off the Agreement
        # rather than re-derived from the rubric kind at this call site.
        agreement_statistic: str | None = computed["statistic"]
        contested, contested_reason = agreement.is_contested(
            rubric.kind, scores[0], scores[1], threshold
        )
    else:
        single_judge = True
        item_agreement = None
        agreement_statistic = None
        # One score is not a disagreement: there is nothing for the second
        # judge to have contested.
        contested, contested_reason = False, None

    headline = agreement.headline_score([scores], [contested])

    return {
        "judge_prompt_id": rendered["template_id"],
        "judge_prompt_template_hash": rendered["template_hash"],
        "judge_prompt_language": rendered["language"],
        "rubric_id": rendered["rubric_id"],
        "rubric_version": rendered["rubric_version"],
        "rubric_kind": rendered["rubric_kind"],
        "judges": records,
        "single_judge": single_judge,
        "single_judge_reason": single_judge_reason,
        "agreement": item_agreement,
        "agreement_statistic": agreement_statistic,
        "contested": contested,
        "contested_reason": contested_reason,
        # The threshold's values, not a reference to it: a row must state the
        # rule it was judged under without resolving today's configuration.
        "contested_threshold": {"max_ordinal_delta": threshold.max_ordinal_delta},
        "judged_headline_score": headline["score"],
        "judged_headline_excluded_n": headline["n_excluded"],
        # Recorded from the calls that were made, not asserted as constants.
        "judge_egress": {
            "item_left_machine": True,
            "subject_output_left_machine": True,
            "providers": sorted({record["provider"] for record in records}),
            "generation_count": _GENERATIONS_PER_ITEM,
            "judge_call_count": len(records),
        },
        "judge_cost": cost.judge_cost_fields(records),
    }
