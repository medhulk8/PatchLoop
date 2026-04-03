from pipeline import run_dispute_report

if __name__ == "__main__":
    sample = [
        {"invoice_id": "i1", "disputed_amount": 20.0, "invoice_value": 200.0, "quantity": 1},
        {"invoice_id": "i2", "disputed_amount": 30.0, "invoice_value": 300.0, "quantity": 3},
    ]
    print(run_dispute_report(sample))
