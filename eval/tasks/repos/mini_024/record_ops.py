from models import DisputeRecord


def expand_dispute_rows(records: list[DisputeRecord]) -> list[dict]:
    """
    Expand each dispute record into one row per disputed item.

    For multi-item disputes the total disputed value is divided evenly
    across individual items so that per-item totals sum correctly in the
    downstream aggregation step.
    """
    rows = []
    for r in records:
        item_processed = r.processed_value / r.disputed_item_count
        for _ in range(r.disputed_item_count):
            rows.append({
                "order_id": r.order_id,
                "disputed_value": r.disputed_value,
                "processed_value": item_processed,
            })
    return rows
