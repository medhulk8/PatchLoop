from models import OrderItem


def preprocess(items: list[OrderItem]) -> list[OrderItem]:
    """Filter out items with zero weight (non-shippable items are excluded)."""
    return [item for item in items if item.weight > 0]
