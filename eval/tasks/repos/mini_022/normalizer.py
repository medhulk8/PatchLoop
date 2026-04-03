def normalize(summary: dict) -> dict:
    """Round monetary totals to two decimal places for consistent output precision."""
    return {k: round(v, 2) if isinstance(v, float) else v for k, v in summary.items()}
