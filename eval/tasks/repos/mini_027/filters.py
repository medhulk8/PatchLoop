from models import OrderRecord


def filter_valid_orders(orders: list[OrderRecord]) -> list[OrderRecord]:
    """Drop orders with non-positive units_ordered or sku_count."""
    return [o for o in orders if o.units_ordered > 0 and o.sku_count > 0]
