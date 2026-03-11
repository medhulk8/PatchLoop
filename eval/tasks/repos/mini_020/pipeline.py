from loader import load_records
from validator import validate_records
from preprocessor import preprocess
from score_calc import compute_normalized
from aggregator import aggregate
from score_entry import build_all
from normalizer import normalize_output
from reporter import build_report


def run_pipeline(raw_records: list[dict]) -> list[dict]:
    validate_records(raw_records)
    records = load_records(raw_records)
    records = preprocess(records)
    scores = [compute_normalized(r) for r in records]
    aggregated = aggregate(records, scores)
    entries = build_all(aggregated)
    entries = normalize_output(entries)
    return build_report(entries)
