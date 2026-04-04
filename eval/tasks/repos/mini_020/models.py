from dataclasses import dataclass


@dataclass
class StudentRecord:
    student_id: str
    raw_score: float
    max_score: float
    attempts: int
