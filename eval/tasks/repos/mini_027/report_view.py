def format_report(summary: dict, fill_rate: float) -> dict:
    """Format the final fulfillment report."""
    return {
        "total_filled": summary["total_filled"],
        "total_ordered": summary["total_ordered"],
        "fill_rate": round(fill_rate, 4),
    }
