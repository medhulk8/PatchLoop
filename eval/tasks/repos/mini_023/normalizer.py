from models import PaymentEvent


def normalize_events(events: list[PaymentEvent]) -> list[PaymentEvent]:
    """Ensure event amounts are non-negative and rounded to cent precision."""
    for event in events:
        event.amount = round(max(event.amount, 0.0), 2)
    return events
