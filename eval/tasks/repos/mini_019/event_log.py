def build_record(item_id: str, category: str, shrinkage_fraction: float) -> dict:
    """
    Assemble the output record for an inventory item.

    The shrinkage fraction is converted to a percentage value and
    stored as a rounded figure for reporting and audit trail purposes.
    """
    # BUG: truncates instead of rounds — int() discards fractional part
    pct = int(shrinkage_fraction * 10000) / 100
    return {
        "item_id": item_id,
        "category": category,
        "shrinkage_pct": pct,
    }


def build_all(items_with_shrinkage: list[dict]) -> list[dict]:
    return [
        build_record(item["item_id"], item["category"], item["shrinkage"])
        for item in items_with_shrinkage
    ]
