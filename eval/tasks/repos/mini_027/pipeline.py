from filters import filter_records
from loader import load_records
from normalizers import normalize_records
from ratio_calc import compute_downtime_ratio
from record_ops import expand_machine_rows
from report_view import build_report
from summary_builder import build_summary


def run_downtime_report(raw_records: list[dict]) -> dict:
    """End-to-end maintenance pipeline: raw rows -> downtime analytics."""
    records = load_records(raw_records)
    records = filter_records(records)
    records = normalize_records(records)
    rows = expand_machine_rows(records)
    summary = build_summary(rows)
    ratio = compute_downtime_ratio(summary["total_downtime"], summary["total_scheduled"])
    return build_report(summary, ratio)
