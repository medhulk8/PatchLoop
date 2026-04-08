from dataclasses import dataclass


@dataclass
class OrderRecord:
    order_id: str
    units_filled: float
    units_ordered: float
    sku_count: int
