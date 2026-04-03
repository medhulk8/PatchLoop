from dataclasses import dataclass, field


@dataclass
class PaymentEvent:
    event_id: str
    customer_id: str
    amount: float
    decision: str  # "block", "review", "allow"
    is_flagged: bool = field(default=False)
