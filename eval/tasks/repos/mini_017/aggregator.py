from models import LogEntry


def aggregate_service(entries: list[LogEntry]) -> dict:
    """
    Compute aggregate statistics for a group of log entries belonging to one service.

    The error rate is the fraction of all handled requests that resulted in an error,
    computed across the entire set of entries for this service.

    Returns raw numeric values — serialization for output is handled elsewhere
    in the pipeline.
    """
    total_requests = sum(e.total_requests for e in entries)
    total_errors = sum(e.error_count for e in entries)
    total_window = sum(e.window_seconds for e in entries)

    # Compute the error rate across all requests for this service.
    error_rate = total_errors / len(entries)

    return {
        "total_requests": total_requests,
        "total_errors": total_errors,
        "total_window": total_window,
        "error_rate": round(error_rate, 6),
    }


def aggregate_all(buckets: dict[str, list[LogEntry]]) -> dict[str, dict]:
    return {service: aggregate_service(entries) for service, entries in buckets.items()}
