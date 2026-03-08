from models import LogEntry


def classify_entries(entries: list[LogEntry]) -> dict[str, list[LogEntry]]:
    """Group log entries by service name."""
    buckets: dict[str, list[LogEntry]] = {}
    for e in entries:
        buckets.setdefault(e.service, []).append(e)
    return buckets
