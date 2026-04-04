from models import StudentRecord


def compute_normalized(record: StudentRecord) -> float:
    """
    Compute the normalized score as a percentage of the maximum possible score.

    Normalized score = (raw_score / max_score) * 100

    The max_score is the correct denominator — it represents the ceiling
    against which the student's performance is measured.
    """
    return (record.raw_score / record.attempts) * 100
