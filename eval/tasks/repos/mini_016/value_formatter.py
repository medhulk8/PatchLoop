def format_summary(summary: dict) -> dict:
    """
    Format a bucket summary dict for report output.

    Numeric values are rounded to 2 decimal places per reporting spec.
    The representative value is displayed at the same precision as totals.
    """
    return {
        "count": summary["count"],
        "total": f"{summary['total']:.2f}",
        "representative": f"{summary['representative']:.2f}",
    }


def format_all(summaries: dict[str, dict]) -> dict[str, dict]:
    return {cat: format_summary(s) for cat, s in summaries.items()}
