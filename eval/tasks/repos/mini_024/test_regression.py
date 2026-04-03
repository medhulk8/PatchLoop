from pipeline import run_chargeback_report


def test_regression_01():
    # Single item, disputed_item_count=1: chargeback_rate = 30 / 300 = 0.10
    records = [{"order_id": "o1", "disputed_value": 30.0, "processed_value": 300.0, "disputed_item_count": 1}]
    result = run_chargeback_report(records)
    assert result["chargeback_rate"] == 0.1


def test_regression_02():
    # Single item: 50 / 500 = 0.10
    records = [{"order_id": "o2", "disputed_value": 50.0, "processed_value": 500.0, "disputed_item_count": 1}]
    result = run_chargeback_report(records)
    assert result["chargeback_rate"] == 0.1


def test_regression_03():
    # Two qty=1 orders: total_disputed=80, total_processed=800, rate=0.10
    records = [
        {"order_id": "o3", "disputed_value": 30.0, "processed_value": 300.0, "disputed_item_count": 1},
        {"order_id": "o4", "disputed_value": 50.0, "processed_value": 500.0, "disputed_item_count": 1},
    ]
    result = run_chargeback_report(records)
    assert result["total_disputed"] == 80.0
    assert result["total_processed"] == 800.0
    assert result["chargeback_rate"] == 0.1


def test_regression_04():
    # Multi-item dispute: disputed_item_count=3, disputed_value=45 total.
    # Each expanded row should carry disputed_value=15 (45/3), not full 45.
    # Bug B copies full 45 per row → total_disputed becomes 135 instead of 45.
    # With Bug A also present: rate = 450/135 = 3.33 (wrong).
    # After Bug A fix only: rate = 135/450 = 0.30 (wrong, should be 0.10).
    # After both fixes: rate = 45/450 = 0.10 (correct).
    records = [{"order_id": "o5", "disputed_value": 45.0, "processed_value": 450.0, "disputed_item_count": 3}]
    result = run_chargeback_report(records)
    assert result["total_disputed"] == 45.0
    assert result["total_processed"] == 450.0
    assert result["chargeback_rate"] == 0.1


def test_regression_05():
    # Single item: 20 / 400 = 0.05
    records = [{"order_id": "o6", "disputed_value": 20.0, "processed_value": 400.0, "disputed_item_count": 1}]
    result = run_chargeback_report(records)
    assert result["chargeback_rate"] == 0.05
