from models import RefundRecord


def filter_records(records: list[RefundRecord]) -> list[RefundRecord]:
    """Exclude records with non-positive order values or negative refund amounts."""
    return [r for r in records if r.order_value > 0 and r.refund_amount >= 0]
