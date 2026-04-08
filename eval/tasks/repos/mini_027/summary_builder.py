from pipeline import run_pipeline


def build_fulfillment_summary(raw_orders: list[dict]) -> dict:
    """
    Build aggregated fulfillment totals from raw order data.

    Runs the full pipeline and returns total_filled and total_ordered
    for use by the rate calculation step.
    """
    rows = run_pipeline(raw_orders)
    total_filled = sum(r["units_filled"] for r in rows)
    total_ordered = sum(r["units_ordered"] for r in rows)
    return {
        "total_filled": total_filled,
        "total_ordered": total_ordered,
    }
