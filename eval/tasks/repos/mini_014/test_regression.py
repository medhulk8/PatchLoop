from pipeline import run_report


def test_regression_01():
    # Basic report: two categories, multiple transactions each
    records = [
        {"id": "t1", "category": "food", "amount": 10.0},
        {"id": "t2", "category": "food", "amount": 5.0},
        {"id": "t3", "category": "travel", "amount": 100.0},
    ]
    report = run_report(records)
    assert report.totals == {"food": 15.0, "travel": 100.0}


def test_regression_02():
    # Single category with many transactions should collapse to one total
    records = [
        {"id": "a1", "category": "utilities", "amount": 50.0},
        {"id": "a2", "category": "utilities", "amount": 30.0},
        {"id": "a3", "category": "utilities", "amount": 20.0},
    ]
    report = run_report(records)
    assert report.totals == {"utilities": 100.0}
    assert report.record_count == 3


def test_regression_03():
    # Amounts with cents should be summed correctly
    records = [
        {"id": "x1", "category": "health", "amount": 12.50},
        {"id": "x2", "category": "health", "amount": 7.75},
        {"id": "x3", "category": "misc", "amount": 3.25},
    ]
    report = run_report(records)
    assert report.totals == {"health": 20.25, "misc": 3.25}


def test_regression_04():
    # Categories list should reflect actual categories, not transaction IDs
    records = [
        {"id": "r1", "category": "books", "amount": 15.0},
        {"id": "r2", "category": "books", "amount": 25.0},
        {"id": "r3", "category": "music", "amount": 9.99},
    ]
    report = run_report(records)
    assert set(report.totals.keys()) == {"books", "music"}


def test_regression_05():
    # Mixed categories: each category total is independent of other categories
    records = [
        {"id": "m1", "category": "rent", "amount": 1200.0},
        {"id": "m2", "category": "food", "amount": 200.0},
        {"id": "m3", "category": "rent", "amount": 0.0},
        {"id": "m4", "category": "food", "amount": 150.0},
    ]
    report = run_report(records)
    assert report.totals["rent"] == 1200.0
    assert report.totals["food"] == 350.0
