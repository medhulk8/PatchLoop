from dataclasses import dataclass


@dataclass
class DisputeRecord:
    order_id: str
    disputed_value: float
    processed_value: float
    disputed_item_count: int
