from pipeline import run_dispute_report


def test_regression_01():
    # Single line, quantity=1: dispute_rate = 20 / 200 = 0.10
    invoices = [{"invoice_id": "i1", "disputed_amount": 20.0, "invoice_value": 200.0, "quantity": 1}]
    result = run_dispute_report(invoices)
    assert result["dispute_rate"] == 0.1


def test_regression_02():
    # Single line: 50 / 500 = 0.10
    invoices = [{"invoice_id": "i2", "disputed_amount": 50.0, "invoice_value": 500.0, "quantity": 1}]
    result = run_dispute_report(invoices)
    assert result["dispute_rate"] == 0.1


def test_regression_03():
    # Two quantity=1 invoices: total_disputed=70, total_invoice_value=700, rate=0.10
    invoices = [
        {"invoice_id": "i3", "disputed_amount": 20.0, "invoice_value": 200.0, "quantity": 1},
        {"invoice_id": "i4", "disputed_amount": 50.0, "invoice_value": 500.0, "quantity": 1},
    ]
    result = run_dispute_report(invoices)
    assert result["dispute_rate"] == 0.1


def test_regression_04():
    # Multi-line invoice: quantity=3, disputed_amount=30 total, invoice_value=300.
    # Correct dispute_rate = 30 / 300 = 0.10.
    # Bug B copies full 30 per line → total_disputed=90, rate=90/300=0.30 (wrong after Bug A fix).
    invoices = [{"invoice_id": "i5", "disputed_amount": 30.0, "invoice_value": 300.0, "quantity": 3}]
    result = run_dispute_report(invoices)
    assert result["dispute_rate"] == 0.1


def test_regression_05():
    # Single line: 10 / 500 = 0.02
    invoices = [{"invoice_id": "i6", "disputed_amount": 10.0, "invoice_value": 500.0, "quantity": 1}]
    result = run_dispute_report(invoices)
    assert result["dispute_rate"] == 0.02
