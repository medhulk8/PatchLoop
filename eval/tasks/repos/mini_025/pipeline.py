from loader import load_batches
from filters import filter_batches
from normalizers import normalize_batches
from record_ops import expand_sample_rows
from summary_builder import build_summary
from rate_calc import compute_defect_rate
from report_view import build_report


def run_defect_report(raw_batches: list[dict]) -> dict:
    """End-to-end defect analytics pipeline: raw batch dicts -> summary report."""
    batches = load_batches(raw_batches)
    batches = filter_batches(batches)
    batches = normalize_batches(batches)
    rows = expand_sample_rows(batches)
    summary = build_summary(rows)
    rate = compute_defect_rate(summary["total_defective"], summary["total_units"])
    return build_report(summary, rate)
