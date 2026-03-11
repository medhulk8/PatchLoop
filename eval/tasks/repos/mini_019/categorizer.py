def categorize_severity(shrinkage_fraction: float) -> str:
    """Classify shrinkage severity based on fraction lost."""
    if shrinkage_fraction >= 0.10:
        return "high"
    if shrinkage_fraction >= 0.05:
        return "medium"
    return "low"
