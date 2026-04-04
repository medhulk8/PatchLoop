from pipeline import run_pipeline


def test_regression_01():
    # Degenerate case: no shrinkage (opening == closing).
    # lost = 0, so Bug A (divides by closing) gives 0/100 = 0 — same as correct 0/100 = 0.
    records = [{"item_id": "i1", "opening_stock": 100.0, "closing_stock": 100.0, "category": "A"}]
    result = run_pipeline(records)
    assert result[0]["item_id"] == "i1"
    assert result[0]["shrinkage_pct"] == 0.0


def test_regression_02():
    # 20% shrinkage: Bug A uses closing (80) as denominator → 20/80=25%, not 20/100=20%.
    records = [{"item_id": "i2", "opening_stock": 100.0, "closing_stock": 80.0, "category": "A"}]
    result = run_pipeline(records)
    assert result[0]["shrinkage_pct"] == 20.0


def test_regression_03():
    # Multiple items; verify each is computed independently.
    records = [
        {"item_id": "i3", "opening_stock": 200.0, "closing_stock": 160.0, "category": "B"},
        {"item_id": "i4", "opening_stock": 500.0, "closing_stock": 450.0, "category": "B"},
    ]
    result = run_pipeline(records)
    i3 = next(r for r in result if r["item_id"] == "i3")
    i4 = next(r for r in result if r["item_id"] == "i4")
    # i3: 40/200 = 20.0%; i4: 50/500 = 10.0%
    assert i3["shrinkage_pct"] == 20.0
    assert i4["shrinkage_pct"] == 10.0


def test_regression_04():
    # opening=300, closing=292 → lost=8 → shrinkage=8/300=0.02666...
    # Bug B truncates: int(0.02666*10000)/100 = int(266.6)/100 = 266/100 = 2.66
    # Correct:  round(0.02666*10000)/100 = round(266.6)/100 = 267/100 = 2.67 ← DIFFERENT
    # Bug A alone: 8/292=0.02739... → int(273.9)/100 = 2.73 (also wrong — Bug A visible)
    records = [{"item_id": "i5", "opening_stock": 300.0, "closing_stock": 292.0, "category": "C"}]
    result = run_pipeline(records)
    assert result[0]["shrinkage_pct"] == 2.67


def test_regression_05():
    # Larger shrinkage with a clean percentage: 15/300 = 5.0% exactly.
    records = [{"item_id": "i6", "opening_stock": 300.0, "closing_stock": 285.0, "category": "D"}]
    result = run_pipeline(records)
    assert result[0]["shrinkage_pct"] == 5.0
