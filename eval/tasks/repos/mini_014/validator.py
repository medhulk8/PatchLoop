from models import Transaction


def validate(transactions: list[Transaction]) -> list[Transaction]:
    """Drop transactions that are missing required fields or have invalid amounts."""
    valid = []
    for t in transactions:
        if not t.id:
            continue
        if not t.category:
            continue
        if t.amount < 0:
            continue
        valid.append(t)
    return valid
