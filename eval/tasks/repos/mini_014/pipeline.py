from aggregator import aggregate
from cleaner import clean
from formatter import format_report
from loader import load_transactions
from models import Report
from validator import validate


def run_report(raw_records: list[dict]) -> Report:
    """
    Execute the full report pipeline.

    Stages:
      1. load   — parse raw dicts into Transaction objects
      2. clean  — normalize fields
      3. validate — drop malformed records
      4. aggregate — sum amounts by category
      5. format — produce the final Report
    """
    transactions = load_transactions(raw_records)
    transactions = clean(transactions)
    transactions = validate(transactions)
    totals = aggregate(transactions)
    return format_report(totals, transactions)
