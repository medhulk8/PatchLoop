from models import Transaction


def load_transactions(records: list[dict]) -> list[Transaction]:
    """Convert raw record dicts into Transaction objects."""
    result = []
    for r in records:
        result.append(Transaction(
            id=r["id"],
            category=r["category"],
            amount=float(r["amount"]),
            description=r.get("description", ""),
            tags=r.get("tags", []),
        ))
    return result
