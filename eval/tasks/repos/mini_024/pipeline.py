from loader import load_records
from filters import filter_records
from normalizers import normalize_records
from record_ops import expand_dispute_rows
from summary_builder import build_summary
from rate_calc import compute_chargeback_rate
from report_view import build_report


def run_chargeback_report(raw_records: list[dict]) -> dict:
    """End-to-end chargeback analytics pipeline: raw dispute dicts -> summary report."""
    records = load_records(raw_records)
    records = filter_records(records)
    records = normalize_records(records)
    rows = expand_dispute_rows(records)
    summary = build_summary(rows)
    rate = compute_chargeback_rate(summary["total_disputed"], summary["total_processed"])
    return build_report(summary, rate)
