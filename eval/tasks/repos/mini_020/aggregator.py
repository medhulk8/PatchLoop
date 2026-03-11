from models import StudentRecord


def aggregate(records: list[StudentRecord], scores: list[float]) -> list[dict]:
    """Pair each student record with its computed normalized score."""
    return [
        {"student_id": r.student_id, "score": s}
        for r, s in zip(records, scores)
    ]
