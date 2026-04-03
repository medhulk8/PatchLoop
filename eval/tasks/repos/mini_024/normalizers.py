from models import DisputeRecord


def normalize_records(records: list[DisputeRecord]) -> list[DisputeRecord]:
    """Round monetary values to cent precision for consistent downstream processing."""
    for r in records:
        r.disputed_value = round(r.disputed_value, 2)
        r.processed_value = round(r.processed_value, 2)
    return records
