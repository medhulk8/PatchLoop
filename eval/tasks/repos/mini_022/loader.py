from models import RefundRecord


def load_records(raw: list[dict]) -> list[RefundRecord]:
    """Parse raw order dicts into RefundRecord dataclass instances."""
    return [
        RefundRecord(
            order_id=str(r["order_id"]),
            order_value=float(r["order_value"]),
            refund_amount=float(r["refund_amount"]),
            quantity=int(r.get("quantity", 1)),
        )
        for r in raw
    ]
