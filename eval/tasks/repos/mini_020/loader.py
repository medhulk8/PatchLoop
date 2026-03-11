from models import StudentRecord


def load_records(raw: list[dict]) -> list[StudentRecord]:
    """Parse raw dicts into StudentRecord objects."""
    return [
        StudentRecord(
            student_id=str(r["student_id"]),
            raw_score=float(r["raw_score"]),
            max_score=float(r["max_score"]),
            attempts=int(r["attempts"]),
        )
        for r in raw
    ]
