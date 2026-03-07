from datetime import datetime


def retry_after_seconds(header: str, now: datetime) -> int:
    """Parse a Retry-After header value and return seconds to wait.

    The header may be:
      - An integer string of delta-seconds (e.g. "120")
      - An HTTP-date string (e.g. "Wed, 21 Oct 2015 07:28:00 GMT")
      - Empty / blank (treat as 0)
      - Malformed (treat as 0)

    Returns 0 if the wait time is in the past or cannot be determined.
    """
    return max(0, int(header.strip()))   # BUG: int() only handles delta-seconds.
                                         # Blank headers raise ValueError.
                                         # HTTP-date strings raise ValueError.
                                         # Malformed values raise ValueError.
