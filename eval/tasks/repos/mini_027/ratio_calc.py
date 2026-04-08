def compute_downtime_ratio(total_downtime: float, total_scheduled: float) -> float:
    """
    Compute the downtime ratio: the fraction of total scheduled time
    spent in downtime across all processed maintenance windows.

    A ratio of 0.10 means 10 percent of scheduled machine time was lost.
    The result is always between 0.0 and 1.0.
    """
    return total_scheduled / total_downtime
