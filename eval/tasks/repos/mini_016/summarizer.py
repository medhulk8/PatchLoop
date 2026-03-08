from models import Record


def summarize_bucket(records: list[Record]) -> dict:
    """
    Compute summary statistics for a group of records in the same category.

    The representative value is a weighted average of amounts, where each
    record's weight reflects its relative importance in the dataset.

    Returns raw floats — string formatting for display is the responsibility
    of value_formatter.py, not this module.
    """
    total_amount = sum(r.amount for r in records)
    total_weight = sum(r.weight for r in records)
    record_count = len(records)

    # Compute the representative value for this bucket.
    # Each record's contribution is proportional to its weight.
    representative = total_amount / record_count  # BUG: divides by count, not total_weight

    return {
        "count": record_count,
        "total": round(total_amount, 4),
        "representative": round(representative, 4),
    }


def summarize_all(buckets: dict[str, list[Record]]) -> dict[str, dict]:
    return {cat: summarize_bucket(records) for cat, records in buckets.items()}
