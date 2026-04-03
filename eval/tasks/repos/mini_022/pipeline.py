from loader import load_records
from filters import filter_records
from record_ops import expand_refund_rows
from summary_builder import build_summary
from normalizer import normalize
from rate_calc import compute_refund_rate
from reporter import build_report


def run_report(raw_records: list[dict]) -> dict:
    """End-to-end refund analytics pipeline: raw order dicts -> summary report."""
    records = load_records(raw_records)
    records = filter_records(records)
    rows = expand_refund_rows(records)
    summary = build_summary(rows)
    summary = normalize(summary)
    rate = compute_refund_rate(summary["total_refunded"], summary["total_order_value"])
    return build_report(summary, rate)
