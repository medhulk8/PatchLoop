from dataclasses import dataclass, field


@dataclass
class Transaction:
    id: str
    category: str
    amount: float
    description: str = ""
    tags: list = field(default_factory=list)


@dataclass
class Report:
    totals: dict        # category -> total amount
    record_count: int
    categories: list
