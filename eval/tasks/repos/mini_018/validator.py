REQUIRED_FIELDS = {"worker_id", "completed_jobs", "elapsed_hours", "num_workers"}


def validate_records(records: list[dict]) -> None:
    """Validate that all required fields are present and values are in range."""
    for i, r in enumerate(records):
        missing = REQUIRED_FIELDS - r.keys()
        if missing:
            raise ValueError(f"Record {i}: missing fields {missing}")
        if float(r["elapsed_hours"]) <= 0:
            raise ValueError(f"Record {i}: elapsed_hours must be positive")
        if int(r["num_workers"]) <= 0:
            raise ValueError(f"Record {i}: num_workers must be positive")
        if int(r["completed_jobs"]) < 0:
            raise ValueError(f"Record {i}: completed_jobs must be non-negative")
