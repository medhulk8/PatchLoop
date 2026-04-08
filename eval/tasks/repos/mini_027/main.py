from rate_calc import compute_fill_rate
from report_view import format_report
from summary_builder import build_fulfillment_summary


def run_fulfillment_report(raw_orders: list[dict]) -> dict:
    """
    Run the full fulfillment analytics pipeline and return a report dict.

    Keys: total_filled, total_ordered, fill_rate.
    """
    summary = build_fulfillment_summary(raw_orders)
    fill_rate = compute_fill_rate(summary["total_filled"], summary["total_ordered"])
    return format_report(summary, fill_rate)
