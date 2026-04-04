def validate_items(items_raw: list[dict]) -> None:
    """Raise ValueError if any required field is missing or invalid."""
    required = {"item_id", "unit_price", "quantity", "weight", "handling_fee"}
    for r in items_raw:
        missing = required - r.keys()
        if missing:
            raise ValueError(f"Missing fields: {missing}")
        if float(r["unit_price"]) <= 0:
            raise ValueError(f"unit_price must be positive: {r['unit_price']}")
        if int(r["quantity"]) <= 0:
            raise ValueError(f"quantity must be positive: {r['quantity']}")
