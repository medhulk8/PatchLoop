import pytest
from paginator import paginate, total_pages


ITEMS = list(range(1, 11))  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_first_page():
    assert paginate(ITEMS, page=1, page_size=3) == [1, 2, 3]


def test_second_page():
    assert paginate(ITEMS, page=2, page_size=3) == [4, 5, 6]


def test_last_full_page():
    assert paginate(ITEMS, page=3, page_size=3) == [7, 8, 9]


def test_last_partial_page():
    """Last page may have fewer items than page_size."""
    assert paginate(ITEMS, page=4, page_size=3) == [10]


def test_page_size_one():
    assert paginate(ITEMS, page=5, page_size=1) == [5]


def test_out_of_range_page():
    assert paginate(ITEMS, page=99, page_size=3) == []


def test_invalid_page():
    assert paginate(ITEMS, page=0, page_size=3) == []


def test_total_pages_exact():
    assert total_pages(9, 3) == 3


def test_total_pages_with_remainder():
    assert total_pages(10, 3) == 4
