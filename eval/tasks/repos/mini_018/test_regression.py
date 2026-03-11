from pipeline import run_pipeline


def test_regression_01():
    # Degenerate case: num_workers == elapsed_hours (both = 2).
    # Bug A divides by num_workers, so 20/2 == 20/2 — invisible here.
    # Bug B: int(10.0 * 100) / 100 = 10.0 = round(10.0 * 100) / 100 — also invisible.
    records = [{"worker_id": "w1", "completed_jobs": 20, "elapsed_hours": 2.0, "num_workers": 2}]
    result = run_pipeline(records)
    assert result[0]["worker_id"] == "w1"
    assert result[0]["rate"] == 10.0


def test_regression_02():
    # num_workers (4) != elapsed_hours (6): Bug A gives 36/4=9.0, correct is 36/6=6.0.
    records = [{"worker_id": "w2", "completed_jobs": 36, "elapsed_hours": 6.0, "num_workers": 4}]
    result = run_pipeline(records)
    assert result[0]["rate"] == 6.0


def test_regression_03():
    # Multiple worker groups in a single pipeline run.
    records = [
        {"worker_id": "w3", "completed_jobs": 60, "elapsed_hours": 4.0, "num_workers": 5},
        {"worker_id": "w4", "completed_jobs": 18, "elapsed_hours": 3.0, "num_workers": 6},
    ]
    result = run_pipeline(records)
    w3 = next(r for r in result if r["worker_id"] == "w3")
    w4 = next(r for r in result if r["worker_id"] == "w4")
    # w3: 60/4 = 15.0; w4: 18/3 = 6.0
    assert w3["rate"] == 15.0
    assert w4["rate"] == 6.0


def test_regression_04():
    # completed_jobs=8, elapsed_hours=3 → rate=8/3=2.666...
    # Bug B truncates: int(2.666*100)/100 = int(266.6)/100 = 266/100 = 2.66
    # Correct:  round(2.666*100)/100 = round(266.6)/100 = 267/100 = 2.67 ← DIFFERENT
    # Bug A: 8/4=2.0 → int(2.0*100)/100 = 2.0 (also wrong — Bug A visible)
    records = [{"worker_id": "w5", "completed_jobs": 8, "elapsed_hours": 3.0, "num_workers": 4}]
    result = run_pipeline(records)
    assert result[0]["rate"] == 2.67


def test_regression_05():
    # rate = 100/8 = 12.5 — clean value, Bug B invisible after Bug A fix.
    records = [{"worker_id": "w6", "completed_jobs": 100, "elapsed_hours": 8.0, "num_workers": 10}]
    result = run_pipeline(records)
    assert result[0]["rate"] == 12.5
