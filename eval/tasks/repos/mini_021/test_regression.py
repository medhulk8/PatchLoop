from pipeline import run_pipeline


def test_regression_01():
    # Degenerate case: quantity == weight == 3, handling_fee == 0.
    # Bug A: unit_price * weight = unit_price * quantity → same value. Bug A invisible.
    # Bug B: round(cost - 0) = round(cost + 0) → fee of 0, Bug B invisible.
    records = [{"item_id": "i1", "unit_price": 10.0, "quantity": 3, "weight": 3.0, "handling_fee": 0.0}]
    result = run_pipeline(records)
    assert result[0]["item_id"] == "i1"
    assert result[0]["final_price"] == 30


def test_regression_02():
    # Bug A: 8 * 2.0 = 16, not 8 * 5 = 40. handling_fee=0 so Bug B invisible after fix.
    records = [{"item_id": "i2", "unit_price": 8.0, "quantity": 5, "weight": 2.0, "handling_fee": 0.0}]
    result = run_pipeline(records)
    assert result[0]["final_price"] == 40


def test_regression_03():
    # Multiple items. i3: qty==weight, fee=0 (both bugs hidden). i4: qty≠weight, fee=0 (Bug A visible).
    records = [
        {"item_id": "i3", "unit_price": 6.0, "quantity": 4, "weight": 4.0, "handling_fee": 0.0},
        {"item_id": "i4", "unit_price": 9.0, "quantity": 2, "weight": 1.0, "handling_fee": 0.0},
    ]
    result = run_pipeline(records)
    i3 = next(r for r in result if r["item_id"] == "i3")
    i4 = next(r for r in result if r["item_id"] == "i4")
    # i3: 6*4=24; i4: 9*2=18
    assert i3["final_price"] == 24
    assert i4["final_price"] == 18


def test_regression_04():
    # qty=4, weight=2.0, fee=10.
    # Correct: cost=15*4=60, final=round(60+10)=70.
    # Bug A active: cost=15*2.0=30, final=round(30-10)=20 → FAIL.
    # Fix Bug A only: cost=60, Bug B: round(60-10)=50 ≠ 70 → still FAIL.
    # Fix both: round(60+10)=70 → PASS.
    records = [{"item_id": "i5", "unit_price": 15.0, "quantity": 4, "weight": 2.0, "handling_fee": 10.0}]
    result = run_pipeline(records)
    assert result[0]["final_price"] == 70


def test_regression_05():
    # Bug A: 25 * 3.0 = 75, not 25 * 6 = 150. handling_fee=0 so Bug B invisible after fix.
    records = [{"item_id": "i6", "unit_price": 25.0, "quantity": 6, "weight": 3.0, "handling_fee": 0.0}]
    result = run_pipeline(records)
    assert result[0]["final_price"] == 150
