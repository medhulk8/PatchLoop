from main import run_fulfillment_report


def test_regression_01():
    orders = [{"order_id": "o1", "units_filled": 20.0, "units_ordered": 100.0, "sku_count": 1}]
    result = run_fulfillment_report(orders)
    assert result["fill_rate"] == 0.2


def test_regression_02():
    orders = [
        {"order_id": "o2", "units_filled": 50.0, "units_ordered": 200.0, "sku_count": 1},
        {"order_id": "o3", "units_filled": 50.0, "units_ordered": 200.0, "sku_count": 1},
    ]
    result = run_fulfillment_report(orders)
    assert result["fill_rate"] == 0.25


def test_regression_03():
    orders = [{"order_id": "o4", "units_filled": 80.0, "units_ordered": 400.0, "sku_count": 1}]
    result = run_fulfillment_report(orders)
    assert result["fill_rate"] == 0.2


def test_regression_04():
    orders = [{"order_id": "o5", "units_filled": 30.0, "units_ordered": 300.0, "sku_count": 3}]
    result = run_fulfillment_report(orders)
    assert result["fill_rate"] == 0.1


def test_regression_05():
    orders = [
        {"order_id": "o6", "units_filled": 10.0, "units_ordered": 500.0, "sku_count": 1},
        {"order_id": "o7", "units_filled": 40.0, "units_ordered": 500.0, "sku_count": 1},
    ]
    result = run_fulfillment_report(orders)
    assert result["fill_rate"] == 0.05
