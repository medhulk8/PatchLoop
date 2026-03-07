import os
import pytest
from paths import safe_join


def test_allows_simple_filename():
    assert safe_join("/srv/app", "app.log") == os.path.join("/srv/app", "app.log")


def test_allows_nested_path_single_part():
    result = safe_join("/srv/app", "logs/2026/app.log")
    assert result == os.path.normpath("/srv/app/logs/2026/app.log")


def test_allows_nested_path_multi_part():
    result = safe_join("/srv/app", "logs", "2026", "app.log")
    assert result == os.path.normpath("/srv/app/logs/2026/app.log")


def test_rejects_parent_traversal_simple():
    # The naive fix (remove the guard entirely) lets this through — it must not.
    with pytest.raises(ValueError):
        safe_join("/srv/app", "../secret.txt")


def test_rejects_traversal_inside_nested_path():
    with pytest.raises(ValueError):
        safe_join("/srv/app", "logs/../../secret.txt")


def test_rejects_absolute_part():
    with pytest.raises(ValueError):
        safe_join("/srv/app", "/etc/passwd")
