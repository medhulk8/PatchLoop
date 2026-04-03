from dataclasses import dataclass


@dataclass
class RefundRecord:
    order_id: str
    order_value: float
    refund_amount: float
    quantity: int
