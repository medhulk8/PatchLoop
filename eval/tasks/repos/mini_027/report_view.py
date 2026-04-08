def build_report(summary: dict, downtime_ratio: float) -> dict:
    """Assemble the final maintenance downtime analytics report."""
    return {
        "total_downtime": summary["total_downtime"],
        "total_scheduled": summary["total_scheduled"],
        "machine_row_count": summary["machine_row_count"],
        "downtime_ratio": round(downtime_ratio, 4),
    }
