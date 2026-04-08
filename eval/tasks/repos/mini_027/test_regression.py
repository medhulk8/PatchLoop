from pipeline import run_downtime_report


def test_regression_01():
    records = [{"site_id": "s1", "downtime_minutes": 20.0, "scheduled_minutes": 200.0, "machine_count": 1}]
    result = run_downtime_report(records)
    assert result["downtime_ratio"] == 0.1


def test_regression_02():
    records = [{"site_id": "s2", "downtime_minutes": 50.0, "scheduled_minutes": 500.0, "machine_count": 1}]
    result = run_downtime_report(records)
    assert result["downtime_ratio"] == 0.1


def test_regression_03():
    records = [
        {"site_id": "s3", "downtime_minutes": 20.0, "scheduled_minutes": 200.0, "machine_count": 1},
        {"site_id": "s4", "downtime_minutes": 50.0, "scheduled_minutes": 500.0, "machine_count": 1},
    ]
    result = run_downtime_report(records)
    assert result["downtime_ratio"] == 0.1


def test_regression_04():
    records = [{"site_id": "s5", "downtime_minutes": 30.0, "scheduled_minutes": 300.0, "machine_count": 3}]
    result = run_downtime_report(records)
    assert result["downtime_ratio"] == 0.1


def test_regression_05():
    records = [{"site_id": "s6", "downtime_minutes": 10.0, "scheduled_minutes": 500.0, "machine_count": 1}]
    result = run_downtime_report(records)
    assert result["downtime_ratio"] == 0.02
