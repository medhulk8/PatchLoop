REQUIRED_FIELDS = {"student_id", "raw_score", "max_score", "attempts"}


def validate_records(records: list[dict]) -> None:
    """Validate that all required fields are present and values are in range."""
    for i, r in enumerate(records):
        missing = REQUIRED_FIELDS - r.keys()
        if missing:
            raise ValueError(f"Record {i}: missing fields {missing}")
        if float(r["max_score"]) <= 0:
            raise ValueError(f"Record {i}: max_score must be positive")
        if int(r["attempts"]) <= 0:
            raise ValueError(f"Record {i}: attempts must be positive")
        if float(r["raw_score"]) < 0:
            raise ValueError(f"Record {i}: raw_score must be non-negative")
