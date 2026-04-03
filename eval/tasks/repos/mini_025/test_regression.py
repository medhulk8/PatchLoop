from pipeline import run_defect_report


def test_regression_01():
    # Single batch, sample_size=1: defect_rate = 10 / 200 = 0.05
    batches = [{"batch_id": "b1", "defective_units": 10.0, "total_units": 200.0, "sample_size": 1}]
    result = run_defect_report(batches)
    assert result["defect_rate"] == 0.05


def test_regression_02():
    # Single batch: 20 / 400 = 0.05
    batches = [{"batch_id": "b2", "defective_units": 20.0, "total_units": 400.0, "sample_size": 1}]
    result = run_defect_report(batches)
    assert result["defect_rate"] == 0.05


def test_regression_03():
    # Two sample_size=1 batches: total_defective=30, total_units=600, rate=0.05
    batches = [
        {"batch_id": "b3", "defective_units": 10.0, "total_units": 200.0, "sample_size": 1},
        {"batch_id": "b4", "defective_units": 20.0, "total_units": 400.0, "sample_size": 1},
    ]
    result = run_defect_report(batches)
    assert result["total_defective"] == 30.0
    assert result["total_units"] == 600.0
    assert result["defect_rate"] == 0.05


def test_regression_04():
    # Multi-unit sample: sample_size=4, defective_units=8 total.
    # Each expanded row should carry defective_units=2 (8/4), not full 8.
    # Bug B copies full 8 per row → total_defective becomes 32 instead of 8.
    # After Bug A fix only: rate = 32/200 = 0.16 (wrong, should be 0.04).
    # After both fixes: rate = 8/200 = 0.04 (correct).
    batches = [{"batch_id": "b5", "defective_units": 8.0, "total_units": 200.0, "sample_size": 4}]
    result = run_defect_report(batches)
    assert result["total_defective"] == 8.0
    assert result["total_units"] == 200.0
    assert result["defect_rate"] == 0.04


def test_regression_05():
    # Single batch: 5 / 500 = 0.01
    batches = [{"batch_id": "b6", "defective_units": 5.0, "total_units": 500.0, "sample_size": 1}]
    result = run_defect_report(batches)
    assert result["defect_rate"] == 0.01
