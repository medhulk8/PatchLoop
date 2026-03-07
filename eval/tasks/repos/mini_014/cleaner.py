from models import Transaction


def clean(transactions: list[Transaction]) -> list[Transaction]:
    """Normalize transaction fields: strip whitespace, lowercase category."""
    cleaned = []
    for t in transactions:
        cleaned.append(Transaction(
            id=t.id.strip(),
            category=t.category.strip().lower(),
            amount=round(t.amount, 2),
            description=t.description.strip(),
            tags=[tag.strip().lower() for tag in t.tags],
        ))
    return cleaned
