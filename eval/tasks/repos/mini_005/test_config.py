from config import merge_config


def test_nested_override_preserves_siblings():
    defaults = {"db": {"host": "localhost", "port": 5432}}
    overrides = {"db": {"host": "db.prod"}}
    result = merge_config(defaults, overrides)
    assert result == {"db": {"host": "db.prod", "port": 5432}}


def test_deeply_nested_override_preserves_siblings():
    defaults = {"http": {"retry": {"count": 3, "backoff": 1}}}
    overrides = {"http": {"retry": {"count": 5}}}
    result = merge_config(defaults, overrides)
    assert result == {"http": {"retry": {"count": 5, "backoff": 1}}}


def test_top_level_override_works():
    defaults = {"debug": False, "host": "localhost"}
    overrides = {"debug": True}
    assert merge_config(defaults, overrides) == {"debug": True, "host": "localhost"}


def test_does_not_mutate_defaults():
    # A common partial fix is result[key].update(overrides[key]), which mutates
    # defaults[key] because result is a shallow copy. This test catches that.
    defaults = {"db": {"host": "localhost", "port": 5432}}
    overrides = {"db": {"host": "db.prod"}}
    merge_config(defaults, overrides)
    assert defaults == {"db": {"host": "localhost", "port": 5432}}


def test_does_not_mutate_overrides():
    defaults = {"db": {"host": "localhost"}}
    overrides = {"db": {"host": "db.prod", "port": 5432}}
    merge_config(defaults, overrides)
    assert overrides == {"db": {"host": "db.prod", "port": 5432}}
