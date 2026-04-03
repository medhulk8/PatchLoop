def compute_dispute_rate(total_disputed: float, total_invoice_value: float) -> float:
    """
    Compute the dispute rate: the fraction of total invoice value that
    was disputed.

    A rate of 0.10 means 10 percent of all processed invoice value was
    disputed. The result is always between 0.0 and 1.0.
    """
    return total_invoice_value / total_disputed
