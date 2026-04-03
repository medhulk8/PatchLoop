from models import BatchRecord


def normalize_batches(batches: list[BatchRecord]) -> list[BatchRecord]:
    """Round unit counts to two decimal places for consistent downstream processing."""
    for b in batches:
        b.defective_units = round(b.defective_units, 2)
        b.total_units = round(b.total_units, 2)
    return batches
