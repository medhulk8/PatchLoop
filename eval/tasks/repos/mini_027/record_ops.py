from models import OrderRecord


def expand_sku_rows(orders: list[OrderRecord]) -> list[dict]:
    """
    Expand each order into one row per SKU.

    For multi-SKU orders the total units ordered is divided evenly across
    individual SKUs so that per-SKU totals sum correctly in the downstream
    aggregation step.
    """
    rows = []
    for o in orders:
        units_per_sku = o.units_ordered / o.sku_count
        for _ in range(o.sku_count):
            rows.append({
                "order_id": o.order_id,
                "units_filled": o.units_filled,
                "units_ordered": units_per_sku,
            })
    return rows
