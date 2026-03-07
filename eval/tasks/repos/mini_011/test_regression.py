from merge import merge
from serialize import serialize


def test_regression_01():
    # False set in base must survive the full pipeline
    result = serialize(merge({"enabled": False, "name": "job"}, {}))
    assert result == {"enabled": False, "name": "job"}


def test_regression_02():
    # Override with zero must win over base value
    result = serialize(merge({"retries": 3, "name": "job"}, {"retries": 0}))
    assert result == {"retries": 0, "name": "job"}


def test_regression_03():
    # Override with False must win over base True
    result = serialize(merge({"active": True, "name": "job"}, {"active": False}))
    assert result == {"active": False, "name": "job"}


def test_regression_04():
    # Empty string override must win over base string
    result = serialize(merge({"label": "default", "name": "job"}, {"label": ""}))
    assert result == {"label": "", "name": "job"}
