from models import PaymentEvent


def load_events(raw: list[dict]) -> list[PaymentEvent]:
    """Parse raw event dicts into PaymentEvent dataclass instances."""
    return [
        PaymentEvent(
            event_id=str(r["event_id"]),
            customer_id=str(r["customer_id"]),
            amount=float(r["amount"]),
            decision=str(r["decision"]),
        )
        for r in raw
    ]
