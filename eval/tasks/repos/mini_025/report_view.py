def build_report(summary: dict, defect_rate: float) -> dict:
    """Assemble the final defect analytics report."""
    return {
        "total_defective": summary["total_defective"],
        "total_units": summary["total_units"],
        "sample_count": summary["sample_count"],
        "defect_rate": round(defect_rate, 4),
    }
