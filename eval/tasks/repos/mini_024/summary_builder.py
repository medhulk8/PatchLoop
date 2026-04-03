def build_summary(rows: list[dict]) -> dict:
    """Aggregate per-item rows into report totals."""
    return {
        "total_disputed": sum(row["disputed_value"] for row in rows),
        "total_processed": sum(row["processed_value"] for row in rows),
        "item_count": len(rows),
    }
