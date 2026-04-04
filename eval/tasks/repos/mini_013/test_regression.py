from pipeline import process_record


def test_regression_01():
    # All-truthy values with no schema defaults — output should match input exactly
    result = process_record({"name": "alice", "score": 99}, {})
    assert result == {"name": "alice", "score": 99}


def test_regression_02():
    # A score of zero is a valid value and must appear in the output
    result = process_record({"name": "bob", "score": 0}, {})
    assert result == {"name": "bob", "score": 0}


def test_regression_03():
    # An empty string label is a valid value and must appear in the output
    result = process_record({"id": 42, "label": ""}, {})
    assert result == {"id": 42, "label": ""}


def test_regression_04():
    # A record value must override the schema default for the same field
    result = process_record(
        {"player": "carol", "score": 0},
        {"score": 100, "lives": 3},
    )
    assert result == {"player": "carol", "score": 0, "lives": 3}


def test_regression_05():
    # False is a valid explicit value and must override a truthy schema default
    result = process_record(
        {"feature": "notifications", "enabled": False},
        {"enabled": True},
    )
    assert result == {"feature": "notifications", "enabled": False}
