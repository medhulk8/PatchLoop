from pipeline import run_risk_report


def test_regression_01():
    # 1 blocked event ($100) + 1 allowed ($300). Total=$400, flagged=$100.
    # risk_score = flagged / total = 100 / 400 = 0.25
    events = [
        {"event_id": "e1", "customer_id": "c1", "amount": 100.0, "decision": "block"},
        {"event_id": "e2", "customer_id": "c1", "amount": 300.0, "decision": "allow"},
    ]
    result = run_risk_report(events)
    assert result["risk_score"] == 0.25


def test_regression_02():
    # 1 blocked ($100) + 1 allowed ($400). Total=$500, flagged=$100.
    # risk_score = 100 / 500 = 0.20
    events = [
        {"event_id": "e3", "customer_id": "c2", "amount": 100.0, "decision": "block"},
        {"event_id": "e4", "customer_id": "c2", "amount": 400.0, "decision": "allow"},
    ]
    result = run_risk_report(events)
    assert result["risk_score"] == 0.2


def test_regression_03():
    # 2 blocked ($50 each) + 1 allowed ($300). Total=$400, flagged=$100.
    # risk_score = 100 / 400 = 0.25
    events = [
        {"event_id": "e5", "customer_id": "c3", "amount": 50.0, "decision": "block"},
        {"event_id": "e6", "customer_id": "c3", "amount": 50.0, "decision": "block"},
        {"event_id": "e7", "customer_id": "c3", "amount": 300.0, "decision": "allow"},
    ]
    result = run_risk_report(events)
    assert result["flagged_amount"] == 100.0
    assert result["risk_score"] == 0.25


def test_regression_04():
    # 1 blocked ($60) + 1 review ($90) + 1 allowed ($150). Total=$300.
    # Both block and review count as flagged: flagged=$150, risk_score=150/300=0.5
    # Bug B only flags "block", giving flagged=$60, score=60/300=0.2 (wrong).
    events = [
        {"event_id": "e8",  "customer_id": "c4", "amount": 60.0,  "decision": "block"},
        {"event_id": "e9",  "customer_id": "c4", "amount": 90.0,  "decision": "review"},
        {"event_id": "e10", "customer_id": "c4", "amount": 150.0, "decision": "allow"},
    ]
    result = run_risk_report(events)
    assert result["flagged_amount"] == 150.0
    assert result["risk_score"] == 0.5


def test_regression_05():
    # 1 blocked ($80) + 1 allowed ($320). Total=$400, flagged=$80.
    # risk_score = 80 / 400 = 0.20
    events = [
        {"event_id": "e11", "customer_id": "c5", "amount": 80.0,  "decision": "block"},
        {"event_id": "e12", "customer_id": "c5", "amount": 320.0, "decision": "allow"},
    ]
    result = run_risk_report(events)
    assert result["risk_score"] == 0.2
