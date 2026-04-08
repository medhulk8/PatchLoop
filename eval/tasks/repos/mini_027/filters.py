from models import OrderRecord


def filter_valid_orders(orders: list[OrderRecord]) -> list[OrderRecord]:
    """Drop orders with non-positive units_ordered or quantity."""
    return [o for o in orders if o.units_ordered > 0 and o.quantity > 0]
