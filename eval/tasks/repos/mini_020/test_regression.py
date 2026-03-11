from pipeline import run_pipeline


def test_regression_01():
    # Degenerate case: max_score == attempts == 4.
    # Bug A divides by attempts (4) instead of max_score (4) — same value, so result is identical.
    # Bug B: int(75.0) = 75 = round(75.0), so Bug B invisible too.
    records = [{"student_id": "s1", "raw_score": 3.0, "max_score": 4.0, "attempts": 4}]
    result = run_pipeline(records)
    assert result[0]["student_id"] == "s1"
    assert result[0]["score_pct"] == 75


def test_regression_02():
    # Bug A: 72/4*100=1800, not 72/100*100=72. Clean value — Bug B invisible after fix.
    records = [{"student_id": "s2", "raw_score": 72.0, "max_score": 100.0, "attempts": 4}]
    result = run_pipeline(records)
    assert result[0]["score_pct"] == 72


def test_regression_03():
    # Multiple students; each computed independently.
    records = [
        {"student_id": "s3", "raw_score": 85.0, "max_score": 100.0, "attempts": 5},
        {"student_id": "s4", "raw_score": 63.0, "max_score": 90.0, "attempts": 3},
    ]
    result = run_pipeline(records)
    s3 = next(r for r in result if r["student_id"] == "s3")
    s4 = next(r for r in result if r["student_id"] == "s4")
    # s3: 85/100*100=85; s4: 63/90*100=70
    assert s3["score_pct"] == 85
    assert s4["score_pct"] == 70


def test_regression_04():
    # raw=80, max=120, attempts=5
    # Correct: 80/120*100=66.666... → round=67
    # Bug B: int(66.666)=66 ≠ 67  ← truncation vs rounding differ
    # Bug A: 80/5*100=1600 (wrong — fails on buggy code)
    records = [{"student_id": "s5", "raw_score": 80.0, "max_score": 120.0, "attempts": 5}]
    result = run_pipeline(records)
    assert result[0]["score_pct"] == 67


def test_regression_05():
    # raw=40, max=80, attempts=5. Correct: 40/80*100=50. Clean value — Bug B invisible.
    records = [{"student_id": "s6", "raw_score": 40.0, "max_score": 80.0, "attempts": 5}]
    result = run_pipeline(records)
    assert result[0]["score_pct"] == 50
