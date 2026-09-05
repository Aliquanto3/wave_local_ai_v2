"""A dependency-free pacing/retry layer.

This module knows nothing about status codes, providers, or the CLI: every
provider-specific decision (`is_retryable`, `retry_hint_s`) is supplied by the
caller. It is pure functions plus two small stateful helpers, testable with a
fake clock/sleep/jitter -- no real `time.sleep` in its own tests.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable


class Pacer:
    """Sleeps just enough that consecutive `.wait()` calls are spaced `min_interval_s` apart.

    The first call never sleeps -- there is no previous call to space against.
    After a sleep, `.wait()` advances its own notion of "last call time" by
    exactly `min_interval_s` rather than by the wall clock read after sleeping,
    so sleep overshoot never compounds drift across a batch. When no sleep was
    needed -- the caller's own work already outlasted the interval -- it resets
    to the clock instead: carrying the overrun forward as a credit would let
    the next few calls fire back to back, which is precisely the burst the
    pacing exists to prevent (a retry's backoff is the common way an item
    outlasts the interval, so the credit would be spent on the provider that
    just rate-limited us).
    """

    def __init__(
        self,
        min_interval_s: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval_s = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._last_call_at: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last_call_at is None:
            self._last_call_at = now
            return
        elapsed = now - self._last_call_at
        remaining = self._min_interval_s - elapsed
        if remaining > 0:
            self._sleep(remaining)
        # max, not a bare advance: with a sleep, `now` is behind
        # `last + interval` and the advance wins (no drift from sleep
        # overshoot); without one, `now` is ahead and the clock wins (no
        # accumulated credit to spend as an unpaced burst).
        self._last_call_at = max(now, self._last_call_at + self._min_interval_s)


class RetryBudget:
    """A run-scoped count of retries left, shared across every item of one batch.

    One instance per provider batch, not one per call: a budget shared across
    every item is what makes "N retries total for this batch" the enforced
    behavior, rather than N retries per item.
    """

    def __init__(self, max_retries: int) -> None:
        self._remaining = max_retries

    def take(self) -> bool:
        """Decrement and return True while retries remain; False once exhausted."""
        if self._remaining <= 0:
            return False
        self._remaining -= 1
        return True


class RetryBudgetExhausted(RuntimeError):
    """Raised when a retryable failure has no retries left in its budget.

    Always raised as `raise RetryBudgetExhausted(...) from exc`, so `__cause__`
    keeps the original error (its status code, its retry hint) inspectable by
    whatever catches this.
    """


def call_with_retry[T](
    fn: Callable[[], T],
    *,
    is_retryable: Callable[[Exception], bool],
    retry_hint_s: Callable[[Exception], float | None],
    budget: RetryBudget,
    base_delay_s: float,
    max_delay_s: float = 60.0,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> tuple[T, int]:
    """Call `fn`, retrying on a retryable exception until it succeeds or the budget runs out.

    Returns `(result, attempt)` on eventual success, `attempt` being the
    number of retries it took (0 on a first-try success). A non-retryable
    exception (`is_retryable` returns False) re-raises immediately, untouched
    by the budget. A retryable one takes one unit from `budget` -- raising
    `RetryBudgetExhausted` when none remain -- then sleeps for
    `retry_hint_s(exc)` when the caller's provider supplied one, else
    `min(max_delay_s, base_delay_s * 2**attempt)` plus a `jitter()` fractional
    extra, and retries.
    """
    attempt = 0
    while True:
        try:
            return fn(), attempt
        except Exception as exc:
            if not is_retryable(exc):
                raise
            if not budget.take():
                raise RetryBudgetExhausted(
                    f"retry budget exhausted after {attempt} retr"
                    f"{'y' if attempt == 1 else 'ies'}"
                ) from exc
            hint = retry_hint_s(exc)
            delay = (
                hint
                if hint is not None
                else min(max_delay_s, base_delay_s * 2**attempt) + jitter()
            )
            sleep(delay)
            attempt += 1
