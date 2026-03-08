from models import LogEntry


def normalize_entries(entries: list[LogEntry]) -> list[LogEntry]:
    """Normalize service names to lowercase stripped strings."""
    for e in entries:
        e.service = e.service.strip().lower()
    return entries
