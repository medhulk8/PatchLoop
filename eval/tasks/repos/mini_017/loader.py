from models import LogEntry


def load_entries(raw: list[dict]) -> list[LogEntry]:
    """Parse raw dicts into LogEntry objects."""
    return [
        LogEntry(
            service=row["service"],
            total_requests=int(row["total_requests"]),
            error_count=float(row["error_count"]),
            window_seconds=int(row["window_seconds"]),
        )
        for row in raw
    ]
