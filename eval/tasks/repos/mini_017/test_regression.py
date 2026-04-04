"""Regression tests for the log aggregation pipeline."""
import pytest
from pipeline import run_report


def _find(report: list[dict], service: str) -> dict:
    for row in report:
        if row["service"] == service:
            return row
    raise KeyError(service)


def test_regression_01():
    """Single entry, single request: error rate is unambiguous."""
    raw = [{"service": "alpha", "total_requests": 1, "error_count": 1.0, "window_seconds": 10}]
    report = run_report(raw)
    row = _find(report, "alpha")
    assert row["error_rate"] == pytest.approx(1.0)
    assert row["error_count"] == pytest.approx(1.0)
    assert row["total_requests"] == 1


def test_regression_02():
    """Two entries with different request loads: error rate must weight by requests, not by entry."""
    # entry A: 100 requests, 10 errors
    # entry B: 900 requests, 0 errors
    # correct error_rate = 10 / 1000 = 0.01
    # buggy error_rate  = (10+0) / 2 = 5.0  (divides by 2 entries)
    raw = [
        {"service": "beta", "total_requests": 100, "error_count": 10.0, "window_seconds": 60},
        {"service": "beta", "total_requests": 900, "error_count": 0.0, "window_seconds": 60},
    ]
    report = run_report(raw)
    row = _find(report, "beta")
    assert row["error_rate"] == pytest.approx(0.01)
    assert row["total_requests"] == 1000


def test_regression_03():
    """Three entries: verify aggregate request count and error rate calculation."""
    # 50 + 150 + 300 = 500 total requests
    # 5 + 15 + 30 = 50 total errors
    # correct error_rate = 50 / 500 = 0.1
    # buggy error_rate  = 50 / 3 ≈ 16.667
    raw = [
        {"service": "gamma", "total_requests": 50,  "error_count": 5.0,  "window_seconds": 30},
        {"service": "gamma", "total_requests": 150, "error_count": 15.0, "window_seconds": 30},
        {"service": "gamma", "total_requests": 300, "error_count": 30.0, "window_seconds": 60},
    ]
    report = run_report(raw)
    row = _find(report, "gamma")
    assert row["error_rate"] == pytest.approx(0.1)
    assert row["total_requests"] == 500
    assert row["error_count"] == pytest.approx(50.0)


def test_regression_04():
    """Fractional error counts must be preserved exactly — no integer truncation."""
    # entry A: 200 requests, 5.75 errors
    # entry B: 100 requests, 8.5  errors
    # total_errors = 14.25 (exactly representable in float64)
    # total_requests = 300
    # correct error_rate = 14.25 / 300 = 0.0475
    # correct error_count = 14.25
    # buggy (int truncation): error_count = 14, error_rate would still be computed from floats above,
    #   but the persisted error_count field would read 14 instead of 14.25
    raw = [
        {"service": "delta", "total_requests": 200, "error_count": 5.75, "window_seconds": 60},
        {"service": "delta", "total_requests": 100, "error_count": 8.5,  "window_seconds": 60},
    ]
    report = run_report(raw)
    row = _find(report, "delta")
    assert row["error_rate"] == pytest.approx(0.0475)
    assert row["error_count"] == pytest.approx(14.25), (
        f"error_count should be 14.25 (float), got {row['error_count']!r}"
    )
    assert row["total_requests"] == 300


def test_regression_05():
    """Multi-service report: each service's error rate computed independently."""
    raw = [
        # service "low": 1000 requests, 10 errors → rate = 0.01
        {"service": "low",  "total_requests": 1000, "error_count": 10.0, "window_seconds": 120},
        # service "high": 200 requests, 40 errors → rate = 0.2
        {"service": "high", "total_requests": 200,  "error_count": 40.0, "window_seconds": 60},
        # second entry for "high": 100 requests, 10 errors → combined rate = 50/300 ≈ 0.1667
        {"service": "high", "total_requests": 100,  "error_count": 10.0, "window_seconds": 60},
    ]
    report = run_report(raw)
    low  = _find(report, "low")
    high = _find(report, "high")
    assert low["error_rate"]  == pytest.approx(0.01)
    assert high["error_rate"] == pytest.approx(50.0 / 300.0)
    assert high["total_requests"] == 300
