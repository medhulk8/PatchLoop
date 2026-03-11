def build_record(student_id: str, score: float) -> dict:
    """
    Assemble the final output record for a student.

    The score is stored as an integer percentage to align with the
    grading system's whole-number reporting format.
    """
    # BUG: integer division truncates the decimal part of the score
    return {
        "student_id": student_id,
        "score_pct": int(score),
    }


def build_all(aggregated: list[dict]) -> list[dict]:
    return [build_record(item["student_id"], item["score"]) for item in aggregated]
