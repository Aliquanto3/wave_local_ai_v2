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
"""

from __future__ import annotations

import re
from typing import Protocol, TypedDict

from wave_local_ai_v2 import judge_protocol, scoring
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
