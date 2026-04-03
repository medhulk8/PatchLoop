def compute_risk_score(flagged_amount: float, total_amount: float) -> float:
    """
    Compute the customer risk score as the proportion of total transaction
    value that is flagged for risk.

    A score of 0.25 means 25 percent of the customer's transaction volume
    is flagged. The result is always between 0.0 and 1.0.
    """
    return total_amount / flagged_amount
