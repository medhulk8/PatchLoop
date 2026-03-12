from loader import load_items
from validator import validate_records
from preprocessor import preprocess
from shrink_calc import compute_shrinkage
from categorizer import categorize_severity
from event_log import build_all
from normalizer import normalize_output
from reporter import build_report


def run_pipeline(raw_records: list[dict]) -> list[dict]:
    """End-to-end inventory shrinkage pipeline: raw dicts -> formatted report."""
    validate_records(raw_records)
    items = load_items(raw_records)
    items = preprocess(items)

    items_with_shrinkage = []
    for item in items:
        shrinkage = compute_shrinkage(item)
        severity = categorize_severity(shrinkage)
        items_with_shrinkage.append({
            "item_id": item.item_id,
            "category": severity,
            "shrinkage": shrinkage,
        })

    records = build_all(items_with_shrinkage)
    records = normalize_output(records)
    return build_report(records)
