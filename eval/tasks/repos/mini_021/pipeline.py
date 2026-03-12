from loader import load_items
from validator import validate_items
from preprocessor import preprocess
from cost_calc import compute_cost
from aggregator import aggregate
from batch_ops import build_all
from normalizer import normalize_output
from reporter import build_report


def run_pipeline(raw_records: list[dict]) -> list[dict]:
    validate_items(raw_records)
    items = load_items(raw_records)
    items = preprocess(items)
    costs = [compute_cost(item) for item in items]
    aggregated = aggregate(items, costs)
    records = build_all(aggregated)
    records = normalize_output(records)
    return build_report(records)
