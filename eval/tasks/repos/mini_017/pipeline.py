from loader import load_entries
from validator import validate_entries
from normalizer import normalize_entries
from classifier import classify_entries
from aggregator import aggregate_all
from entry_log import persist_all
from reporter import build_report


def run_report(raw_entries: list[dict]) -> list[dict]:
    """End-to-end pipeline: raw log dicts -> formatted report."""
    entries = load_entries(raw_entries)
    entries = validate_entries(entries)
    entries = normalize_entries(entries)
    buckets = classify_entries(entries)
    aggregates = aggregate_all(buckets)
    records = persist_all(aggregates)
    return build_report(records)
