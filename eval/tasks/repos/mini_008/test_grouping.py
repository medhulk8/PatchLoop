from grouping import group_rows


def test_noncontiguous_keys_are_merged():
    rows = [("b", 1), ("a", 2), ("b", 3)]
    assert group_rows(rows) == {"b": [1, 3], "a": [2]}


def test_key_order_is_first_seen():
    # The naive fix (sort then groupby) changes key order — this catches that.
    rows = [("b", 1), ("a", 2), ("b", 3)]
    assert list(group_rows(rows).keys()) == ["b", "a"]


def test_value_order_is_input_order():
    # The naive fix (sort then groupby) may reorder values — this catches that.
    rows = [("a", 2), ("a", 1), ("a", 3)]
    assert group_rows(rows)["a"] == [2, 1, 3]


def test_single_key():
    rows = [("x", 10), ("x", 20)]
    assert group_rows(rows) == {"x": [10, 20]}


def test_all_different_keys():
    rows = [("a", 1), ("b", 2), ("c", 3)]
    assert group_rows(rows) == {"a": [1], "b": [2], "c": [3]}
    assert list(group_rows(rows).keys()) == ["a", "b", "c"]
