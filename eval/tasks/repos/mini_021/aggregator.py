from models import OrderItem


def aggregate(items: list[OrderItem], costs: list[float]) -> list[dict]:
    """Pair each item with its computed cost and handling fee."""
    return [
        {"item_id": r.item_id, "cost": c, "handling_fee": r.handling_fee}
        for r, c in zip(items, costs)
    ]
