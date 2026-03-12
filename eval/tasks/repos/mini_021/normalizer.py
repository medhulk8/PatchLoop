def normalize_output(records: list[dict]) -> list[dict]:
    """Ensure consistent field ordering in output records."""
    return [
        {"item_id": r["item_id"], "final_price": r["final_price"]}
        for r in records
    ]
