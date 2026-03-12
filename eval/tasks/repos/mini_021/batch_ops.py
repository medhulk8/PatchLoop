def build_record(item_id: str, cost: float, handling_fee: float) -> dict:
    """
    Assemble the final output record for an order item.

    The final price is the item cost plus the handling fee.
    Both values contribute to the total charged to the customer.
    """
    # BUG: subtracts handling_fee instead of adding it
    return {
        "item_id": item_id,
        "final_price": round(cost - handling_fee),
    }


def build_all(aggregated: list[dict]) -> list[dict]:
    return [
        build_record(item["item_id"], item["cost"], item["handling_fee"])
        for item in aggregated
    ]
