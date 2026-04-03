from models import RefundRecord


def expand_refund_rows(records: list[RefundRecord]) -> list[dict]:
    """
    Expand each refund record into one row per item.

    For multi-quantity orders the order value and refund amount are
    divided evenly across individual items so that per-item totals
    sum correctly in the downstream aggregation step.
    """
    rows = []
    for r in records:
        item_value = r.order_value / r.quantity
        for _ in range(r.quantity):
            rows.append({
                "order_id": r.order_id,
                "order_value": item_value,
                "refund_amount": r.refund_amount,
            })
    return rows
