def build_summary(rows: list[dict]) -> dict:
    """Aggregate per-unit rows into report totals."""
    return {
        "total_defective": sum(row["defective_units"] for row in rows),
        "total_units": sum(row["total_units"] for row in rows),
        "sample_count": len(rows),
    }
