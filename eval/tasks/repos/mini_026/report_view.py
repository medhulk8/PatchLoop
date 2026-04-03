def build_report(summary: dict, dispute_rate: float) -> dict:
    """Assemble the final invoice dispute analytics report."""
    return {
        "total_disputed": summary["total_disputed"],
        "total_invoice_value": summary["total_invoice_value"],
        "line_count": summary["line_count"],
        "dispute_rate": round(dispute_rate, 4),
    }
