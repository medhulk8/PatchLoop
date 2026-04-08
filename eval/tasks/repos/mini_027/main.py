from pipeline import run_downtime_report

if __name__ == "__main__":
    sample = [
        {"site_id": "s1", "downtime_minutes": 20.0, "scheduled_minutes": 200.0, "machine_count": 1},
        {"site_id": "s2", "downtime_minutes": 30.0, "scheduled_minutes": 300.0, "machine_count": 3},
    ]
    print(run_downtime_report(sample))
