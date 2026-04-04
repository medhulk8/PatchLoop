from dataclasses import dataclass


@dataclass
class OrderItem:
    item_id: str
    unit_price: float
    quantity: int
    weight: float
    handling_fee: float
