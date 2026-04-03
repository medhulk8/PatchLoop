from pipeline import run_report

if __name__ == "__main__":
    sample = [
        {"order_id": "o1", "order_value": 200.0, "refund_amount": 50.0, "quantity": 1},
        {"order_id": "o2", "order_value": 150.0, "refund_amount": 60.0, "quantity": 3},
    ]
    print(run_report(sample))
