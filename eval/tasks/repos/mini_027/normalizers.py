from models import OrderRecord


def normalize_orders(orders: list[OrderRecord]) -> list[OrderRecord]:
    """Clamp units_filled to [0, units_ordered] to handle over-fill edge cases."""
    normalized = []
    for o in orders:
        normalized.append(OrderRecord(
            order_id=o.order_id,
            units_filled=max(0.0, min(o.units_filled, o.units_ordered)),
            units_ordered=o.units_ordered,
            sku_count=o.sku_count,
        ))
    return normalized
