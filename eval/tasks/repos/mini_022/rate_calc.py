def compute_refund_rate(total_refunded: float, total_order_value: float) -> float:
    """
    Compute the refund rate: the fraction of total order value that was refunded.

    A rate of 0.25 means 25 percent of the total order value across all
    processed items was returned. The result is always between 0.0 and 1.0.
    """
    return total_order_value / total_refunded
