from pipeline import run_report


def test_regression_01():
    # Single item, qty=1: refund_rate = refunded / order_value = 50 / 200 = 0.25
    records = [{"order_id": "o1", "order_value": 200.0, "refund_amount": 50.0, "quantity": 1}]
    result = run_report(records)
    assert result["refund_rate"] == 0.25


def test_regression_02():
    # Single item, qty=1: 100 / 400 = 0.25
    records = [{"order_id": "o2", "order_value": 400.0, "refund_amount": 100.0, "quantity": 1}]
    result = run_report(records)
    assert result["refund_rate"] == 0.25


def test_regression_03():
    # Two qty=1 orders: total_refunded=50, total_order_value=400, rate=0.125
    records = [
        {"order_id": "o3", "order_value": 100.0, "refund_amount": 20.0, "quantity": 1},
        {"order_id": "o4", "order_value": 300.0, "refund_amount": 30.0, "quantity": 1},
    ]
    result = run_report(records)
    assert result["total_refunded"] == 50.0
    assert result["total_order_value"] == 400.0
    assert result["refund_rate"] == 0.125


def test_regression_04():
    # Multi-quantity refund: qty=3, order_value=150, refund_amount=60 total.
    # Each item should carry refund_amount=20 (60/3), not the full 60.
    # Bug in expand_refund_rows copies the full 60 per row, so total_refunded
    # becomes 180 instead of 60, and refund_rate becomes 1.2 instead of 0.4.
    records = [{"order_id": "o5", "order_value": 150.0, "refund_amount": 60.0, "quantity": 3}]
    result = run_report(records)
    assert result["total_refunded"] == 60.0
    assert result["total_order_value"] == 150.0
    assert result["refund_rate"] == 0.4


def test_regression_05():
    # Single item, qty=1: 100 / 500 = 0.2
    records = [{"order_id": "o6", "order_value": 500.0, "refund_amount": 100.0, "quantity": 1}]
    result = run_report(records)
    assert result["refund_rate"] == 0.2
