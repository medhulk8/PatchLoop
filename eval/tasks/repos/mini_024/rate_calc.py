def compute_chargeback_rate(total_disputed: float, total_processed: float) -> float:
    """
    Compute the chargeback rate: the fraction of total processed value
    that was disputed.

    A rate of 0.10 means 10 percent of all processed transaction value
    was charged back. The result is always between 0.0 and 1.0.
    """
    return total_processed / total_disputed
