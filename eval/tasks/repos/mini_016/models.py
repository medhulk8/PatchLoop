from dataclasses import dataclass


@dataclass
class Record:
    id: str
    category: str
    amount: float
    weight: float
