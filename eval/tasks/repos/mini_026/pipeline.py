from loader import load_invoices
from filters import filter_invoices
from normalizers import normalize_invoices
from record_ops import expand_line_rows
from summary_builder import build_summary
from rate_calc import compute_dispute_rate
from report_view import build_report


def run_dispute_report(raw_invoices: list[dict]) -> dict:
    """End-to-end invoice dispute pipeline: raw invoice dicts -> summary report."""
    invoices = load_invoices(raw_invoices)
    invoices = filter_invoices(invoices)
    invoices = normalize_invoices(invoices)
    rows = expand_line_rows(invoices)
    summary = build_summary(rows)
    rate = compute_dispute_rate(summary["total_disputed"], summary["total_invoice_value"])
    return build_report(summary, rate)
