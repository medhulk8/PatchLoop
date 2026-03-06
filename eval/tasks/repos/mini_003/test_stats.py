import pytest
from stats import mean, median, variance, std_dev


# --- mean ---

def test_mean_basic():
    assert mean([1, 2, 3, 4, 5]) == 3.0


def test_mean_single():
    assert mean([7]) == 7.0


def test_mean_empty():
    with pytest.raises(ValueError):
        mean([])


# --- median ---

def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    """Even-length list: median is the average of the two middle elements."""
    assert median([1, 2, 3, 4]) == 2.5


def test_median_even_not_integers():
    assert median([1.0, 3.0, 5.0, 7.0]) == 4.0


def test_median_two_elements():
    assert median([10, 20]) == 15.0


def test_median_single():
    assert median([42]) == 42


def test_median_already_sorted():
    assert median([1, 3, 5, 7, 9]) == 5


def test_median_empty():
    with pytest.raises(ValueError):
        median([])


# --- variance / std_dev ---

def test_variance_basic():
    assert variance([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(4.0)


def test_std_dev_basic():
    assert std_dev([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.0)


def test_variance_single_raises():
    with pytest.raises(ValueError):
        variance([1])
