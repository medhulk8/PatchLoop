from pipeline import run_risk_report

if __name__ == "__main__":
    sample = [
        {"event_id": "e1", "customer_id": "c1", "amount": 100.0, "decision": "block"},
        {"event_id": "e2", "customer_id": "c1", "amount": 90.0, "decision": "review"},
        {"event_id": "e3", "customer_id": "c1", "amount": 310.0, "decision": "allow"},
    ]
    print(run_risk_report(sample))
