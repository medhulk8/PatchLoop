from models import Record


def classify_records(records: list[Record]) -> dict[str, list[Record]]:
    """Group records into buckets by category."""
    buckets: dict[str, list[Record]] = {}
    for r in records:
        if r.category not in buckets:
            buckets[r.category] = []
        buckets[r.category].append(r)
    return buckets
