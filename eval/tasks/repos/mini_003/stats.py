"""
Basic descriptive statistics utilities.
"""


def mean(values):
    """Return the arithmetic mean of a list of numbers."""
    if not values:
        raise ValueError("mean() requires at least one value")
    return sum(values) / len(values)


def median(values):
    """
    Return the median of a list of numbers.

    For odd-length lists: return the middle element.
    For even-length lists: return the average of the two middle elements.
    """
    if not values:
        raise ValueError("median() requires at least one value")

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2

    if n % 2 == 1:
        return sorted_vals[mid]
    else:
        # BUG: returns only the upper-middle element instead of averaging.
        # Should be: (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        return sorted_vals[mid]


def variance(values):
    """Return the population variance of a list of numbers."""
    if len(values) < 2:
        raise ValueError("variance() requires at least two values")
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / len(values)


def std_dev(values):
    """Return the population standard deviation."""
    return variance(values) ** 0.5
