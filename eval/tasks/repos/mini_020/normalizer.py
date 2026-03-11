def normalize_output(records: list[dict]) -> list[dict]:
    """Ensure consistent field ordering in output records."""
    return [
        {"student_id": r["student_id"], "score_pct": r["score_pct"]}
        for r in records
    ]
