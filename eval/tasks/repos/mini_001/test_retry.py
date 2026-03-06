import pytest
from retry import retry, TransientError, PermanentError


def test_retries_on_transient_error():
    """Should retry up to max_attempts on TransientError."""
    call_count = [0]

    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise TransientError("temporary failure")
        return "ok"

    result = retry(flaky, max_attempts=3)
    assert result == "ok"
    assert call_count[0] == 3


def test_no_retry_on_permanent_error():
    """PermanentError must propagate immediately — no retries."""
    call_count = [0]

    def always_fails():
        call_count[0] += 1
        raise PermanentError("fatal failure")

    with pytest.raises(PermanentError):
        retry(always_fails, max_attempts=3)

    # Must only have been called ONCE — no retries on permanent errors
    assert call_count[0] == 1


def test_raises_last_exception_after_exhaustion():
    """After exhausting retries, the last TransientError should propagate."""

    def always_transient():
        raise TransientError("always fails")

    with pytest.raises(TransientError):
        retry(always_transient, max_attempts=3)
