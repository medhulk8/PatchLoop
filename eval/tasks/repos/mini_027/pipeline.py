from filters import filter_valid_orders
from loader import load_orders
from normalizers import normalize_orders
from record_ops import expand_sku_rows


def run_pipeline(raw_orders: list[dict]) -> list[dict]:
    """
    Run the fulfillment data pipeline.

    Loads, filters, normalizes, then expands order records into
    per-SKU rows ready for aggregation.
    """
    orders = load_orders(raw_orders)
    orders = filter_valid_orders(orders)
    orders = normalize_orders(orders)
    return expand_sku_rows(orders)
