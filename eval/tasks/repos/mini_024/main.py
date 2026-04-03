from pipeline import run_chargeback_report

if __name__ == "__main__":
    sample = [
        {"order_id": "o1", "disputed_value": 30.0, "processed_value": 300.0, "disputed_item_count": 1},
        {"order_id": "o2", "disputed_value": 45.0, "processed_value": 450.0, "disputed_item_count": 3},
    ]
    print(run_chargeback_report(sample))
