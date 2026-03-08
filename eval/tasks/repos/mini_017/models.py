from dataclasses import dataclass


@dataclass
class LogEntry:
    """A single log entry representing a time window of service activity."""

    service: str
    total_requests: int
    error_count: float  # float to support fractional weighting
    window_seconds: int
