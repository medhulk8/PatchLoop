from pipeline import run_report


def test_regression_01():
    # Uniform weights: weighted average equals plain average; baseline sanity check
    records = [
        {"id": "r1", "category": "alpha", "amount": 10.0, "weight": 1.0},
        {"id": "r2", "category": "alpha", "amount": 20.0, "weight": 1.0},
    ]
    result = run_report(records)
    assert len(result) == 1
    assert result[0]["category"] == "alpha"
    assert result[0]["representative"] == "15.00"


def test_regression_02():
    # Non-uniform weights: a high-weight record should dominate the representative value
    records = [
        {"id": "r1", "category": "beta", "amount": 100.0, "weight": 9.0},
        {"id": "r2", "category": "beta", "amount": 10.0, "weight": 1.0},
    ]
    result = run_report(records)
    # weighted avg = (100*9 + 10*1) / (9+1) = 910/10 = 91.0
    # plain avg    = (100 + 10) / 2         = 55.0  <- bug produces this
    assert result[0]["representative"] == "91.00"


def test_regression_03():
    # Multiple categories; each bucket's representative is computed independently
    records = [
        {"id": "r1", "category": "gamma", "amount": 200.0, "weight": 3.0},
        {"id": "r2", "category": "gamma", "amount": 50.0,  "weight": 1.0},
        {"id": "r3", "category": "delta", "amount": 80.0,  "weight": 4.0},
        {"id": "r4", "category": "delta", "amount": 20.0,  "weight": 1.0},
    ]
    result = run_report(records)
    gamma = next(r for r in result if r["category"] == "gamma")
    delta = next(r for r in result if r["category"] == "delta")
    # gamma: (200*3 + 50*1) / (3+1) = 650/4 = 162.5
    assert gamma["representative"] == "162.50"
    # delta: (80*4 + 20*1) / (4+1) = 340/5 = 68.0
    assert delta["representative"] == "68.00"


def test_regression_04():
    # Zero-amount record with high weight should pull representative down significantly
    records = [
        {"id": "r1", "category": "epsilon", "amount": 0.0,   "weight": 10.0},
        {"id": "r2", "category": "epsilon", "amount": 100.0,  "weight": 1.0},
    ]
    result = run_report(records)
    # weighted avg = (0*10 + 100*1) / (10+1) = 100/11 = 9.0909...
    assert result[0]["representative"] == "9.0909"


def test_regression_05():
    # Fractional weights summing to 1.0; weighted avg differs clearly from plain avg
    records = [
        {"id": "r1", "category": "zeta", "amount": 60.0, "weight": 0.5},
        {"id": "r2", "category": "zeta", "amount": 40.0, "weight": 0.3},
        {"id": "r3", "category": "zeta", "amount": 10.0, "weight": 0.2},
    ]
    result = run_report(records)
    # weighted avg = (60*0.5 + 40*0.3 + 10*0.2) / 1.0 = (30+12+2) / 1.0 = 44.0
    # plain avg    = (60 + 40 + 10) / 3 = 36.67
    assert result[0]["representative"] == "44.00"
