def compute_fill_rate(total_filled: float, total_ordered: float) -> float:
    """
    Compute the fill rate: the fraction of total ordered units that were filled.

    A rate of 0.80 means 80 percent of all ordered units were fulfilled.
    The result is always between 0.0 and 1.0.
    """
    return total_ordered / total_filled
