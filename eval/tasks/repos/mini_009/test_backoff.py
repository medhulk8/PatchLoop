from datetime import datetime, timezone
from backoff import retry_after_seconds


NOW = datetime(2015, 10, 21, 7, 27, 50, tzinfo=timezone.utc)
FUTURE = datetime(2015, 10, 21, 7, 29, 0, tzinfo=timezone.utc)


def test_blank_header_returns_zero():
    assert retry_after_seconds("", NOW) == 0


def test_whitespace_only_returns_zero():
    assert retry_after_seconds("   ", NOW) == 0


def test_zero_seconds():
    assert retry_after_seconds("0", NOW) == 0


def test_integer_seconds():
    assert retry_after_seconds("30", NOW) == 30


def test_http_date_future():
    # Fixing blank handling alone is not enough — HTTP-date must also work.
    header = "Wed, 21 Oct 2015 07:28:00 GMT"
    assert retry_after_seconds(header, NOW) == 10


def test_http_date_in_past_clamps_to_zero():
    header = "Wed, 21 Oct 2015 07:28:00 GMT"
    assert retry_after_seconds(header, FUTURE) == 0


def test_malformed_header_returns_zero():
    # After fixing blank and HTTP-date, malformed values must not crash.
    assert retry_after_seconds("not-a-date", NOW) == 0
