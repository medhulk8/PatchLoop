"""
Retry utility for transient failures.
"""


class TransientError(Exception):
    """Raised when an operation fails transiently and should be retried."""
    pass


class PermanentError(Exception):
    """Raised when an operation fails permanently and should NOT be retried."""
    pass


def retry(func, max_attempts=3):
    """
    Retry func up to max_attempts times on TransientError.
    Raises the last exception if all attempts fail.
    Raises immediately on PermanentError (no retries).
    """
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as exc:
            # BUG: catches ALL exceptions including PermanentError.
            # PermanentError should propagate immediately, not be retried.
            # Fix: change `except Exception` to `except TransientError`.
            last_exc = exc
    raise last_exc
