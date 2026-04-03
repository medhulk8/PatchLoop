from models import DisputeRecord


def load_records(raw: list[dict]) -> list[DisputeRecord]:
    """Parse raw dispute dicts into DisputeRecord dataclass instances."""
    return [
        DisputeRecord(
            order_id=str(r["order_id"]),
            disputed_value=float(r["disputed_value"]),
            processed_value=float(r["processed_value"]),
            disputed_item_count=int(r.get("disputed_item_count", 1)),
        )
        for r in raw
    ]
