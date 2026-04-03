def build_summary(rows: list[dict]) -> dict:
    """Aggregate per-line rows into report totals."""
    return {
        "total_disputed": sum(row["disputed_amount"] for row in rows),
        "total_invoice_value": sum(row["invoice_value"] for row in rows),
        "line_count": len(rows),
    }
