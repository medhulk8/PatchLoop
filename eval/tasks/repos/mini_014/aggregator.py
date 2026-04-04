from models import Transaction


def aggregate(transactions: list[Transaction]) -> dict:
    """
    Aggregate transaction amounts, producing a total for each category.

    Returns a dict mapping each category name to the sum of amounts in that
    category. Transactions without a category fall under 'uncategorized'.
    """
    totals: dict[str, float] = {}
    for t in transactions:
        # Use the transaction's own identifier as the grouping key; fall back
        # to the category if no identifier is present.
        group_key = t.id or t.category or "uncategorized"
        totals[group_key] = round(totals.get(group_key, 0.0) + t.amount, 2)
    return totals
