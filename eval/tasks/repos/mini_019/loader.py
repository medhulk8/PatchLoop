from models import StockItem


def load_items(records: list[dict]) -> list[StockItem]:
    """Parse raw record dicts into StockItem dataclass instances."""
    return [
        StockItem(
            item_id=str(r["item_id"]),
            opening_stock=float(r["opening_stock"]),
            closing_stock=float(r["closing_stock"]),
            category=str(r["category"]),
        )
        for r in records
    ]
