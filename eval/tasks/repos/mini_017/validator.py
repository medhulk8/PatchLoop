from models import LogEntry
from constants import MIN_WINDOW_SECONDS, MAX_ERROR_COUNT


def validate_entries(entries: list[LogEntry]) -> list[LogEntry]:
    """Drop entries that are structurally invalid."""
    valid = []
    for e in entries:
        if e.total_requests <= 0:
            continue
        if e.window_seconds < MIN_WINDOW_SECONDS:
            continue
        if e.error_count < 0 or e.error_count > MAX_ERROR_COUNT:
            continue
        valid.append(e)
    return valid
