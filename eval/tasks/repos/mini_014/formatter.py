from models import Report, Transaction


def format_report(totals: dict, transactions: list[Transaction]) -> Report:
    """
    Build a Report from aggregated totals.

    The totals dict maps group keys to total amounts. Categories are the
    unique category values from the input transactions, sorted alphabetically.
    """
    categories = sorted({t.category for t in transactions})
    return Report(
        totals=totals,
        record_count=len(transactions),
        categories=categories,
    )
