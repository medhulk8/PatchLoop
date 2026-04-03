from pipeline import run_defect_report

if __name__ == "__main__":
    sample = [
        {"batch_id": "b1", "defective_units": 10.0, "total_units": 200.0, "sample_size": 1},
        {"batch_id": "b2", "defective_units": 15.0, "total_units": 300.0, "sample_size": 3},
    ]
    print(run_defect_report(sample))
