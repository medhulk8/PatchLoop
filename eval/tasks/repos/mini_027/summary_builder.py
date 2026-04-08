def build_summary(rows: list[dict]) -> dict:
    """Aggregate expanded machine rows into report totals."""
    return {
        "total_downtime": sum(row["downtime_minutes"] for row in rows),
        "total_scheduled": sum(row["scheduled_minutes"] for row in rows),
        "machine_row_count": len(rows),
    }
