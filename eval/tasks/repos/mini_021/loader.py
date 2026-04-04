from models import OrderItem


def load_items(raw: list[dict]) -> list[OrderItem]:
    """Parse raw dicts into OrderItem objects."""
    return [
        OrderItem(
            item_id=str(r["item_id"]),
            unit_price=float(r["unit_price"]),
            quantity=int(r["quantity"]),
            weight=float(r["weight"]),
            handling_fee=float(r["handling_fee"]),
        )
        for r in raw
    ]
