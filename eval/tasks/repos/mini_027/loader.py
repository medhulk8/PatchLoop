from models import OrderRecord


def load_orders(raw: list[dict]) -> list[OrderRecord]:
    records = []
    for item in raw:
        records.append(OrderRecord(
            order_id=str(item["order_id"]),
            units_filled=float(item["units_filled"]),
            units_ordered=float(item["units_ordered"]),
            sku_count=int(item["sku_count"]),
        ))
    return records
