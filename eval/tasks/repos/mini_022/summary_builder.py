def build_summary(rows: list[dict]) -> dict:
    """Aggregate per-item rows into report totals."""
    return {
        "total_refunded": sum(row["refund_amount"] for row in rows),
        "total_order_value": sum(row["order_value"] for row in rows),
        "item_count": len(rows),
    }
