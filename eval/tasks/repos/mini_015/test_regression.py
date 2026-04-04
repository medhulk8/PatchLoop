from pipeline import run_pipeline


def test_regression_01():
    # Standard events with non-zero priorities and values; baseline sanity check
    records = [
        {"id": "e1", "category": "web", "priority": 3, "value": 10.0},
        {"id": "e2", "category": "web", "priority": 7, "value": 20.0},
    ]
    result = run_pipeline(records)
    assert len(result) == 1
    assert result[0]["category"] == "web"
    assert result[0]["count"] == 2
    assert result[0]["total"] == 30.0
    assert result[0]["priority_range"] == "3-7"


def test_regression_02():
    # An event with value 0.0 must contribute 0.0 to the total, not be replaced
    records = [
        {"id": "e1", "category": "api", "priority": 5, "value": 0.0},
        {"id": "e2", "category": "api", "priority": 5, "value": 15.0},
    ]
    result = run_pipeline(records)
    assert result[0]["total"] == 15.0


def test_regression_03():
    # An event with priority 0 must be counted; the min of [0, 3] is 0
    records = [
        {"id": "e1", "category": "bg", "priority": 0, "value": 5.0},
        {"id": "e2", "category": "bg", "priority": 3, "value": 5.0},
    ]
    result = run_pipeline(records)
    assert result[0]["priority_range"] == "0-3"


def test_regression_04():
    # All events have priority 0; min and max must both be 0
    records = [
        {"id": "e1", "category": "low", "priority": 0, "value": 1.0},
        {"id": "e2", "category": "low", "priority": 0, "value": 2.0},
    ]
    result = run_pipeline(records)
    assert result[0]["priority_range"] == "0-0"


def test_regression_05():
    # Two categories; zero-priority events in one must not corrupt the other
    records = [
        {"id": "e1", "category": "a", "priority": 0, "value": 5.0},
        {"id": "e2", "category": "a", "priority": 2, "value": 3.0},
        {"id": "e3", "category": "b", "priority": 1, "value": 4.0},
    ]
    result = run_pipeline(records)
    a = next(r for r in result if r["category"] == "a")
    b = next(r for r in result if r["category"] == "b")
    assert a["priority_range"] == "0-2"
    assert b["priority_range"] == "1-1"
