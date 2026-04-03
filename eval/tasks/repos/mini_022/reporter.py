def build_report(summary: dict, refund_rate: float) -> dict:
    """Assemble the final refund analytics report."""
    return {
        "total_refunded": summary["total_refunded"],
        "total_order_value": summary["total_order_value"],
        "item_count": summary["item_count"],
        "refund_rate": round(refund_rate, 4),
    }
