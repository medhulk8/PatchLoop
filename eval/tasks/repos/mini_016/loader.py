from models import Record


def load_records(data: list[dict]) -> list[Record]:
    """Load raw record dicts into Record objects."""
    return [
        Record(
            id=r["id"],
            category=r["category"],
            amount=float(r["amount"]),
            weight=float(r.get("weight", 1.0)),
        )
        for r in data
    ]
