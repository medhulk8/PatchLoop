REQUIRED_FIELDS = {"item_id", "opening_stock", "closing_stock", "category"}


def validate_records(records: list[dict]) -> None:
    """Validate required fields and value ranges."""
    for i, r in enumerate(records):
        missing = REQUIRED_FIELDS - r.keys()
        if missing:
            raise ValueError(f"Record {i}: missing fields {missing}")
        if float(r["opening_stock"]) <= 0:
            raise ValueError(f"Record {i}: opening_stock must be positive")
        if float(r["closing_stock"]) < 0:
            raise ValueError(f"Record {i}: closing_stock must be non-negative")
        if float(r["closing_stock"]) > float(r["opening_stock"]):
            raise ValueError(f"Record {i}: closing_stock cannot exceed opening_stock")
