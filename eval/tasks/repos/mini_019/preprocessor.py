from models import StockItem


def preprocess(items: list[StockItem]) -> list[StockItem]:
    """Sort items by item_id for deterministic output ordering."""
    return sorted(items, key=lambda x: x.item_id)
