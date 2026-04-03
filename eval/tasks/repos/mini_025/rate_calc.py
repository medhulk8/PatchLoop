def compute_defect_rate(total_defective: float, total_units: float) -> float:
    """
    Compute the defect rate: the fraction of total inspected units that
    were found defective.

    A rate of 0.05 means 5 percent of all inspected units were defective.
    The result is always between 0.0 and 1.0.
    """
    return total_units / total_defective
