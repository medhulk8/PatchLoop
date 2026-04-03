from models import BatchRecord


def filter_batches(batches: list[BatchRecord]) -> list[BatchRecord]:
    """Exclude batches with non-positive total units or negative defective counts."""
    return [b for b in batches if b.total_units > 0 and b.defective_units >= 0]
