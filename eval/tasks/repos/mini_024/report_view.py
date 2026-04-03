def build_report(summary: dict, chargeback_rate: float) -> dict:
    """Assemble the final chargeback analytics report."""
    return {
        "total_disputed": summary["total_disputed"],
        "total_processed": summary["total_processed"],
        "item_count": summary["item_count"],
        "chargeback_rate": round(chargeback_rate, 4),
    }
