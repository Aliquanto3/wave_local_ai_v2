import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_dependencies import evaluate_waiver, select_blocking, waiver_rejection


def _waiver(
    opened: str, expiry: str, package: str = "pkg", vuln_id: str = "GHSA-1"
) -> dict:
    return {
        "id": vuln_id,
        "package": package,
        "reason": "test",
        "opened": opened,
        "expiry": expiry,
        "owner": "someone",
    }


def test_evaluate_waiver_rejects_expired_entry() -> None:
    entry = _waiver(opened="2026-01-01", expiry="2026-01-10")
    today = date(2026, 1, 11)

    assert evaluate_waiver(entry, today) is False


def test_evaluate_waiver_rejects_over_90_day_window_even_before_expiry() -> None:
    entry = _waiver(opened="2026-01-01", expiry="2026-05-01")  # ~120 days
    today = date(2026, 1, 5)  # well before expiry

    assert evaluate_waiver(entry, today) is False


def test_evaluate_waiver_accepts_current_entry_within_window() -> None:
    entry = _waiver(opened="2026-01-01", expiry="2026-03-01")  # 59 days
    today = date(2026, 1, 15)

    assert evaluate_waiver(entry, today) is True


def test_waiver_rejection_names_the_expiry_date() -> None:
    entry = _waiver(opened="2026-01-01", expiry="2026-01-10")
    today = date(2026, 1, 11)

    assert waiver_rejection(entry, today) == "expired 2026-01-10"


def test_waiver_rejection_names_the_over_long_lifetime() -> None:
    entry = _waiver(opened="2026-01-01", expiry="2026-05-01")
    today = date(2026, 1, 5)

    assert waiver_rejection(entry, today) == "lifetime 120 days > 90"


def test_select_blocking_returns_unwaived_high_and_drops_low() -> None:
    findings = [
        {"package": "pkg-high", "id": "GHSA-high", "severity": "HIGH"},
        {"package": "pkg-low", "id": "GHSA-low", "severity": "LOW"},
    ]
    waivers: list[dict] = []
    today = date(2026, 1, 15)

    blocking = select_blocking(findings, waivers, today)

    assert blocking == [{"package": "pkg-high", "id": "GHSA-high", "severity": "HIGH"}]
