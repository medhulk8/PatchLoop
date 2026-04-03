from models import DisputeRecord


def filter_records(records: list[DisputeRecord]) -> list[DisputeRecord]:
    """Exclude records with non-positive processed values or negative disputed amounts."""
    return [r for r in records if r.processed_value > 0 and r.disputed_value >= 0]
