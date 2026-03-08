from loader import load_records
from validator import validate_records
from normalizer import normalize_records
from classifier import classify_records
from summarizer import summarize_all
from value_formatter import format_all
from reporter import build_report
from constants import DEFAULT_UNIT


def run_report(raw_records: list[dict], unit: str = DEFAULT_UNIT) -> list[dict]:
    """End-to-end pipeline: raw record dicts -> formatted report."""
    records = load_records(raw_records)
    records = validate_records(records)
    records = normalize_records(records, unit=unit)
    buckets = classify_records(records)
    summaries = summarize_all(buckets)
    formatted = format_all(summaries)
    return build_report(formatted)
