from models import StudentRecord


def preprocess(records: list[StudentRecord]) -> list[StudentRecord]:
    """Sort records by student_id for deterministic output ordering."""
    return sorted(records, key=lambda r: r.student_id)
