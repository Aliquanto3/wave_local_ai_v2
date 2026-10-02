"""Unit tests for `retry.py`: fake clock/sleep/jitter, no real time.sleep."""

from __future__ import annotations

import pytest

from wave_local_ai_v2.retry import (
    Pacer,
    RetryBudget,
    RetryBudgetExhausted,
    call_with_retry,
    derived_retry_budget,
)
from wave_local_ai_v2.settings import (
    DEFAULT_CLOUD_RETRY_MIN_RETRIES,
    DEFAULT_CLOUD_RETRY_RETRIES_PER_ITEM,
)


class _FakeClock:
    """A monotonic clock advanced only by explicit `.advance()` calls."""

    def __init__(self) -> None:
        self._now = 0.0

    def advance(self, seconds: float) -> None:
        self._now += seconds

    def __call__(self) -> float:
        return self._now


class _RecordingSleep:
    """Records every sleep duration instead of blocking."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def test_pacer_first_call_never_sleeps() -> None:
    clock = _FakeClock()
    sleep = _RecordingSleep()
    pacer = Pacer(5.0, clock=clock, sleep=sleep)

    pacer.wait()

    assert sleep.calls == []


def test_pacer_sleeps_only_the_remainder_of_min_interval() -> None:
    clock = _FakeClock()
    sleep = _RecordingSleep()
    pacer = Pacer(5.0, clock=clock, sleep=sleep)

    pacer.wait()  # no sleep, last_call_at = 0
    clock.advance(2.0)  # 2s elapsed since last call
    pacer.wait()  # sleeps the remaining 3s; last_call_at advances to 5 (not 2)
    clock.advance(8.0)  # now = 10, a full interval past last_call_at=5
    pacer.wait()  # no sleep needed

    assert sleep.calls == [3.0]


def test_pacer_never_banks_an_overrun_as_a_burst_of_unpaced_calls() -> None:
    # The retry case: one item outlasts the interval (a backoff sleep, a
    # retryDelay hint), so its own wait needs no sleep. The next calls must
    # still be spaced a full interval apart -- banking the overrun would fire
    # them back to back at the provider that just rate-limited us.
    clock = _FakeClock()
    sleep = _RecordingSleep()
    pacer = Pacer(5.0, clock=clock, sleep=sleep)

    pacer.wait()  # no sleep, last_call_at = 0
    clock.advance(30.0)  # the call itself took 30s: six intervals of overrun
    pacer.wait()  # nothing to wait for
    pacer.wait()  # immediately after: must sleep the full interval

    assert sleep.calls == [5.0]


def test_call_with_retry_succeeds_after_one_retryable_failure() -> None:
    sleep = _RecordingSleep()
    attempts_made = {"n": 0}

    def flaky() -> str:
        attempts_made["n"] += 1
        if attempts_made["n"] == 1:
            raise ValueError("transient")
        return "ok"

    result, attempt = call_with_retry(
        flaky,
        is_retryable=lambda exc: True,
        retry_hint_s=lambda exc: None,
        budget=RetryBudget(max_retries=3),
        base_delay_s=1.0,
        sleep=sleep,
        jitter=lambda: 0.0,
    )

    assert (result, attempt) == ("ok", 1)
    assert len(sleep.calls) == 1


def test_retry_hint_is_honoured_verbatim_not_blended_with_backoff() -> None:
    sleep = _RecordingSleep()
    attempts_made = {"n": 0}

    def flaky() -> str:
        attempts_made["n"] += 1
        if attempts_made["n"] == 1:
            raise ValueError("transient")
        return "ok"

    call_with_retry(
        flaky,
        is_retryable=lambda exc: True,
        retry_hint_s=lambda exc: 13.0,
        budget=RetryBudget(max_retries=3),
        base_delay_s=1.0,
        sleep=sleep,
        jitter=lambda: 999.0,  # would be obviously blended in if used
    )

    assert sleep.calls == [13.0]


def test_non_retryable_exception_reraises_with_no_sleep_or_budget_use() -> None:
    sleep = _RecordingSleep()
    budget = RetryBudget(max_retries=3)

    def always_fails() -> str:
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        call_with_retry(
            always_fails,
            is_retryable=lambda exc: False,
            retry_hint_s=lambda exc: None,
            budget=budget,
            base_delay_s=1.0,
            sleep=sleep,
        )

    assert sleep.calls == []
    assert budget.take() is True  # untouched: still has all 3 retries


def test_retry_budget_exhaustion_raises_with_cause_and_attempt_count() -> None:
    sleep = _RecordingSleep()
    original = ValueError("still failing")

    def always_fails() -> str:
        raise original

    with pytest.raises(RetryBudgetExhausted, match="2") as exc_info:
        call_with_retry(
            always_fails,
            is_retryable=lambda exc: True,
            retry_hint_s=lambda exc: None,
            budget=RetryBudget(max_retries=2),
            base_delay_s=1.0,
            sleep=sleep,
            jitter=lambda: 0.0,
        )

    assert exc_info.value.__cause__ is original


def test_exponential_backoff_with_no_hint_grows_and_caps() -> None:
    sleep = _RecordingSleep()

    def always_fails() -> str:
        raise ValueError("transient")

    with pytest.raises(RetryBudgetExhausted):
        call_with_retry(
            always_fails,
            is_retryable=lambda exc: True,
            retry_hint_s=lambda exc: None,
            budget=RetryBudget(max_retries=3),
            base_delay_s=1.0,
            max_delay_s=3.0,
            sleep=sleep,
            jitter=lambda: 0.0,
        )

    # base_delay_s * 2**attempt for attempts 0, 1, 2, capped at max_delay_s=3.0
    assert sleep.calls == [1.0, 2.0, 3.0]


def test_retry_budget_take_decrements_and_reports_exhaustion() -> None:
    budget = RetryBudget(max_retries=1)

    assert budget.take() is True
    assert budget.take() is False
    assert budget.take() is False


def _default_budget(item_count: int) -> int:
    return derived_retry_budget(
        item_count,
        per_item=DEFAULT_CLOUD_RETRY_RETRIES_PER_ITEM,
        minimum=DEFAULT_CLOUD_RETRY_MIN_RETRIES,
    )


def test_the_derived_budget_grows_with_the_item_count() -> None:
    # A development-size batch keeps the four retries it was validated with;
    # a publication-size one is not held to that total.
    assert _default_budget(20) == 4
    assert _default_budget(100) == 20
    assert _default_budget(300) == 60
    assert _default_budget(100) > _default_budget(20)


def test_the_derived_budget_never_falls_below_its_floor() -> None:
    assert _default_budget(0) == DEFAULT_CLOUD_RETRY_MIN_RETRIES
    assert _default_budget(1) == DEFAULT_CLOUD_RETRY_MIN_RETRIES
    # A fractional product rounds up: a budget is whole retries.
    assert derived_retry_budget(21, per_item=0.2, minimum=1) == 5


def test_the_derived_budget_refuses_a_negative_item_count() -> None:
    with pytest.raises(ValueError, match="negative"):
        derived_retry_budget(-1, per_item=0.2, minimum=4)


def test_a_retry_budget_reports_the_total_it_started_with() -> None:
    budget = RetryBudget(_default_budget(100))
    budget.take()

    assert budget.total == 20


@pytest.mark.parametrize("item_count", [20, 100, 300, 10_000])
def test_a_refusal_is_never_retried_whatever_the_budget(item_count: int) -> None:
    # A model absent from the catalog, a family collision and an unparseable
    # judge reply are deterministic: retrying one turns a named error into a
    # timeout, however much budget a large batch was given.
    budget = RetryBudget(_default_budget(item_count))
    sleep = _RecordingSleep()
    calls = {"n": 0}

    def refused() -> None:
        calls["n"] += 1
        raise LookupError("model id absent from the live catalog")

    with pytest.raises(LookupError):
        call_with_retry(
            refused,
            is_retryable=lambda exc: False,
            retry_hint_s=lambda exc: None,
            budget=budget,
            base_delay_s=1.0,
            sleep=sleep,
            jitter=lambda: 0.0,
        )

    assert calls["n"] == 1
    assert sleep.calls == []
    assert budget.take() is True
